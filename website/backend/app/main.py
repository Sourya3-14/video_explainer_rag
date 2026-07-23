from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.chat_routes import router as chat_router

app = FastAPI(title="Multimodal RAG Website", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Multimodal RAG backend is running"}
