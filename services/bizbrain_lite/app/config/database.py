"""
FLOW Agent OS Database Configuration

Postgres connection pool setup for durable job_records, reflection_records, skill_records.
Uses SQLAlchemy AsyncIO for async/await support.
"""

import os
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Get Postgres URI from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://flow_user:flow_password@localhost:5432/flow_agent_os"
)

# Connection pool configuration
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))  # Recycle connections after 1 hour
POOL_PRE_PING = os.getenv("DB_POOL_PRE_PING", "true").lower() == "true"

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=POOL_PRE_PING,  # Verify connections before using
    connect_args={
        "timeout": 10,
        "command_timeout": 30,
        "server_settings": {
            "application_name": "flow_agent_os",
            "jit": "off",
        }
    }
)

# Session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injection for FastAPI routes.
    
    Usage:
        @app.get("/tasks")
        async def list_tasks(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """
    Initialize database schema.
    
    Creates all tables defined in SQLAlchemy models.
    Run this once on startup.
    """
    from app.models.flow_job_record import Base as JobBase
    from app.models.flow_reflection_record import Base as ReflectionBase
    from app.models.flow_skill_record import Base as SkillBase
    from app.models.user import Base as UserBase
    from app.models.ai_readiness_report import Base as AIReadinessBase
    from app.models.concierge_booking import Base as ConciergeBase
    
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(JobBase.metadata.create_all)
        await conn.run_sync(ReflectionBase.metadata.create_all)
        await conn.run_sync(SkillBase.metadata.create_all)
        await conn.run_sync(UserBase.metadata.create_all)
        await conn.run_sync(AIReadinessBase.metadata.create_all)
        await conn.run_sync(ConciergeBase.metadata.create_all)


async def health_check() -> bool:
    """
    Check if database is reachable.
    
    Returns True if connection successful, False otherwise.
    """
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception:
        return False


async def close_db():
    """
    Close database connection pool.
    
    Run this on shutdown.
    """
    await engine.dispose()
