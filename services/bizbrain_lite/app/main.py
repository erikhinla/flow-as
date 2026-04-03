import asyncio
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agents, artifacts, handoffs, health, tasks, threads, flow_health, hermes_skills, openclaw_intake, agent_zero_reviews
from app.config.settings import get_settings
from app.services.skill_extraction_job import SkillExtractionJob
from app.services.redis_queue_service import get_redis_client, RedisQueueService

settings = get_settings()

app = FastAPI(
    title="BizBrain Lite",
    version="0.1.0",
    description="Lightweight control plane for TB10X agents and operations",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.social_hub_api_origin, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/v1")
app.include_router(tasks.router, prefix="/v1")
app.include_router(artifacts.router, prefix="/v1")
app.include_router(handoffs.router, prefix="/v1")
app.include_router(threads.router, prefix="/v1")
app.include_router(agents.router, prefix="/v1")
app.include_router(flow_health.router, prefix="/v1")  # FLOW health checks
app.include_router(hermes_skills.router, prefix="/v1")  # Hermes skill loop
app.include_router(openclaw_intake.router, prefix="/v1")  # OpenClaw intake and routing
app.include_router(agent_zero_reviews.router, prefix="/v1")  # Agent Zero review enforcement

# Skill extraction background job
skill_extraction_job = None

# Redis queue service (initialized on startup)
redis_queue_service = None


@app.on_event("startup")
async def startup_services():
    """Initialize all FLOW services on app startup"""
    global skill_extraction_job, redis_queue_service
    
    # Initialize Redis queue service
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        redis_client = await get_redis_client(redis_url)
        redis_queue_service = RedisQueueService(redis_client)
        openclaw_intake.redis_queue_service = redis_queue_service
        print(f"✓ Redis queue service initialized: {redis_url}")
    except Exception as e:
        print(f"✗ Failed to initialize Redis: {e}")
        redis_queue_service = None
    
    # Initialize skill extraction background job
    try:
        skill_extraction_job = SkillExtractionJob(interval_seconds=300)  # Run every 5 minutes
        asyncio.create_task(skill_extraction_job.start())
        print("✓ Skill extraction job started")
    except Exception as e:
        print(f"✗ Failed to start skill extraction job: {e}")
        skill_extraction_job = None


@app.on_event("shutdown")
async def shutdown_services():
    """Clean up services on app shutdown"""
    global skill_extraction_job, redis_queue_service
    
    # Stop skill extraction job
    if skill_extraction_job:
        await skill_extraction_job.stop()
    
    # Close Redis connection
    if redis_queue_service:
        try:
            await redis_queue_service.redis.close()
            print("✓ Redis connection closed")
        except Exception as e:
            print(f"✗ Error closing Redis: {e}")

