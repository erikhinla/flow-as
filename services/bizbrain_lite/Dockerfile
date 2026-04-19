# =============================================================================
# bizbrain_lite — FLOW Agent OS API service
# Build context: repo root (so schemas/ is available)
# docker-compose: build: context: . dockerfile: services/bizbrain_lite/Dockerfile
# =============================================================================

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
        libpq-dev \
            && rm -rf /var/lib/apt/lists/*

            # Copy schemas from repo root so the service can validate task envelopes
            COPY schemas/ /app/schemas/

            # Copy the service source
            COPY services/bizbrain_lite/ /app/

            # Install Python dependencies
            RUN pip install --no-cache-dir -e .

            # Create runtime dirs
            RUN mkdir -p /app/runtime/reviews

            EXPOSE 8000

            CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
            
