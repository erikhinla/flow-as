import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agents, artifacts, handoffs, health, tasks, threads, flow_health, hermes_skills
from app.config.settings import get_settings
from app.services.skill_extraction_job import SkillExtractionJob

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

# Skill extraction background job
skill_extraction_job = None


@app.on_event("startup")
async def startup_skill_extraction():
    """Start skill extraction background job on app startup"""
    global skill_extraction_job
    skill_extraction_job = SkillExtractionJob(interval_seconds=300)  # Run every 5 minutes
    asyncio.create_task(skill_extraction_job.start())


@app.on_event("shutdown")
async def shutdown_skill_extraction():
    """Stop skill extraction background job on app shutdown"""
    global skill_extraction_job
    if skill_extraction_job:
        await skill_extraction_job.stop()

