"""
Hermes Skill Extraction Background Job

Runs periodically (every 5 minutes) to process pending reflections.
Extracts reusable patterns and indexes them for future task enrichment.

This is part of the recursive learning loop:
1. Task executes → reflection written
2. Background job reads reflections → extracts skills
3. Skills indexed by task_type + context
4. Next similar task: retrieve skills → enrich execution
5. Track success/failure → confidence updates
"""

import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config.database import DATABASE_URL
from app.services.skill_extraction_service import SkillExtractionService

logger = logging.getLogger(__name__)


class SkillExtractionJob:
    """
    Background job for periodic skill extraction.
    
    Can be run as:
    - Scheduled task (APScheduler)
    - Celery task
    - FastAPI BackgroundTask
    - Standalone asyncio loop
    """
    
    def __init__(self, interval_seconds: int = 300):
        """
        Initialize extraction job.
        
        Args:
            interval_seconds: How often to run extraction (default: 5 min)
        """
        self.interval_seconds = interval_seconds
        self.running = False
        
        # Create session factory
        self.engine = None
        self.async_session = None
    
    async def initialize(self):
        """Set up database connection"""
        self.engine = create_async_engine(DATABASE_URL, echo=False)
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    
    async def shutdown(self):
        """Clean up database connection"""
        if self.engine:
            await self.engine.dispose()
    
    async def run_extraction_pass(self):
        """Execute one skill extraction pass"""
        async with self.async_session() as db:
            try:
                logger.info("=== Starting skill extraction pass ===")
                stats = await SkillExtractionService.process_pending_reflections(db)
                logger.info(f"Extraction pass complete: extracted={stats['extracted']}, "
                           f"skipped={stats['skipped']}, errors={stats['errors']}")
                return stats
            except Exception as e:
                logger.error(f"Error during extraction pass: {e}", exc_info=True)
                return {'extracted': 0, 'skipped': 0, 'errors': 1}
    
    async def start(self):
        """Start the background job loop"""
        await self.initialize()
        self.running = True
        
        logger.info(f"Starting skill extraction job (interval: {self.interval_seconds}s)")
        
        try:
            while self.running:
                # Run extraction
                await self.run_extraction_pass()
                
                # Wait for next interval
                await asyncio.sleep(self.interval_seconds)
        
        except asyncio.CancelledError:
            logger.info("Skill extraction job cancelled")
        except Exception as e:
            logger.error(f"Skill extraction job error: {e}", exc_info=True)
        finally:
            await self.shutdown()
    
    async def stop(self):
        """Stop the background job"""
        self.running = False
        logger.info("Stopping skill extraction job")


# FastAPI integration example
async def start_skill_extraction_job(app):
    """
    Start skill extraction job on FastAPI app startup.
    
    Usage in main.py:
    
        from app.services.skill_extraction_job import start_skill_extraction_job, stop_skill_extraction_job
        
        job = None
        
        @app.on_event("startup")
        async def startup():
            global job
            job = SkillExtractionJob(interval_seconds=300)
            asyncio.create_task(job.start())
        
        @app.on_event("shutdown")
        async def shutdown():
            global job
            if job:
                await job.stop()
    """
    logger.info("Initializing skill extraction job")


# Standalone runner (for testing or cron execution)
async def run_once():
    """Run extraction once and exit (useful for cron jobs)"""
    job = SkillExtractionJob()
    await job.initialize()
    try:
        stats = await job.run_extraction_pass()
        return stats
    finally:
        await job.shutdown()


if __name__ == "__main__":
    """
    Run skill extraction as standalone script.
    
    Usage:
        python -m app.services.skill_extraction_job
    """
    logger.basicConfig(level=logging.INFO)
    stats = asyncio.run(run_once())
    print(f"Extraction stats: {stats}")
