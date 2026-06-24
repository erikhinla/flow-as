"""Base class for all FAAS agent executors.

Provides the core execution loop:
1. Claim job from queue with lease
2. Write pre-execution reflection (strategy)
3. Execute task
4. Handle mid-execution adaptation (if applicable)
5. Write post-execution reflection (learning)
6. Complete job via FAAS API

All state changes flow through FAAS proof-of-work API for audit trail.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db_session
from app.models.flow_job_record import JobRecord, JobStatus
from app.services.redis_queue_service import RedisQueueService

logger = logging.getLogger(__name__)


class ExecutionResult:
    """Result of task execution."""

    def __init__(
        self,
        success: bool,
        artifact_path: str,
        summary: str,
        error_message: Optional[str] = None,
        can_retry: bool = False,
        adaptation_info: Optional[Dict[str, Any]] = None,
    ):
        self.success = success
        self.artifact_path = artifact_path
        self.summary = summary
        self.error_message = error_message
        self.can_retry = can_retry
        self.adaptation_info = adaptation_info or {}


class AgentExecutor(ABC):
    """Abstract base class for autonomous FAAS agent executors.

    Subclasses must implement:
    - owner: str ("openclaw", "hermes", "agent_zero")
    - execute_task(job: JobRecord) -> ExecutionResult
    - get_task_context(job: JobRecord) -> Dict[str, Any]

    The base class provides:
    - Job claim/lease management
    - Pre/mid/post execution reflection sequencing
    - Error handling and escalation
    - State update via FAAS API
    """

    owner: str
    lease_seconds: int = 900  # 15 minutes default
    max_reflection_sequences: int = 10

    def __init__(
        self,
        db_session_maker,
        redis_queue_service: RedisQueueService,
        worker_id: str = None,
    ):
        self.db_session_maker = db_session_maker
        self.queue_service = redis_queue_service
        self.worker_id = worker_id or f"{self.owner}-{uuid4().hex[:8]}"
        self.api_base_url = "http://localhost:18000/v1"  # TODO: from config
        self.current_job: Optional[JobRecord] = None
        self.reflection_sequence: int = 0

    async def run(self, check_interval: int = 5):
        """Main executor loop.

        Continuously:
        1. Check for jobs in queue
        2. Claim job with lease
        3. Execute with full reflection cycle
        4. Handle errors and escalation
        5. Release lease
        """
        logger.info(f"{self.owner} executor started: {self.worker_id}")

        while True:
            try:
                await self.process_one_job()
            except Exception as exc:
                logger.error(f"Error in {self.owner} executor loop: {exc}", exc_info=True)
                await asyncio.sleep(check_interval)

    async def process_one_job(self, timeout: int = 30) -> bool:
        """Process one job from queue. Returns True if job was processed."""
        # 1. Dequeue job (blocking with timeout)
        job_id = await self.queue_service.dequeue_job(self.owner, timeout=timeout)
        if not job_id:
            return False

        async with self.db_session_maker() as db:
            try:
                # 2. Fetch full job record
                from sqlalchemy import select

                result = await db.execute(
                    select(JobRecord).where(JobRecord.job_id == job_id)
                )
                job = result.scalar_one_or_none()
                if not job:
                    logger.warning(f"Job {job_id} not found in database")
                    return False

                self.current_job = job
                self.reflection_sequence = 0

                # 3. Claim job with lease
                await self._claim_job(db, job)

                # 4. Write pre-execution reflection (strategy)
                await self._write_reflection(
                    db,
                    job,
                    sequence=1,
                    what_worked="Pre-execution setup",
                    what_failed="None",
                    pattern_observed=f"Executing: {job.goal}",
                    context_type="pre_execution",
                )

                # 5. Get execution context
                context = await self.get_task_context(job)

                # 6. Execute task
                logger.info(f"Executing {self.owner} task: {job.job_id}")
                result = await self.execute_task(job)

                if result.success:
                    # 7. Write success reflection
                    await self._write_reflection(
                        db,
                        job,
                        sequence=2,
                        what_worked=result.summary,
                        what_failed="None",
                        pattern_observed=f"Task completed successfully: {job.task_type}",
                        success_signal=f"Artifact written to {result.artifact_path}",
                    )

                    # 8. Complete job
                    await self._complete_job(db, job, result.artifact_path)
                    logger.info(f"Job completed: {job.job_id}")

                else:
                    # 9. Handle failure with potential mid-execution adaptation
                    if result.can_retry and self.reflection_sequence < self.max_reflection_sequences:
                        logger.info(
                            f"Job {job.job_id} failed but can adapt. "
                            f"Reflection sequence: {self.reflection_sequence}"
                        )

                        # Write mid-execution adaptation reflection
                        await self._write_reflection(
                            db,
                            job,
                            sequence=self.reflection_sequence + 1,
                            what_worked="Initial attempt",
                            what_failed=result.error_message,
                            pattern_observed=f"Attempting adaptation strategy",
                            failure_signal=result.error_message,
                            context_type="mid_execution_adaptation",
                        )

                        # Retry with adaptation
                        adapted_result = await self.adapt_and_retry(job, result, context)

                        if adapted_result.success:
                            await self._write_reflection(
                                db,
                                job,
                                sequence=self.reflection_sequence + 2,
                                what_worked=adapted_result.summary,
                                what_failed="None",
                                pattern_observed=f"Adapted strategy succeeded",
                                success_signal=f"Artifact: {adapted_result.artifact_path}",
                            )
                            await self._complete_job(db, job, adapted_result.artifact_path)
                            logger.info(f"Job completed after adaptation: {job.job_id}")
                            return True

                    # Failure without retry or retry exhausted
                    await self._write_reflection(
                        db,
                        job,
                        sequence=self.reflection_sequence + 1,
                        what_worked="None",
                        what_failed=result.error_message,
                        failure_signal=result.error_message,
                        context_type="post_execution_failure",
                    )

                    await self._fail_job(db, job, result.error_message)
                    logger.error(f"Job failed: {job.job_id}: {result.error_message}")

                return True

            except Exception as exc:
                logger.error(f"Error processing job {job_id}: {exc}", exc_info=True)
                if self.current_job:
                    await self._fail_job(
                        db, self.current_job, f"Executor error: {str(exc)}"
                    )
                return False

    async def _claim_job(self, db: AsyncSession, job: JobRecord) -> None:
        """Claim job with lease via FAAS API."""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base_url}/jobs/{job.task_id}/claim",
                json={
                    "worker_id": self.worker_id,
                    "owner": self.owner,
                    "lease_seconds": self.lease_seconds,
                },
                headers={"Authorization": "Bearer test-token"},  # TODO: from config
            )
            if response.status_code != 200:
                raise RuntimeError(
                    f"Failed to claim job {job.job_id}: {response.text}"
                )

        logger.debug(f"Job claimed: {job.job_id} by {self.worker_id}")

    async def _complete_job(self, db: AsyncSession, job: JobRecord, result_pointer: str) -> None:
        """Complete job via FAAS API."""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base_url}/jobs/{job.task_id}/complete",
                json={
                    "worker_id": self.worker_id,
                    "result_pointer": result_pointer,
                    "needs_review": job.review_required,
                },
                headers={"Authorization": "Bearer test-token"},
            )
            if response.status_code != 200:
                raise RuntimeError(
                    f"Failed to complete job {job.job_id}: {response.text}"
                )

        logger.debug(f"Job completed via FAAS: {job.job_id}")

    async def _fail_job(self, db: AsyncSession, job: JobRecord, error_message: str) -> None:
        """Fail job via FAAS API."""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base_url}/jobs/{job.task_id}/fail",
                json={"worker_id": self.worker_id, "error_message": error_message},
                headers={"Authorization": "Bearer test-token"},
            )
            if response.status_code != 200:
                logger.error(f"Failed to fail job {job.job_id}: {response.text}")

    async def _write_reflection(
        self,
        db: AsyncSession,
        job: JobRecord,
        sequence: int,
        what_worked: str,
        what_failed: str,
        pattern_observed: Optional[str] = None,
        context_type: Optional[str] = None,
        tool_sequence: Optional[list] = None,
        success_signal: Optional[str] = None,
        failure_signal: Optional[str] = None,
    ) -> None:
        """Write reflection via FAAS API."""
        import httpx

        self.reflection_sequence = max(self.reflection_sequence, sequence)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base_url}/jobs/{job.task_id}/reflections",
                json={
                    "worker_id": self.worker_id,
                    "sequence_number": sequence,
                    "what_worked": what_worked,
                    "what_failed": what_failed,
                    "pattern_observed": pattern_observed,
                    "context_type": context_type or f"{self.owner}_execution",
                    "tool_sequence": tool_sequence,
                    "success_signal": success_signal,
                    "failure_signal": failure_signal,
                },
                headers={"Authorization": "Bearer test-token"},
            )
            if response.status_code != 200:
                logger.warning(f"Failed to write reflection: {response.text}")

    @abstractmethod
    async def execute_task(self, job: JobRecord) -> ExecutionResult:
        """Execute the task. Subclasses must implement.

        Args:
            job: JobRecord with task details, inputs, goal, etc.

        Returns:
            ExecutionResult with success flag, artifact path, and summary.
        """
        pass

    @abstractmethod
    async def get_task_context(self, job: JobRecord) -> Dict[str, Any]:
        """Get execution context for the task.

        Args:
            job: JobRecord

        Returns:
            Dict with task-specific context (skills, prior patterns, etc.)
        """
        pass

    async def adapt_and_retry(
        self, job: JobRecord, failed_result: ExecutionResult, context: Dict[str, Any]
    ) -> ExecutionResult:
        """Adapt strategy and retry after failure. Override in subclass if needed.

        Default: re-execute with no changes (allows subclasses to override).
        """
        logger.info(f"Retrying {job.job_id} with potential adaptation")
        return await self.execute_task(job)
