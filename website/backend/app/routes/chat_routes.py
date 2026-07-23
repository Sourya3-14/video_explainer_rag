from pathlib import Path

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from app.auth import (
    create_access_token,
    get_current_user,
    get_current_user_optional,
    verify_access_token,
    verify_google_token,
)
from app.controllers.chat_controller import (
    ask_question,
    create_session,
    list_sessions,
    upload_video_and_create_session,
)
from app.database import get_db
from app.models import ChatMessageRequest, GoogleAuthRequest, SessionCreateRequest

router = APIRouter(prefix="", tags=["chat"])
DB = get_db()


@router.post("/auth/google")
def google_login(payload: GoogleAuthRequest) -> dict:
    """Authenticates Google ID Token and returns JWT token."""
    google_user = verify_google_token(payload.google_token)

    users_collection = DB["users"]
    user = users_collection.find_one({"email": google_user["email"]})

    if not user:
        user_doc = {
            "email": google_user["email"],
            "name": google_user.get("name", ""),
            "picture": google_user.get("picture", ""),
            "google_sub": google_user["sub"],
        }
        res = users_collection.insert_one(user_doc)
        user_id = str(res.inserted_id)
    else:
        user_id = str(user["_id"])

    access_token = create_access_token(
        {
            "user_id": user_id,
            "email": google_user["email"],
            "name": google_user.get("name", ""),
            "picture": google_user.get("picture", ""),
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": google_user["email"],
            "name": google_user.get("name", ""),
            "picture": google_user.get("picture", ""),
        },
    }


@router.get("/sessions")
def get_sessions(current_user: dict = Depends(get_current_user)) -> list[dict]:
    return list_sessions(user_id=current_user["user_id"])


@router.post("/sessions", response_model=dict)
def create_upload_session(
    file: UploadFile | None = File(default=None),
    title: str | None = Form(default=None),
    video_title: str | None = Form(default=None),
    youtube_url: str | None = Form(default=None),
    current_user: dict = Depends(get_current_user),
) -> dict:
    payload = SessionCreateRequest(title=title, video_title=video_title, youtube_url=youtube_url)
    if file or youtube_url:
        return upload_video_and_create_session(file, payload, user_id=current_user["user_id"])
    return create_session(payload, user_id=current_user["user_id"], pending=False)


@router.get("/sessions/{session_id}/video")
def get_session_video(
    session_id: str,
    token: str | None = Query(default=None),
    current_user: dict | None = Depends(get_current_user_optional),
) -> FileResponse:
    # 1. Fallback: If header is missing (e.g. standard HTML <video> tag), verify token from URL query
    user_data = current_user
    if not user_data and token:
        try:
            user_data = verify_access_token(token)
        except Exception as exc:
            raise HTTPException(status_code=401, detail="Invalid token provided in query parameter") from exc
    if not user_data or "user_id" not in user_data:
        raise HTTPException(status_code=401, detail="Authentication required to stream video")

    # 2. Fetch session restricted to the user's ID
    session = DB.chat_sessions.find_one({"_id": ObjectId(session_id), "user_id": user_data["user_id"]})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or access denied")

    video_path = session.get("video_path")
    if not video_path:
        raise HTTPException(status_code=404, detail="No video available for this session")

    path = Path(video_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Video file missing on server")

    return FileResponse(path)


@router.post("/sessions/{session_id}/messages")
def post_message(
    session_id: str,
    payload: ChatMessageRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    return ask_question(session_id, payload, user_id=current_user["user_id"])