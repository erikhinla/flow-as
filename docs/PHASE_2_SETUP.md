# Phase 2: Durable State Implementation - Dependencies

Add these to `services/bizbrain_lite/requirements.txt` or `pyproject.toml`:

## Postgres / SQLAlchemy
```
sqlalchemy>=2.0.0
asyncpg>=0.28.0
alembic>=1.12.0
psycopg2-binary>=2.9.0
```

## Environment Variables (add to .env)
```
# Database
DATABASE_URL=postgresql+asyncpg://flow_user:flow_password@localhost:5432/flow_agent_os
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_RECYCLE=3600
DB_POOL_PRE_PING=true
DB_ECHO=false
```

## Setup Steps

1. **Install dependencies:**
   ```bash
   cd services/bizbrain_lite
   pip install -e ".[postgres]"
   ```

2. **Initialize database:**
   ```bash
   # Create Postgres database
   createdb flow_agent_os
   createuser flow_user -P  # Enter password: flow_password
   
   # Run migrations
   alembic upgrade head
   ```

3. **Update main.py to initialize FLOW health endpoint:**
   ```python
   from app.api import flow_health
   
   app.include_router(flow_health.router)  # This adds /flow/health, /flow/workers, etc.
   ```

4. **Test health endpoint:**
   ```bash
   curl http://localhost:8000/v1/flow/health
   ```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0",
  "timestamp": "2026-04-03T...",
  "checks": {"database": "ok", "postgres": "ok"},
  "queues": {"pending": 0, "queued": 0, "active": 0, ...},
  "metrics": {"jobs_completed_1h": 0, "jobs_failed_1h": 0, ...},
  "alerts": null
}
```

## Files Created in Phase 2

**Models:**
- `app/models/flow_job_record.py` — JobRecord SQLAlchemy model
- `app/models/flow_reflection_record.py` — ReflectionRecord SQLAlchemy model
- `app/models/flow_skill_record.py` — SkillRecord SQLAlchemy model

**Config:**
- `app/config/database.py` — Postgres connection pool setup

**API:**
- `app/api/flow_health.py` — Health check endpoints for FLOW

**Migrations:**
- `alembic/versions/flow_001_create_durable_state.py` — Alembic migration

## Next Phase

Once database is running and health check is working:
- Phase 3: Hermes skill extraction loop
- Phase 4: OpenClaw envelope validation + routing
- Phase 5: Agent Zero review artifact enforcement
