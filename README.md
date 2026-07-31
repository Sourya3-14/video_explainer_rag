# Multimodal RAG Web Application

This repository contains a full-stack multimodal Retrieval-Augmented Generation (RAG) application for chatting with uploaded videos. Users can upload a video file or provide a YouTube URL, have the system process the content, and then ask questions about it in natural language.

The project combines:

- a FastAPI backend for video processing, indexing, authentication, and chat endpoints
- a React + Vite frontend for uploading videos and interacting with the assistant
- MongoDB for session and user storage
- LanceDB for vector search over extracted video content
- Google Gemini for answer generation

## Features

- Upload video files or reference YouTube videos
- Extract video metadata and sample frames
- Extract audio and transcribe it
- Build a retrieval index from the transcript and visual context
- Ask questions about the video content in a chat-style interface
- Authenticate users with Google OAuth and JWT-based session handling
- Persist chat sessions per user

## Tech Stack

- Backend: Python, FastAPI, PyMongo, sentence-transformers, moviepy, SpeechRecognition
- Frontend: React, Vite, Tailwind CSS, Axios
- Vector Store: LanceDB
- AI Models: Google Gemini, sentence-transformers embeddings
- Storage: MongoDB

## Project Structure

```text
.
├── notebook/                  # Jupyter notebook for prototyping the multimodal RAG flow
├── website/
│   ├── backend/               # FastAPI backend
│   │   ├── app/
│   │   │   ├── controllers/
│   │   │   ├── routes/
│   │   │   ├── services/
│   │   │   └── main.py
│   │   ├── uploads/           # Uploaded and processed video files
│   │   └── requirements.txt
│   └── frontend/              # React frontend
│       ├── src/
│       └── package.json
└── README.md
```

## Prerequisites

Before running the project, make sure you have the following installed:

- Python 3.10+
- Node.js 18+
- MongoDB running locally or remotely
- FFmpeg installed and available on your PATH

## Backend Setup

1. Open a terminal and navigate to the repository root.
2. Create and activate a virtual environment:

```bash
python -m venv venv
venv\Scripts\activate
```

3. Install Python dependencies:

```bash
pip install -r website/backend/requirements.txt
```

4. Create a `.env` file inside `website/backend` with the required variables:

```env
GOOGLE_API_KEY=your_google_gemini_api_key
GOOGLE_CLIENT_ID=your_google_oauth_client_id
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=multimodal_rag
JWT_SECRET_KEY=change-this-to-a-secure-secret
```

5. Start the backend:

```bash
cd website/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:

- http://localhost:8000
- Swagger UI: http://localhost:8000/docs

## Frontend Setup

1. In a second terminal, install the frontend dependencies:

```bash
cd website/frontend
npm install
```

2. Start the development server:

```bash
npm run dev
```

The frontend will be available at:

- http://localhost:5173

## Usage

1. Open the frontend in your browser.
2. Sign in with Google.
3. Create a new session.
4. Upload a video file or enter a YouTube URL.
5. Wait for the video to be processed.
6. Ask questions about the video in the chat interface.

## Notes

- The backend stores uploaded videos in the `website/backend/uploads` directory.
- Vector embeddings are stored in the `website/backend/vector_store` directory.
- The notebook under `notebook/` is useful for exploring the pipeline and experimenting with the indexing logic.

## Development Notes

If you want to contribute or extend the project:

- improve the retrieval pipeline for better context accuracy
- add support for more video formats or richer metadata extraction
- enhance the frontend experience with better session visualization
- add automated tests for backend routes and processing pipelines
