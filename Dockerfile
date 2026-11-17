# Use official lightweight Python base image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Set working directory
WORKDIR /app

# Install system dependencies required by Playwright and SQLite
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Install uv dependency manager
RUN pip install --no-cache-dir uv

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install project dependencies without building the application yet
RUN uv sync --frozen --no-install-project

# Copy application source code
COPY . .

# Install the application into the environment
RUN uv sync --frozen

# Install Playwright browser binaries
RUN uv run playwright install chromium --with-deps

# Expose ports for FastAPI (8000) and Streamlit (8501)
EXPOSE 8000 8501

# Default command launches the FastAPI backend and Streamlit dashboard concurrently
CMD ["sh", "-c", "uv run uvicorn festtrackai.api.routes:app --host 0.0.0.0 --port 8000 & uv run streamlit run src/festtrackai/ui/dashboard.py --server.port 8501 --server.address 0.0.0.0"]