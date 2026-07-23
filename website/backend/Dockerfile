FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install Linux packages
RUN apt-get update && apt-get install -y \
    build-essential \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
COPY requirements.txt .
RUN pip install --upgrade pip

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Create runtime directories
RUN mkdir -p uploads vector_store

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]