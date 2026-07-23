import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")  # From Google Developer Console
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "multimodal_rag")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")

# Auth Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-key-change-this-in-production")
JWT_ALGORITHM = "HS256"