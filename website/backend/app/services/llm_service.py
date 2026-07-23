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



from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.schema import Document
from llama_index.vector_stores.lancedb import LanceDBVectorStore


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


# def transcribe_audio(audio_path: str | os.PathLike[str]) -> str:
#     if not os.path.exists(audio_path):
#         return ""

#     recognizer = sr.Recognizer()
#     try:
#         with sr.AudioFile(str(audio_path)) as source:
#             audio_data = recognizer.record(source)
#             try:
#                 return recognizer.recognize_whisper(audio_data)
#             except Exception:
#                 return ""
#     except Exception:
#         return ""

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


def build_retrieval_context(question: str, transcript: str, frame_paths: list[str], session_id: str) -> str:
    if not transcript and not frame_paths:
        return ""

    if StorageContext is None or VectorStoreIndex is None or Document is None or LanceDBVectorStore is None:
        return transcript[:4000] if transcript else ""

    cleaned_transcript = " ".join(transcript.split())
    chunks = []
    if cleaned_transcript:
        chunks.extend(
            chunk.strip()
            for chunk in re.split(r"(?<=[.!?])\s+", cleaned_transcript)
            if chunk.strip()
        )

    documents = [Document(text=chunk, metadata={"source": "transcript"}) for chunk in chunks[:8]]
    for frame_path in frame_paths[:4]:
        documents.append(
            Document(text=f"Visual frame from the video: {Path(frame_path).name}", metadata={"source": "image"})
        )

    if not documents:
        return ""

    vector_dir = Path(__file__).resolve().parents[2] / "vector_store" / session_id
    vector_dir.mkdir(parents=True, exist_ok=True)

    vector_store = LanceDBVectorStore(uri=str(vector_dir), table_name=f"session_{session_id}")
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    embed_model = None
    try:
        from llama_index.embeddings.clip import ClipEmbedding
        embed_model = ClipEmbedding(model_name="ViT-B/32")
    except Exception:
        try:
            from llama_index.core.embeddings.mock_embed_model import MockEmbedding
            embed_model = MockEmbedding(embed_dim=384)
        except Exception:
            embed_model = None

    index = (
        VectorStoreIndex.from_documents(documents, storage_context=storage_context, embed_model=embed_model)
        if embed_model is not None
        else VectorStoreIndex.from_documents(documents, storage_context=storage_context)
    )
    retriever = index.as_retriever(similarity_top_k=3)
    retrieval_results = retriever.retrieve(question)
    return "\n".join(node.get_text() for node in retrieval_results if hasattr(node, "get_text"))


def answer_question(
    question: str,
    context: str,
    metadata: dict[str, Any],
    session_id: str | None = None,
    frame_paths: list[str] | None = None,
) -> str:
    retrieval_context = build_retrieval_context(question, context, frame_paths or [], session_id or "default")
    answer_context = retrieval_context or context

    try:
        import google.generativeai as genai

        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = (                
            "You are answering from the uploaded video context only. "
            f"Video metadata: {metadata}.\n"
            f"Retrieved context: {answer_context[:6000]}\n"
            f"Question: {question}\n"
            "Answer concisely and accurately."
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        pass

    if answer_context:
        return (
            f"Based on the retrieved video context, the answer appears to be related to: {answer_context[:1500]}"
        )

    return "The video transcript is not available yet. Please upload a video with clearer audio or try again later."
