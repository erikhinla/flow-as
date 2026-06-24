"""Database configuration and session management.

Provides:
- Async SQLAlchemy session factory
- Database initialization (table creation)
- Connection pool management
"""

import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.config.settings import get_settings
from app.models.flow_job_record import Base as JobBase
from app.models.flow_reflection_record import Base as ReflectionBase
from app.models.audit_log import Base as AuditBase

logger = logging.getLogger(__name__)

settings = get_settings()

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    connect_args={"timeout": 10},
)

# Create async session factory
SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db_session() -> AsyncSession:
    """Get database session for dependency injection."""
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    """Initialize database tables.

    Creates all tables defined in Base metadata if they don't exist.
    """
    async with engine.begin() as conn:
        await conn.run_sync(JobBase.metadata.create_all)
        await conn.run_sync(ReflectionBase.metadata.create_all)
        await conn.run_sync(AuditBase.metadata.create_all)


async def close_db() -> None:
    """Close database connection pool."""
    await engine.dispose()
