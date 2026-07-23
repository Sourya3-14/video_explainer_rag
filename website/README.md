# Multimodal RAG Website

## Backend

```bash
cd website/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Frontend

```bash
cd website/frontend
npm install
npm run dev
```

The frontend expects the backend at http://127.0.0.1:8000.
