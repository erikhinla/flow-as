"""Validate governed FAAS task envelopes and assign a worker lane."""

import json
import logging
import os
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
from datetime import datetime

import jsonschema
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.flow_job_record import JobRecord, JobStatus

logger = logging.getLogger(__name__)


def _load_task_envelope_schema() -> Dict[str, Any]:
    env_path = os.getenv("TASK_ENVELOPE_SCHEMA_PATH")
    candidate_paths = []
    if env_path:
        candidate_paths.append(Path(env_path))
    current_file = Path(__file__).resolve()
    parents = current_file.parents
    candidate_paths.extend([
        parents[2] / "schemas" / "task_envelope.schema.json",
        *([parents[i] / "schemas" / "task_envelope.schema.json" for i in range(3, min(len(parents), 6))]),
        Path.cwd() / "schemas" / "task_envelope.schema.json",
        Path("/app/schemas/task_envelope.schema.json"),
    ])
    for path in candidate_paths:
        if not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8") as schema_file:
                logger.info("Loaded task envelope schema from %s", path)
                return json.load(schema_file)
        except Exception as exc:
            logger.warning("Failed loading task envelope schema at %s: %s", path, exc)
    logger.warning("Could not load task_envelope.schema.json from any known path")
    return {}


TASK_ENVELOPE_SCHEMA = _load_task_envelope_schema()


class EnvelopeValidationService:
    """Enforce one task, one governed owner, and one return path."""

    VALID_SOURCES = ['manual', 'webhook', 'github_action', 'scheduled', 'discord', 'landing_page', 'proof']
    VALID_TASK_TYPES = [
        'classification', 'rewrite', 'content_prep', 'artifact_production',
        'implementation', 'skill_extraction', 'healthcheck'
    ]
    VALID_RISK_TIERS = ['low', 'medium', 'high']
    VALID_OWNERS = ['openclaw', 'hermes', 'agent_zero']
    ROUTING_RULES = {
        'classification': 'openclaw',
        'rewrite': 'openclaw',
        'content_prep': 'hermes',
        'artifact_production': 'hermes',
        'implementation': 'agent_zero',
        'skill_extraction': 'hermes',
        'healthcheck': 'hermes',
    }

    @staticmethod
    def validate_schema(envelope: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if not TASK_ENVELOPE_SCHEMA:
            logger.warning("Schema not loaded, skipping schema validation")
            return True, None
        try:
            jsonschema.validate(instance=envelope, schema=TASK_ENVELOPE_SCHEMA)
            return True, None
        except jsonschema.ValidationError as exc:
            return False, f"Schema validation failed: {exc.message}"
        except Exception as exc:
            return False, f"Schema validation error: {str(exc)}"

    @staticmethod
    def validate_business_rules(envelope: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        risk_tier = envelope.get('risk_tier')
        task_type = envelope.get('task_type')
        preferred = envelope.get('preferred_owner')
        owner_role = envelope.get('owner_role')
        if risk_tier not in EnvelopeValidationService.VALID_RISK_TIERS:
            return False, f"Invalid risk_tier '{risk_tier}'. Must be low, medium, or high"
        if task_type not in EnvelopeValidationService.VALID_TASK_TYPES:
            return False, f"Invalid task_type '{task_type}'"
        for label, owner in [('preferred_owner', preferred), ('owner_role', owner_role)]:
            if owner and owner not in EnvelopeValidationService.VALID_OWNERS:
                return False, f"Invalid {label} '{owner}'"
        if preferred and owner_role and preferred != owner_role:
            return False, "preferred_owner and owner_role must identify the same worker"
        requested_owner = owner_role or preferred
        default_owner = EnvelopeValidationService.ROUTING_RULES[task_type]
        if requested_owner and requested_owner != default_owner:
            return False, f"task_type={task_type} routes to owner_role={default_owner}"
        if risk_tier == 'high':
            if default_owner != 'agent_zero':
                return False, "High-risk work routes only to agent_zero"
            if not envelope.get('review_required') or not envelope.get('execution_approval_required'):
                return False, "High-risk work requires review_required=true and execution_approval_required=true"
        if len(envelope.get('goal', '')) < 10:
            return False, "Goal must be at least 10 characters and observable"
        if task_type == 'implementation' and envelope.get('rollback_required'):
            if not envelope.get('inputs', {}).get('rollback_plan'):
                logger.info("Rollback plan will be created during review for %s", envelope.get('task_id'))
        return True, None

    @staticmethod
    def determine_owner(envelope: Dict[str, Any]) -> str:
        return EnvelopeValidationService.ROUTING_RULES[envelope['task_type']]

    @staticmethod
    async def validate_and_create_job(
        db: AsyncSession, envelope: Dict[str, Any], source: str = 'manual'
    ) -> Tuple[bool, Optional[str], Optional[JobRecord], bool]:
        """Return success, error, job, created_new; task_id is idempotent."""
        existing_result = await db.execute(select(JobRecord).where(JobRecord.task_id == envelope.get('task_id')))
        existing = existing_result.scalar_one_or_none()
        if existing:
            return True, None, existing, False
        schema_valid, schema_error = EnvelopeValidationService.validate_schema(envelope)
        if not schema_valid:
            return False, schema_error, None, False
        rules_valid, rules_error = EnvelopeValidationService.validate_business_rules(envelope)
        if not rules_valid:
            return False, rules_error, None, False
        owner = EnvelopeValidationService.determine_owner(envelope)
        try:
            job = JobRecord(
                job_id=envelope['task_id'], task_id=envelope['task_id'], owner=owner,
                status=JobStatus.VALIDATED.value, task_type=envelope['task_type'],
                risk_tier=envelope['risk_tier'], priority=envelope.get('priority', 'normal'),
                title=envelope.get('title'), goal=envelope.get('goal'), source=source,
                inputs=envelope.get('inputs', {}), output_required=envelope.get('output_required'),
                review_required=bool(envelope.get('review_required')),
                execution_approval_required=bool(envelope.get('execution_approval_required')),
                created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
            )
            db.add(job)
            await db.commit()
            await db.refresh(job)
            return True, None, job, True
        except Exception as exc:
            await db.rollback()
            logger.error("Error creating job record: %s", exc, exc_info=True)
            return False, f"Failed to create job: {str(exc)}", None, False


class RoutingService:
    """Legacy helper kept aligned with canonical queue owner names."""

    @staticmethod
    async def route_job_to_queue(redis_client, job: JobRecord, envelope: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        try:
            queue_key = f"flow:{job.owner}:jobs"
            await redis_client.lpush(queue_key, job.job_id)
            job.status = JobStatus.QUEUED.value
            job.updated_at = datetime.utcnow()
            return True, None
        except Exception as exc:
            return False, f"Failed to route job: {str(exc)}"

    @staticmethod
    def get_queue_name(owner: str) -> str:
        return f"flow:{owner}:jobs"

    @staticmethod
    async def get_queue_depth(redis_client, owner: str) -> int:
        return await redis_client.llen(RoutingService.get_queue_name(owner)) or 0

    @staticmethod
    async def get_all_queue_depths(redis_client) -> Dict[str, int]:
        return {owner: await RoutingService.get_queue_depth(redis_client, owner) for owner in EnvelopeValidationService.VALID_OWNERS}
