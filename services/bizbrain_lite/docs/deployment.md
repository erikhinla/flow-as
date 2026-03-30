# BizBrain Lite Deployment

## Prerequisites

- Python 3.11+
- Redis (local or remote)
- Notion workspace (optional; service runs without it)

## Environment

Copy `.env.example` to `.env` and set:

| Variable | Required | Description |
|----------|----------|--------------|
| `BIZBRAIN_ENV` | No | `dev` or `prod` (default: `dev`) |
| `BIZBRAIN_API_TOKEN` | No | API token for v1 endpoints. If unset, auth is disabled. |
| `BIZBRAIN_REDIS_URL` | Yes | Redis connection URL (e.g. `redis://localhost:6379/0`) |
| `NOTION_API_KEY` | No | Notion integration token for durable mirror |
| `NOTION_TASKS_DB_ID` | No | Notion database ID for tasks |
| `NOTION_ARTIFACTS_DB_ID` | No | Notion database ID for artifacts |
| `NOTION_HANDOFFS_DB_ID` | No | Notion database ID for handoffs |
| `NOTION_AGENT_STATUS_DB_ID` | No | Notion database ID for agent status |
| `NOTION_MEMORY_DB_ID` | No | Notion database ID for operational memory |
| `SOCIAL_HUB_API_ORIGIN` | No | Allowed CORS origin for Social Asset Hub |

## Run locally

```bash
cd services/fastapi/bizbrain_lite
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Production

- Use a process manager (systemd, supervisord, or Docker) to run uvicorn.
- Set `BIZBRAIN_API_TOKEN` in production.
- Use a managed Redis instance.
- Health check: `GET /v1/health` (no auth required).

## Docker (example)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Social Asset Hub integration

Set `VITE_BIZBRAIN_API_ORIGIN` in the hub's `.env` to the BizBrain Lite base URL (e.g. `http://localhost:8000`) and `VITE_BIZBRAIN_API_TOKEN` if auth is enabled.
