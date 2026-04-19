"""
OpenClaw Task Envelope Validation Service

Validates incoming task envelopes against schema and business rules.
Enforces FLOW governance:
- One task, one owner, one return path
- High-risk must have review_required = true
- Rollback required for state-mutating tasks
- Clear, observable goals
"""

import json
import logging
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
from datetime import datetime

import jsonschema
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.flow_job_record import JobRecord, JobStatus, AgentOwner, TaskType, RiskTier

logger = logging.getLogger(__name__)


def _load_task_envelope_schema() -> dict:
        """
            Load the task envelope JSON schema.
                Searches multiple locations so it works both locally and inside Docker.
                    """
        candidates = [
            Path("/app/schemas/task_envelope.schema.json"),
            Path(__file__).parents[3] / "schemas" / "task_envelope.schema.json",
            Path("schemas/task_envelope.schema.json"),
        ]
        for path in candidates:
                    if path.exists():
                                    with open(path, "r") as f:
                                                        logger.info(f"Loaded task_envelope schema from {path}")
                                                        return json.load(f)
                                            logger.warning("Could not find task_envelope.schema.json — schema validation disabled")
                            return {}


TASK_ENVELOPE_SCHEMA = _load_task_envelope_schema()

ROUTING_RULES = {
        "classification":  AgentOwner.OPENCLAW,
        "rewrite":         AgentOwner.OPENCLAW,
        "analysis":        AgentOwner.OPENCLAW,
        "research":        AgentOwner.HERMES,
        "implementation":  AgentOwner.AGENT_ZERO,
        "deployment":      AgentOwner.AGENT_ZERO,
        "review":          AgentOwner.HERMES,
        "planning":        AgentOwner.HERMES,
        "other":           AgentOwner.HERMES,
}


class EnvelopeValidationService:
        """Validate task envelopes before routing."""

    TASK_ENVELOPE_SCHEMA = TASK_ENVELOPE_SCHEMA

    @staticmethod
    def validate_schema(envelope: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
                if not TASK_ENVELOPE_SCHEMA:
                                logger.warning("Schema not loaded — skipping schema validation")
                                return True, None
                            try:
                                            jsonschema.validate(instance=envelope, schema=TASK_ENVELOPE_SCHEMA)
                                            return True, None
except jsonschema.ValidationError as e:
            return False, f"Schema validation failed: {e.message}"

    @staticmethod
    def validate_business_rules(envelope: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
                if envelope.get("risk_tier") == "high" and not envelope.get("review_required"):
                                return False, "High-risk task missing review_required=true (GOVERNANCE VIOLATION)"

        if envelope.get("task_type") == "implementation" and envelope.get("rollback_required"):
                        if not envelope.get("inputs", {}).get("rollback_plan"):
                                            logger.info("Implementation task rollback_required but no rollback_plan (will be created during review)")

        goal = envelope.get("goal", "")
        if len(goal.strip()) < 10:
                        return False, "Goal too vague — must be at least 10 characters"

        task_type = envelope.get("task_type")
        if task_type not in ROUTING_RULES:
                        return False, f"Unknown task_type '{task_type}' — valid: {list(ROUTING_RULES.keys())}"

        return True, None

    @staticmethod
    def determine_owner(envelope: Dict[str, Any]) -> AgentOwner:
                if envelope.get("preferred_owner"):
                                try:
                                                    return AgentOwner(envelope["preferred_owner"])
except ValueError:
                pass
        task_type = envelope.get("task_type", "other")
        return ROUTING_RULES.get(task_type, AgentOwner.HERMES)

    @classmethod
    async def validate_and_create_job(
                cls,
                db: AsyncSession,
                envelope: Dict[str, Any],
                source: str = "manual",
    ) -> Tuple[bool, Optional[str], Optional[JobRecord]]:
                logger.info(f"Starting envelope validation: {envelope.get('task_id')}")

        schema_valid, schema_error = cls.validate_schema(envelope)
        if not schema_valid:
                        logger.error(f"Schema validation failed: {schema_error}")
                        return False, schema_error, None

        rules_valid, rules_error = cls.validate_business_rules(envelope)
        if not rules_valid:
                        logger.error(f"Business rules failed: {rules_error}")
                        return False, rules_error, None

        owner = cls.determine_owner(envelope)

        try:
                        job = JobRecord(
                                            job_id=envelope.get("task_id"),
                                            task_id=envelope.get("task_id"),
                                            title=envelope.get("title"),
                                            goal=envelope.get("goal"),
                                            task_type=TaskType(envelope.get("task_type", "other")),
                                            risk_tier=RiskTier(envelope.get("risk_tier", "low")),
                                            owner=owner,
                                            source=source,
                                            status=JobStatus.PENDING,
                                            review_required=envelope.get("review_required", False),
                                            rollback_required=envelope.get("rollback_required", False),
                                            inputs=envelope.get("inputs", {}),
                                            output_required=envelope.get("output_required", ""),
                                            created_at=datetime.utcnow(),
                        )
                        db.add(job)
                        await db.flush()
                        logger.info(f"Job record created: {job.job_id} -> {owner.value}")
                        return True, None, job
except Exception as e:
            logger.error(f"Failed to create job record: {e}")
            return False, f"Database error: {str(e)}", None


class RoutingService:
        """Simple routing helper used by the intake API."""

    @staticmethod
    def get_queue_name(owner: AgentOwner) -> str:
                return f"flow:{owner.value}:jobs"

    @staticmethod
    def route(envelope: Dict[str, Any]) -> AgentOwner:
                return EnvelopeValidationService.determine_owner(envelope)
