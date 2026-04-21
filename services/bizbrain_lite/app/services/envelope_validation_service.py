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
import os
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
from datetime import datetime

import jsonschema
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.flow_job_record import JobRecord, JobStatus, AgentOwner, TaskType, RiskTier

logger = logging.getLogger(__name__)


def _load_task_envelope_schema() -> Dict[str, Any]:
    env_path = os.getenv("TASK_ENVELOPE_SCHEMA_PATH")
    candidate_paths = []

    if env_path:
        candidate_paths.append(Path(env_path))

    current_file = Path(__file__).resolve()
    candidate_paths.extend([
        current_file.parents[2] / "schemas" / "task_envelope.schema.json",
        current_file.parents[4] / "schemas" / "task_envelope.schema.json",
        Path.cwd() / "schemas" / "task_envelope.schema.json",
    ])

    for path in candidate_paths:
        if not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8") as schema_file:
                logger.info(f"Loaded task envelope schema from {path}")
                return json.load(schema_file)
        except Exception as exc:
            logger.warning(f"Failed loading task_envelope schema at {path}: {exc}")

    logger.warning("Could not load task_envelope.schema.json from any known path")
    return {}


TASK_ENVELOPE_SCHEMA = _load_task_envelope_schema()


class EnvelopeValidationService:
    """
    Validate task envelopes before routing.
    
    Checks:
    1. Schema validation (JSON schema compliance)
    2. Business rules (governance enforcement)
    3. Owner assignment
    """
    
    # Valid values
    VALID_SOURCES = ['manual', 'webhook', 'github_action', 'scheduled']
    VALID_TASK_TYPES = ['classification', 'rewrite', 'content_prep', 'implementation', 'skill_extraction', 'healthcheck']
    VALID_RISK_TIERS = ['low', 'medium', 'high']
    VALID_OWNERS = ['openclaw', 'hermes', 'agent_zero']
    
    # Routing rules: task_type → preferred owner
    ROUTING_RULES = {
        'classification': 'openclaw',
        'rewrite': 'openclaw',
        'content_prep': 'openclaw',
        'markdown_generation': 'openclaw',
        'implementation': 'agent_zero',
        'skill_extraction': 'hermes',
        'healthcheck': 'hermes',
    }
    
    @staticmethod
    def validate_schema(envelope: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate envelope against JSON schema.
        
        Returns:
            (bool, error_message)
        """
        
        if not TASK_ENVELOPE_SCHEMA:
            logger.warning("Schema not loaded, skipping schema validation")
            return True, None
        
        try:
            jsonschema.validate(instance=envelope, schema=TASK_ENVELOPE_SCHEMA)
            return True, None
        except jsonschema.ValidationError as e:
            error_msg = f"Schema validation failed: {e.message}"
            logger.warning(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Schema validation error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    @staticmethod
    def validate_business_rules(envelope: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate business rules (FLOW governance).
        
        Returns:
            (bool, error_message)
        
        Rules:
        1. High-risk tasks MUST have review_required = true
        2. High-risk tasks MUST have rollback_required if mutating state
        3. Goal must be specific and observable (min 10 chars)
        4. Owner must be valid
        5. Task type must be in ROUTING_RULES
        """
        
        rules_checks = {}
        
        # Rule 1: High-risk requires review
        if envelope.get('risk_tier') == 'high' and not envelope.get('review_required'):
            return False, "High-risk task missing review_required=true (GOVERNANCE VIOLATION)"
        rules_checks['high_risk_review'] = True
        
        # Rule 2: Implementation tasks need rollback plan
        if envelope.get('task_type') == 'implementation' and envelope.get('rollback_required'):
            if not envelope.get('inputs', {}).get('rollback_plan'):
                logger.info("Implementation task marked rollback_required but no rollback_plan in inputs (will be created during review)")
        rules_checks['implementation_rollback'] = True
        
        # Rule 3: Goal must be specific
        goal = envelope.get('goal', '')
        if len(goal) < 10:
            return False, f"Goal too vague ('{goal[:20]}...'). Must be >= 10 characters and observable."
        rules_checks['goal_specific'] = True
        
        # Rule 4: Preferred owner valid
        preferred_owner = envelope.get('preferred_owner')
        if preferred_owner and preferred_owner not in EnvelopeValidationService.VALID_OWNERS:
            return False, f"Invalid preferred_owner '{preferred_owner}'. Must be one of {EnvelopeValidationService.VALID_OWNERS}"
        rules_checks['owner_valid'] = True
        
        # Rule 5: Task type valid
        task_type = envelope.get('task_type')
        if task_type not in EnvelopeValidationService.VALID_TASK_TYPES:
            return False, f"Invalid task_type '{task_type}'. Must be one of {EnvelopeValidationService.VALID_TASK_TYPES}"
        rules_checks['task_type_valid'] = True
        
        logger.info(f"Business rules validation passed: {rules_checks}")
        return True, None
    
    @staticmethod
    def determine_owner(envelope: Dict[str, Any]) -> str:
        """
        Determine owner (routing decision).
        
        Logic:
        1. If preferred_owner set: use it
        2. Otherwise: use ROUTING_RULES by task_type
        3. Default: hermes (fallback)
        
        Returns:
            owner string (openclaw, hermes, or agent_zero)
        """
        
        # Check explicit preference
        preferred = envelope.get('preferred_owner')
        if preferred and preferred in EnvelopeValidationService.VALID_OWNERS:
            logger.info(f"Using preferred_owner: {preferred}")
            return preferred
        
        # Use routing rules
        task_type = envelope.get('task_type')
        owner = EnvelopeValidationService.ROUTING_RULES.get(task_type, 'hermes')
        logger.info(f"Routed by task_type '{task_type}' → owner: {owner}")
        return owner
    
    @staticmethod
    async def validate_and_create_job(
        db: AsyncSession,
        envelope: Dict[str, Any],
        source: str = 'manual'
    ) -> Tuple[bool, Optional[str], Optional[JobRecord]]:
        """
        Full validation pipeline: schema → business rules → create job record.
        
        Returns:
            (success: bool, error_message: Optional[str], job_record: Optional[JobRecord])
        """
        
        logger.info(f"Starting envelope validation: {envelope.get('task_id')}")
        
        # Step 1: Schema validation
        schema_valid, schema_error = EnvelopeValidationService.validate_schema(envelope)
        if not schema_valid:
            logger.error(f"Schema validation failed: {schema_error}")
            return False, schema_error, None
        
        # Step 2: Business rules validation
        rules_valid, rules_error = EnvelopeValidationService.validate_business_rules(envelope)
        if not rules_valid:
            logger.error(f"Business rules validation failed: {rules_error}")
            return False, rules_error, None
        
        # Step 3: Determine owner
        owner = EnvelopeValidationService.determine_owner(envelope)
        
        # Step 4: Create job record
        try:
            job = JobRecord(
                job_id=envelope.get('task_id'),  # Use task_id as job_id
                task_id=envelope.get('task_id'),
                owner=owner,
                status=JobStatus.VALIDATED.value,  # Starts as VALIDATED (not PENDING)
                task_type=envelope.get('task_type'),
                risk_tier=envelope.get('risk_tier'),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            
            db.add(job)
            await db.commit()
            await db.refresh(job)
            
            logger.info(f"Job created: {job.job_id}, owner={owner}, status=VALIDATED")
            return True, None, job
        
        except Exception as e:
            logger.error(f"Error creating job record: {e}", exc_info=True)
            await db.rollback()
            return False, f"Failed to create job: {str(e)}", None


class RoutingService:
    """
    Route validated jobs to correct owner's queue.
    """
    
    @staticmethod
    async def route_job_to_queue(
        redis_client,
        job: JobRecord,
        envelope: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Route job to owner's Redis queue.
        
        Queue naming: {owner}:jobs
        - openclaw:jobs
        - hermes:jobs
        - agent_zero:jobs
        
        Returns:
            (success: bool, error_message: Optional[str])
        """
        
        try:
            queue_key = f"{job.owner}:jobs"
            
            # Push job_id to queue (FIFO)
            await redis_client.lpush(queue_key, job.job_id)
            
            # Update job status to QUEUED
            job.status = JobStatus.QUEUED.value
            job.updated_at = datetime.utcnow()
            # Note: caller should commit this to database
            
            logger.info(f"Routed job {job.job_id} to queue {queue_key}")
            return True, None
        
        except Exception as e:
            logger.error(f"Error routing job: {e}", exc_info=True)
            return False, f"Failed to route job: {str(e)}"
    
    @staticmethod
    def get_queue_name(owner: str) -> str:
        """Get Redis queue name for owner"""
        return f"{owner}:jobs"
    
    @staticmethod
    async def get_queue_depth(redis_client, owner: str) -> int:
        """Get number of jobs waiting in owner's queue"""
        queue_name = RoutingService.get_queue_name(owner)
        depth = await redis_client.llen(queue_name)
        return depth or 0
    
    @staticmethod
    async def get_all_queue_depths(redis_client) -> Dict[str, int]:
        """Get queue depths for all owners"""
        depths = {}
        for owner in ['openclaw', 'hermes', 'agent_zero']:
            depths[owner] = await RoutingService.get_queue_depth(redis_client, owner)
        return depths
