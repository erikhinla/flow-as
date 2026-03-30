# BizBrain Lite

BizBrain Lite is a lightweight FastAPI control plane for coordinating OpenClaw, Alpha/Beta/Gamma agents, Social Asset Hub metadata, and deployment operations.

## Scope

- Runtime state: Redis
- Durable operational memory: Notion databases
- Registries: tasks, artifacts, thread handoffs, threads, agent status
- Non-invasive: does not replace public site or Social Asset Hub rendering/export

## Run

1. Create and activate a Python 3.11+ virtual environment.
2. Install dependencies:
   - `pip install -e .`
3. Copy `.env.example` to `.env` and fill required values.
4. Start service:
   - `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

## API prefix

- `/v1`

## Docs

- `docs/api_endpoint_list.md`
- `docs/redis_usage.md`
- `docs/notion_database_mapping.md`
- `docs/alpha_beta_gamma_interaction.md`
- `docs/recommended_build_order.md`
- `docs/deployment.md`

## Tests

```bash
pip install -e ".[dev]"
pytest
```

