from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bson import ObjectId
from fastapi import HTTPException, UploadFile
from pymongo import ASCENDING

from app.database import get_db
from app.models import ChatMessageRequest, SessionCreateRequest
from app.services.llm_service import answer_question, process_video, index_video

DB = get_db()

# Initialize collection & indexes
if "chat_sessions" not in DB.list_collection_names():
    DB.create_collection("chat_sessions")
    DB.chat_sessions.create_index([("created_at", ASCENDING)])
    DB.chat_sessions.create_index([("user_id", ASCENDING)])  # Fast user-level lookup index


def build_session_title(payload: SessionCreateRequest) -> str:
    if payload.title and payload.title.strip():
        return payload.title.strip()
    timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
    return f"Session {timestamp}"


def serialize_session(session: dict[str, Any]) -> dict[str, Any]:
    serialized: dict[str, Any] = {}
    for key, value in session.items():
        if key == "_id":
            serialized["id"] = str(value)
        elif isinstance(value, ObjectId):
            serialized[key] = str(value)
        elif isinstance(value, datetime):
            serialized[key] = value.isoformat()
        elif isinstance(value, list):
            serialized[key] = [serialize_session(item) if isinstance(item, dict) else item for item in value]
        elif isinstance(value, dict):
            serialized[key] = serialize_session(value)
        else:
            serialized[key] = value
    return serialized


def download_youtube_video(url: str, output_dir: Path) -> tuple[Path, str]:
    """Helper to download a YouTube video using yt-dlp."""
    try:
        import yt_dlp
    except ImportError as exc:
        raise HTTPException(status_code=500, detail=f"yt-dlp is not installed on the server: {exc}") from exc

    video_template = output_dir / "input_vid.%(ext)s"
    ydl_opts = {
        "outtmpl": str(video_template),
        "format": "best[ext=mp4]/mp4",
        "quiet": True,
        "noplaylist": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title") or "YouTube video"
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to download YouTube video: {exc}") from exc

    downloaded_files = sorted(output_dir.glob("input_vid.*"))
    if not downloaded_files:
        raise HTTPException(status_code=400, detail="The YouTube video could not be downloaded")

    chosen_file = next(
        (path for path in downloaded_files if path.suffix.lower() in {".mp4", ".mkv", ".avi", ".mov", ".webm"}),
        downloaded_files[0],
    )
    return chosen_file, title


def create_session(payload: SessionCreateRequest, user_id: str, pending: bool = False) -> dict[str, Any]:
    # Delete unused empty sessions ONLY for the current user
    DB.chat_sessions.delete_many({"user_id": user_id, "messages": []})

    session_doc = {
        "user_id": user_id,  # Linked directly to user
        "title": build_session_title(payload),
        "video_title": payload.video_title or ("YouTube video" if payload.youtube_url else "Uploaded video"),
        "source_type": "youtube" if payload.youtube_url else "upload",
        "source_url": payload.youtube_url or "",
        "created_at": datetime.now(timezone.utc),
        "messages": [],
        "video_metadata": {},
        "video_frames": [],
        "transcript": "",
        "status": "pending" if pending else "active",
    }
    result = DB.chat_sessions.insert_one(session_doc)
    session_doc["id"] = str(result.inserted_id)
    return serialize_session(session_doc)


def list_sessions(user_id: str) -> list[dict[str, Any]]:
    # Query ONLY sessions belonging to the authenticated user
    sessions = list(
        DB.chat_sessions.find(
            {"user_id": user_id, "status": {"$ne": "pending"}},
            {
                "_id": 1,
                "title": 1,
                "video_title": 1,
                "created_at": 1,
                "messages": 1,
                "video_metadata": 1,
                "source_type": 1,
                "source_url": 1,
                "video_path": 1,
            },
        )
    )
    serialized_sessions = [serialize_session(session) for session in sessions]
    return sorted(serialized_sessions, key=lambda item: item.get("created_at", ""), reverse=True)


def upload_video_and_create_session(
    file: UploadFile | None, payload: SessionCreateRequest, user_id: str
) -> dict[str, Any]:
    session = create_session(payload, user_id=user_id, pending=True)
    if not file and not payload.youtube_url:
        return session

    session_id = session["id"]
    upload_dir = Path("uploads") / session_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    video_path: Path | None = None
    source_type = "upload"
    if file and file.filename:
        video_path = upload_dir / file.filename
        with video_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    elif payload.youtube_url:
        source_type = "youtube"
        video_path, youtube_title = download_youtube_video(payload.youtube_url, upload_dir)
        if payload.video_title is None:
            session["video_title"] = youtube_title

    if video_path is None:
        raise HTTPException(status_code=400, detail="Unable to process video source")

    processed = process_video(str(video_path), upload_dir)

    index_video(
        transcript=processed["transcript"],
        frame_paths=processed["frame_paths"],
        session_id=session_id,
    )
    update_payload = {
        "video_metadata": processed["metadata"],
        "video_frames": processed["frame_paths"],
        "transcript": processed["transcript"],
        "video_path": str(video_path),
        "source_type": source_type,
        "source_url": payload.youtube_url or "",
        "updated_at": datetime.now(timezone.utc),
    }
    DB.chat_sessions.update_one({"_id": ObjectId(session_id)}, {"$set": update_payload})

    session["video_metadata"] = processed["metadata"]
    session["video_frames"] = processed["frame_paths"]
    session["transcript"] = processed["transcript"]
    session["video_path"] = str(video_path)
    session["source_type"] = source_type
    session["source_url"] = payload.youtube_url or ""
    return serialize_session(session)


def ask_question(session_id: str, payload: ChatMessageRequest, user_id: str) -> dict[str, Any]:
    # Security filter: must match both session_id AND user_id
    session = DB.chat_sessions.find_one({"_id": ObjectId(session_id), "user_id": user_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or access denied")

    transcript = session.get("transcript", "")
    metadata = session.get("video_metadata", {})
    frame_paths = session.get("video_frames", [])

    if session.get("status") == "pending":
        DB.chat_sessions.update_one({"_id": ObjectId(session_id)}, {"$set": {"status": "active"}})

    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # answer = answer_question(question, transcript, metadata, session_id, frame_paths)
    answer = answer_question(
        question=question,
        context=transcript,
        metadata=metadata,
        session_id=session_id,
        frame_paths=frame_paths,
        history=session.get("messages", []),
    )

    now_iso = datetime.now(timezone.utc).isoformat()
    message_entry = {"role": "user", "content": question, "timestamp": now_iso}
    response_entry = {"role": "assistant", "content": answer, "timestamp": now_iso}

    DB.chat_sessions.update_one(
        {"_id": ObjectId(session_id)},
        {
            "$push": {
                "messages": {
                    "$each": [message_entry, response_entry]
                }
            },
            "$set": {
                "last_updated": datetime.now(timezone.utc)
            }
        }
    )

    return {
        "session_id": session_id,
        "answer": answer,
        "messages": [message_entry, response_entry],
    }