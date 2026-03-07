FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml uv.lock ./

# Install uv and dependencies
RUN pip install uv && uv sync

# Expose FastAPI port
EXPOSE 8000

# Run FastAPI with uvicorn
CMD ["uv", "run", "python", "main.py"]
