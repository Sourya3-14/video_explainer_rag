import time
from typing import Any, Dict

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.transport import requests
from google.oauth2 import id_token

from app.config import GOOGLE_CLIENT_ID, JWT_ALGORITHM, JWT_SECRET_KEY

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


def verify_google_token(token: str) -> Dict[str, Any]:
    """Verifies Google ID Token sent from the React frontend."""
    try:
        # If GOOGLE_CLIENT_ID is configured, pass it here for strict validation
        id_info = id_token.verify_oauth2_token(
            token, requests.Request(), audience=GOOGLE_CLIENT_ID if GOOGLE_CLIENT_ID else None
        )
        return {
            "email": id_info.get("email"),
            "name": id_info.get("name"),
            "picture": id_info.get("picture"),
            "sub": id_info.get("sub"),  # Google's unique User ID
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google Token: {exc}",
        ) from exc


def create_access_token(user_data: Dict[str, Any], expires_in_seconds: int = 604800) -> str:
    """Generates a backend JWT valid for 7 days by default."""
    payload = {
        "user_id": user_data["user_id"],
        "email": user_data["email"],
        "name": user_data.get("name", ""),
        "picture": user_data.get("picture", ""),
        "exp": int(time.time()) + expires_in_seconds,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_access_token(token: str) -> Dict[str, Any]:
    """Decodes and validates a raw JWT token string."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization token"
        ) from exc


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """FastAPI Dependency: Protects routes and extracts current authenticated user payload."""
    token = credentials.credentials
    return verify_access_token(token)


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
) -> dict[str, Any] | None:
    """Optional auth dependency; returns None when no bearer token is provided."""
    if not credentials:
        return None
    return verify_access_token(credentials.credentials)


def get_current_user_id(user: Dict[str, Any] = Depends(get_current_user)) -> str:
    """FastAPI Dependency: Convenience helper to directly inject user_id string into routes."""
    user_id = user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user payload")
    return user_id