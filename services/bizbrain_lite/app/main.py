"""BizBrain Lite: FAAS Control Plane and Worker Orchestration.

Main FastAPI application that serves as the FLOW Agent AS control plane.
Manages task intake, job routing, worker coordination, and proof-of-work validation.

Services initialized on startup:
- PostgreSQL: Durable job/reflection records
- Redis: FIFO job queues per worker
- Skill extraction: Background job for pattern learning
- Agent executors: Worker processes for autonomous execution
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    agents,
    artifacts,
    handoffs,
    health,
    tasks,
    threads,
    flow_health,
    hermes_skills,
    openclaw_intake,
    agent_zero_reviews,
    performance,
    flow_control,
    worker_jobs,
)
from app.config.settings import get_settings
from app.config.database import close_db, init_db
from app.services.redis_store import redis_store
from app.services.redis_queue_service import RedisQueueService, get_redis_client
from app.services.skill_extraction_job import SkillExtractionJob
from app.workers.executor_base import AgentExecutor
from app.workers.hermes_executor import HermesExecutor
from app.workers.openclaw_executor import OpenClawExecutor
from app.workers.agent_zero_executor import AgentZeroExecutor
from app.config.database import SessionLocal

logger = logging.getLogger(__name__)
settings = get_settings()

# Global service instances
skill_extraction_job = None
redis_queue_service = None
agent_executors: dict[str, AgentExecutor] = {}
executor_tasks: dict[str, asyncio.Task] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup/shutdown."""
    # Startup
    await startup_services()
    yield
    # Shutdown
    await shutdown_services()


app = FastAPI(
    title="FLOW Agent AS — FAAS Control Plane",
    description="Governed task intake, routing, and worker orchestration",
    version="1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/v1")
app.include_router(artifacts.router, prefix="/v1")
app.include_router(handoffs.router, prefix="/v1")
app.include_router(threads.router, prefix="/v1")
app.include_router(agents.router, prefix="/v1")
app.include_router(flow_health.router, prefix="/v1")
app.include_router(hermes_skills.router, prefix="/v1")
app.include_router(openclaw_intake.router, prefix="/v1")
app.include_router(worker_jobs.router, prefix="/v1")
app.include_router(agent_zero_reviews.router, prefix="/v1")
app.include_router(performance.router, prefix="/v1")
app.include_router(flow_control.router, prefix="/v1")


async def startup_services():
    """Initialize all FLOW services on app startup."""
    global skill_extraction_job, redis_queue_service, agent_executors, executor_tasks

    logger.info("=" * 80)
    logger.info("FLOW AGENT AS — FAAS Control Plane Startup")
    logger.info("=" * 80)

    # 1. Initialize PostgreSQL
    try:
        await init_db()
        logger.info("✓ PostgreSQL tables initialized (job_records, reflection_records, skill_records, audit_logs)")
    except Exception as exc:
        logger.error(f"✗ Failed to initialize PostgreSQL: {exc}")
        raise

    # 2. Initialize Redis
    try:
        redis_url = settings.bizbrain_redis_url
        redis_client = await get_redis_client(redis_url)
        redis_queue_service = RedisQueueService(redis_client)
        openclaw_intake.redis_queue_service = redis_queue_service
        logger.info(f"✓ Redis queue service initialized: {redis_url}")
        logger.info(f"  Queues: flow:openclaw:jobs, flow:hermes:jobs, flow:agent_zero:jobs, flow:dead_letter")
    except Exception as exc:
        logger.error(f"✗ Failed to initialize Redis: {exc}")
        redis_queue_service = None

    # 3. Initialize skill extraction background job
    try:
        skill_extraction_job = SkillExtractionJob(interval_seconds=300)  # Every 5 minutes
        asyncio.create_task(skill_extraction_job.start())
        logger.info("✓ Skill extraction background job started (runs every 5 minutes)")
    except Exception as exc:
        logger.error(f"✗ Failed to start skill extraction job: {exc}")
        skill_extraction_job = None

    # 4. Initialize autonomous agent executors
    try:
        # Create database session factory for workers
        db_factory = SessionLocal

        # Initialize Hermes executor
        hermes_executor = HermesExecutor(
            db_session_maker=db_factory,
            redis_queue_service=redis_queue_service,
            worker_id="hermes-executor-01",
        )
        agent_executors["hermes"] = hermes_executor
        executor_task = asyncio.create_task(hermes_executor.run())
        executor_tasks["hermes"] = executor_task
        logger.info("✓ Hermes executor started (artifact_production, skill_extraction, content_prep)")

        # Initialize OpenClaw executor
        openclaw_executor = OpenClawExecutor(
            db_session_maker=db_factory,
            redis_queue_service=redis_queue_service,
            worker_id="openclaw-executor-01",
        )
        agent_executors["openclaw"] = openclaw_executor
        executor_task = asyncio.create_task(openclaw_executor.run())
        executor_tasks["openclaw"] = executor_task
        logger.info("✓ OpenClaw executor started (classification, rewrite, content_prep)")

        # Initialize Agent Zero executor
        agent_zero_executor = AgentZeroExecutor(
            db_session_maker=db_factory,
            redis_queue_service=redis_queue_service,
            worker_id="agent-zero-executor-01",
        )
        agent_executors["agent_zero"] = agent_zero_executor
        executor_task = asyncio.create_task(agent_zero_executor.run())
        executor_tasks["agent_zero"] = executor_task
        logger.info("✓ Agent Zero executor started (implementation, high-risk work)")

        logger.info("\n" + "=" * 80)
        logger.info("FAAS CONTROL PLANE READY")
        logger.info("=" * 80)
        logger.info(f"API Base URL: http://localhost:18000/v1")
        logger.info(f"Intake endpoint: POST /v1/intake/task")
        logger.info(f"Job management: POST /v1/jobs/{{task_id}}/claim|complete|fail|escalate")
        logger.info(f"Worker reflections: POST /v1/jobs/{{task_id}}/reflections")
        logger.info(f"Hermes skills: GET /v1/hermes/skills, POST /v1/hermes/reflections")
        logger.info(f"Agent Zero reviews: GET /v1/agent-zero/reviews/{{job_id}}/status")
        logger.info("=" * 80 + "\n")

    except Exception as exc:
        logger.error(f"✗ Failed to initialize agent executors: {exc}", exc_info=True)


async def shutdown_services():
    """Clean up services on app shutdown."""
    global skill_extraction_job, redis_queue_service, agent_executors, executor_tasks

    logger.info("\n" + "=" * 80)
    logger.info("FLOW AGENT AS — Shutdown")
    logger.info("=" * 80)

    # 1. Stop skill extraction job
    if skill_extraction_job:
        try:
            await skill_extraction_job.stop()
            logger.info("✓ Skill extraction job stopped")
        except Exception as exc:
            logger.error(f"✗ Error stopping skill extraction job: {exc}")

    # 2. Stop agent executors
    for owner, executor in agent_executors.items():
        try:
            if owner in executor_tasks:
                executor_tasks[owner].cancel()
            logger.info(f"✓ {owner.capitalize()} executor stopped")
        except Exception as exc:
            logger.error(f"✗ Error stopping {owner} executor: {exc}")

    # 3. Close Redis connection
    if redis_queue_service:
        try:
            await redis_queue_service.redis.close()
            logger.info("✓ Redis connection closed")
        except Exception as exc:
            logger.error(f"✗ Error closing Redis: {exc}")

    # 4. Close Redis store
    try:
        await redis_store.close()
        logger.info("✓ Redis store closed")
    except Exception as exc:
        logger.error(f"✗ Error closing Redis store: {exc}")

    # 5. Close database
    try:
        await close_db()
        logger.info("✓ PostgreSQL connection pool closed")
    except Exception as exc:
        logger.error(f"✗ Error closing PostgreSQL: {exc}")

    logger.info("=" * 80 + "\n")
