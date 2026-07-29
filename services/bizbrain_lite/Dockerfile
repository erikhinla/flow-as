FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY services/bizbrain_lite/pyproject.toml /app/pyproject.toml
COPY services/bizbrain_lite/README.md /app/README.md
COPY services/bizbrain_lite/.env.example /app/.env.example
COPY services/bizbrain_lite/alembic.ini /app/alembic.ini
COPY services/bizbrain_lite/app /app/app
COPY services/bizbrain_lite/docs /app/docs
COPY scripts /app/scripts
COPY schemas /app/schemas
COPY alembic /app/alembic

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

RUN mkdir -p /app/runtime/reviews

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
