from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agents, artifacts, handoffs, health, tasks, threads
from app.config.settings import get_settings

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

