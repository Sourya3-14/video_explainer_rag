from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from moviepy import VideoFileClip
import speech_recognition as sr

from dotenv import load_dotenv
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")



# from llama_index.core import StorageContext, VectorStoreIndex
# from llama_index.core.schema import Document
# from llama_index.vector_stores.lancedb import LanceDBVectorStore

import lancedb
from sentence_transformers import SentenceTransformer

embedding_model = SentenceTransformer("BAAI/bge-small-en-v1.5")


def extract_video_metadata(video_path: str | os.PathLike[str]) -> dict[str, Any]:
    clip = VideoFileClip(str(video_path))
    metadata = {
        "duration": round(clip.duration, 2),
        "fps": clip.fps,
        "width": clip.w,
        "height": clip.h,
    }
    clip.close()
    return metadata


def sample_frames(video_path: str | os.PathLike[str], output_dir: Path, limit: int = 6) -> list[str]:
    clip = VideoFileClip(str(video_path))
    clip.write_images_sequence(str(output_dir / "frame%04d.png"), fps=1.0)
    clip.close()

    paths = sorted([str(path) for path in output_dir.glob("frame*.png")])
    return paths[:limit]


def extract_audio(video_path: str | os.PathLike[str], output_audio_path: Path) -> str:
    clip = VideoFileClip(str(video_path))
    if clip.audio is None:
        clip.close()
        return ""

    clip.audio.write_audiofile(str(output_audio_path), codec="pcm_s16le")
    clip.close()
    return str(output_audio_path)

def transcribe_audio(audio_path):
    recognizer = sr.Recognizer()

    print("Audio path:", audio_path)
    print("Exists:", os.path.exists(audio_path))

    with sr.AudioFile(audio_path) as source:
        audio = recognizer.record(source)

    print("Audio loaded.")

    try:
        text = recognizer.recognize_whisper(audio)
        print("Transcript:", text[:300])
        return text
    except Exception as e:
        print("WHISPER ERROR")
        print(type(e))
        print(e)
        raise

def process_video(video_path: str | os.PathLike[str], session_dir: Path) -> dict[str, Any]:
    metadata = extract_video_metadata(video_path)
    frame_paths = sample_frames(video_path, session_dir)
    audio_path = session_dir / "audio.wav"
    extracted_audio_path = extract_audio(video_path, audio_path)
    transcript = transcribe_audio(extracted_audio_path) if extracted_audio_path else ""

    return {
        "metadata": metadata,
        "frame_paths": frame_paths,
        "transcript": transcript,
        "audio_path": extracted_audio_path,
    }

def index_video(
    transcript: str,
    frame_paths: list[str],
    session_id: str,
) -> None:

    if not transcript and not frame_paths:
        return

    cleaned = " ".join(transcript.split())

    chunks = [
        chunk.strip()
        for chunk in re.split(r"(?<=[.!?])\s+", cleaned)
        if chunk.strip()
    ]

    chunks = chunks[:8]

    for frame in frame_paths[:4]:
        chunks.append(f"Visual frame from video: {Path(frame).name}")

    db_path = Path(__file__).resolve().parents[2] / "vector_store"
    db_path.mkdir(parents=True, exist_ok=True)

    db = lancedb.connect(str(db_path))

    table_name = "video_chunks"

    embeddings = embedding_model.encode(chunks).tolist()

    data = [
        {
            "session_id": session_id,
            "text": text,
            "vector": vector,
        }
        for text, vector in zip(chunks, embeddings)
    ]

    try:
        table = db.open_table(table_name)

        # Remove old chunks for this session if re-uploading
        table.delete(f"session_id = '{session_id}'")

    except Exception:
        table = db.create_table(table_name, data=data)
        return

    table.add(data)

def build_retrieval_context(
    question: str,
    session_id: str,
) -> str:

    db_path = Path(__file__).resolve().parents[2] / "vector_store"

    db = lancedb.connect(str(db_path))

    table = db.open_table("video_chunks")

    query_embedding = embedding_model.encode(question).tolist()

    results = (
        table.search(query_embedding)
        .where(f"session_id = '{session_id}'")
        .limit(3)
        .to_list()
    )

    return "\n".join(row["text"] for row in results)

def build_search_query(
    question: str,
    history_text: str,
) -> str:

    if not history_text:
        return question

    try:
        import google.generativeai as genai

        genai.configure(api_key=GOOGLE_API_KEY)

        model = genai.GenerativeModel("gemini-2.5-flash")

        prompt = f"""
            Given the conversation history and the latest user question,
            rewrite the latest question into a standalone search query.

            Conversation:
            {history_text}

            Latest Question:
            {question}

            Return ONLY the rewritten question.
            """

        response = model.generate_content(prompt)

        return response.text.strip()

    except Exception:
        return question
    
def answer_question(
    question: str,
    context: str,
    metadata: dict[str, Any],
    session_id: str | None = None,
    frame_paths: list[str] | None = None,
    history: list[dict] | None = None,
) -> str:
    history_text = ""

    if history:
        # Keep only the last 8 messages
        recent_history = history[-8:]

        for message in recent_history:
            role = message.get("role", "user").capitalize()
            content = message.get("content", "").strip()

            if content:
                history_text += f"{role}: {content}\n"

    search_query = build_search_query(
        question,
        history_text,
    )

    retrieval_context = build_retrieval_context(
        search_query,
        session_id or "default",
    )
    # retrieval_context = build_retrieval_context(question, context, frame_paths or [], session_id or "default")
    answer_context = retrieval_context or context

    try:
        import google.generativeai as genai

        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = f"""
            You are an AI assistant answering questions about an uploaded educational video.

            Conversation History:
            {history_text}

            Video Metadata:
            {metadata}

            Retrieved Context:
            {answer_context}

            Current Question:
            {question}

            Instructions:
            - If the user asks about the conversation itself (for example:
                "What was my previous question?",
                "What did you just say?",
                "Repeat your last answer"),
                answer ONLY from the conversation history.
            - Otherwise Use the retrieved context as the primary source.
            - Use the conversation history to understand references.
            - Do not invent facts not supported by the retrieved context.
            - Explain concepts in simple language.
            - Use bullet points where helpful.
            - Explain technical terms.
            - If the answer is unavailable from the retrieved context,clearly say so.
            - Answer the query proeprly even if it is unrelated to the context
        """

        response = model.generate_content(prompt)
        return response.text.strip()
    
    except Exception:
        pass

    if answer_context:
        return (
            f"Based on the retrieved video context, the answer appears to be related to: {answer_context[:1500]}"
        )

    return "The video transcript is not available yet. Please upload a video with clearer audio or try again later."
