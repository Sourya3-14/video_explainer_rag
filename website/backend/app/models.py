from typing import Optional
from pydantic import BaseModel, Field


class GoogleAuthRequest(BaseModel):
    google_token: str = Field(..., description="ID Token received from Google Sign-In")


class SessionCreateRequest(BaseModel):
    title: Optional[str] = Field(default=None, description="Human-friendly session title")
    video_title: Optional[str] = Field(default=None, description="Original video title")
    youtube_url: Optional[str] = Field(default=None, description="Optional YouTube link for processing")


class ChatMessageRequest(BaseModel):
    question: str = Field(..., min_length=1)