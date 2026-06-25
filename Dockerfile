# Backend image for LiveTransit Copilot — runs both the API and the poller
# (same code, different start command set per-service in docker-compose.yml).
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first so this layer is cached when only app code changes.
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy the application code.
COPY backend ./backend

# Default command (the API). Overridden by the poller service.
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
