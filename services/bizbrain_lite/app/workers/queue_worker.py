"""
FLOW queue worker — full execution loop.

1. BRPOP job_id from Redis owner queue
2. Mark job ACTIVE in Postgres
3. Execute the task through the assigned real agent runtime
4. Write output artifact to runtime/reviews/{job_id}/output.md
5. Mark job COMPLETED in Postgres
6. POST completion embed to Discord webhook
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import async_session
from app.config.settings import get_settings
from app.models.flow_job_record import JobRecord, JobStatus
from app.services.redis_queue_service import RedisQueueService, get_redis_client
from app.services.audit_service import record_audit_event
from app.services.automated_learning_service import AutomatedLearningService
from app.services.skill_loader import SkillLoader, PerformanceContextLoader
from app.models.audit_log import AuditEventType


logging.basicConfig(
    level=os.getenv("FLOW_WORKER_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("flow.queue_worker")

# ── System prompts per agent ──────────────────────────────────────────────────

SYSTEM_PROMPTS: dict[str, str] = {
    "hermes": (
        "You are Hermes, an expert marketing strategist and copywriter. "
        "You produce high-quality, conversion-focused content: emails, social captions, "
        "campaign briefs, ad copy, and content strategy. Be direct, punchy, and professional. "
        "Return well-structured Markdown with clear sections."
    ),
    "openclaw": (
        "You are OpenClaw, a sharp business analyst and operations strategist. "
        "You handle classification, routing decisions, research briefs, and structured analysis. "
        "Return clear, structured Markdown with actionable outputs."
    ),
    "agent_zero": (
        "You are Agent Zero, a senior full-stack developer and implementation specialist. "
        "You build landing pages, write code, create structured deliverables, and handle "
        "complex multi-step implementations. Return complete, production-ready output in Markdown. "
        "For HTML/CSS tasks, include full working code blocks."
    ),
}


def load_tbtx_canon_context() -> str:
    """Load the smallest authoritative TBTX context needed for model work.

    The Canon is mounted read-only in the worker. It is intentionally loaded at
    execution time so a Canon update is used without rebuilding model prompts.
    """
    root = Path(os.getenv("TBTX_CANON_ROOT", "/app/canon/TBTX_CANON"))
    relative_paths = (
        "00_CANON/00_READ_FIRST.md",
        "00_CANON/03_MUST_Framework.md",
        "00_CANON/06_Brand_Constitution.md",
        "00_CANON/07_Vocabulary.md",
        "03_PRODUCTS/Digital_Fog.md",
        "03_PRODUCTS/Digital_Friction.md",
    )
    sections: list[str] = []
    remaining = 28_000
    for relative_path in relative_paths:
        path = root / relative_path
        if not path.is_file() or remaining <= 0:
            continue
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        excerpt = text[:remaining]
        sections.append(f"## {relative_path}\n{excerpt}")
        remaining -= len(excerpt)
    if not sections:
        logger.warning("No TBTX Canon files were available at %s", root)
        return ""
    return "\n\n".join(sections)


# ── Agent runtime execution ───────────────────────────────────────────────────

async def build_execution_prompt(
    goal: str,
    title: str,
    task_type: str,
    owner: str,
    session: AsyncSession = None
) -> str:
    """Build the Canon-bound prompt handed to the assigned agent runtime."""
    skills_context = ""
    performance_context = ""

    if session:
        try:
            # Load relevant skills
            relevant_skills = await SkillLoader.load_relevant_skills(
                session, task_type, owner, limit=3
            )
            if relevant_skills:
                skills_context = SkillLoader.format_skills_for_prompt(relevant_skills)
                logger.debug("Loaded %d skills for enhanced context", len(relevant_skills))

            # Load performance context
            performance_context = await PerformanceContextLoader.load_performance_hints(
                session, task_type, owner
            )

        except Exception as e:
            logger.warning("Skill loading failed, proceeding without enhancement: %s", e)

    execution_engine = os.getenv("FLOW_EXECUTION_ENGINE", owner)
    system_prompt = SYSTEM_PROMPTS.get(execution_engine, SYSTEM_PROMPTS["hermes"])
    user_message = (
        f"# Role\n{system_prompt}\n\n"
        f"# Task\n**Title:** {title}\n\n**Goal:** {goal}\n\n"
        f"**Task type:** {task_type}\n\n"
    )

    canon_context = load_tbtx_canon_context()
    if canon_context:
        user_message += (
            "## Authoritative TBTX Canon\n"
            "Follow this Canon exactly. Do not invent offers, products, frameworks, "
            "claims, or terminology. Lead with the customer's lived experience, not "
            "technology or internal process.\n\n"
            f"{canon_context}\n\n"
        )

    user_message += (
        "## Production quality rules\n"
        "Treat the task's stated scope as binding. When reviewing one component, "
        "such as a hook or CTA, judge that component only; do not reject it because "
        "later MUST stages belong to the next section of the asset. MUST scores must "
        "use the Canon's 1-10 scale and cite the exact source sentence. A truthful "
        "Mirror hook and relief-oriented CTA can be approval-ready as opening components "
        "when their downstream explanation, prescription, and future state are specified.\n\n"
        "For a production-packet task, never create a packet without a real assigned "
        "backlog item and source path. Report the exact blocker instead. Never add "
        "generic performance language, invented evidence, internal commentary, or "
        "unapproved claims. Keep the response to the requested artifact only.\n\n"
    )

    if performance_context:
        user_message += performance_context

    if skills_context:
        user_message += skills_context

    user_message += (
        "# Completion instruction\n"
        "Complete the requested work now. Return the finished artifact, not a plan "
        "for producing it. Do not publish, deploy, schedule, or change an external "
        "account unless the task contains a recorded approval authorizing that exact action."
    )
    return user_message


async def call_agent_zero(runtime_url: str, prompt: str, job_id: str, timeout: float) -> dict:
    """Execute one synchronous turn through Agent Zero's official HTTP API."""
    base_url = runtime_url.rstrip("/")
    origin = base_url
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
        csrf_response = await client.get("/api/csrf_token", headers={"Origin": origin})
        csrf_response.raise_for_status()
        csrf = csrf_response.json()
        if not csrf.get("ok"):
            raise RuntimeError(f"Agent Zero CSRF initialization failed: {csrf.get('error')}")

        token = str(csrf["token"])
        runtime_id = str(csrf["runtime_id"])
        client.cookies.set(f"csrf_token_{runtime_id}", token)
        response = await client.post(
            "/api/message",
            headers={"Origin": origin, "X-CSRF-Token": token},
            json={
                "text": prompt,
                "context": f"flow-{job_id}",
                "message_id": job_id,
            },
        )
        response.raise_for_status()
        payload = response.json()
        message = payload.get("message")
        if isinstance(message, str):
            final = message.strip()
        elif message is not None:
            final = json.dumps(message, indent=2)
        else:
            final = ""
        if not final:
            raise RuntimeError("Agent Zero returned an empty response")
        return {
            "ok": True,
            "engine": "agent_zero",
            "final": final,
            "context": payload.get("context"),
            "upstream_repository": "https://github.com/agent0ai/agent-zero",
            "upstream_commit": os.getenv("AGENT_ZERO_UPSTREAM_COMMIT", "87e1e591e1ba2e8b1a19d34e134fcae490c8dded"),
        }


async def call_agent_runtime(prompt: str, job_id: str) -> dict:
    """Call the assigned installed agent. No direct model fallback is permitted."""
    engine = os.getenv("FLOW_EXECUTION_ENGINE", "").strip()
    runtime_url = os.getenv("FLOW_RUNTIME_URL", "").strip()
    timeout = float(os.getenv("FLOW_RUNTIME_TIMEOUT_SECONDS", "900"))
    if engine not in {"hermes", "openclaw", "agent_zero"}:
        raise RuntimeError(f"Unsupported FLOW_EXECUTION_ENGINE: {engine or '<missing>'}")
    if not runtime_url:
        raise RuntimeError("FLOW_RUNTIME_URL is not configured")

    if engine == "agent_zero":
        return await call_agent_zero(runtime_url, prompt, job_id, timeout)

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{runtime_url.rstrip('/')}/run",
            json={"prompt": prompt, "job_id": job_id},
        )
        response.raise_for_status()
        payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError(str(payload.get("error") or f"{engine} execution failed"))
    if payload.get("engine") != engine:
        raise RuntimeError(
            f"Runtime identity mismatch: expected {engine}, received {payload.get('engine')}"
        )
    final = str(payload.get("final") or "").strip()
    if not final:
        raise RuntimeError(f"{engine} returned an empty response")
    payload["final"] = final
    return payload


# ── Output writer ─────────────────────────────────────────────────────────────

def write_output(
    job_id: str,
    title: str,
    owner: str,
    engine: str,
    content: str,
    output_base: str,
    runtime_evidence: dict | None = None,
) -> str:
    """Write LLM output to disk. Returns the path written."""
    output_dir = Path(output_base) / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "output.md"
    metadata_path = output_dir / "metadata.json"

    output_path.write_text(content, encoding="utf-8")

    metadata = {
        "job_id": job_id,
        "title": title,
        "owner": owner,
        "execution_engine": engine,
        "completed_at": datetime.utcnow().isoformat(),
        "output_file": str(output_path),
        "runtime_evidence": runtime_evidence or {},
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    logger.info("Output written to %s", output_path)
    return str(output_path)


# ── Discord webhook ───────────────────────────────────────────────────────────

async def notify_discord(webhook_url: str, job_id: str, title: str, owner: str, preview: str) -> None:
    """POST a completion embed to a Discord incoming webhook."""
    if not webhook_url:
        return

    agent_colors = {"hermes": 0x5de88a, "openclaw": 0xf7b84b, "agent_zero": 0xff6b6b}
    color = agent_colors.get(owner, 0x6eb8f7)

    preview_text = preview[:1400].strip()
    if len(preview) > 1400:
        preview_text += "\n\n*(output truncated — full artifact in runtime/reviews/)*"

    payload = {
        "embeds": [{
            "title": f"✅ {title}",
            "description": f"```\n{preview_text[:1000]}\n```" if len(preview_text) < 1000 else preview_text,
            "color": color,
            "fields": [
                {"name": "Agent", "value": owner.upper(), "inline": True},
                {"name": "Job ID", "value": f"`{job_id}`", "inline": True},
            ],
            "footer": {"text": "FLOW Agent AS"},
            "timestamp": datetime.utcnow().isoformat(),
        }]
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(webhook_url, json=payload)
            resp.raise_for_status()
            logger.info("Discord notified for job_id=%s", job_id)
    except Exception as e:
        logger.warning("Discord notification failed for job_id=%s: %s", job_id, e)


# ── Postgres transitions ──────────────────────────────────────────────────────

async def activate_job(job_id: str, owner: str) -> tuple[str | None, str | None, str | None]:
    """Mark job ACTIVE. Returns (goal, title, task_type) for LLM use."""
    async with async_session() as session:
        result = await session.execute(select(JobRecord).where(JobRecord.job_id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            logger.warning("Dequeued unknown job_id=%s owner=%s", job_id, owner)
            return None, None, None

        now = datetime.utcnow()
        job.status = JobStatus.ACTIVE.value
        job.updated_at = now
        job.error_message = None
        if job.started_at is None:
            job.started_at = now

        # Record job activation in audit log
        await record_audit_event(
            session,
            event_type=AuditEventType.JOB_STARTED,
            title=f"Execution started: {job.title or job_id}",
            job_id=job_id,
            task_id=job.task_id,
            agent=owner,
            action_by=owner,
            description=f"{owner} agent started executing job",
            event_data={"task_type": job.task_type},
        )

        await session.commit()
        logger.info("Activated job_id=%s owner=%s", job_id, owner)
        return job.goal, job.title, job.task_type


async def complete_job(job_id: str, result_pointer: str) -> None:
    """Mark job COMPLETED and record artifact path."""
    async with async_session() as session:
        result = await session.execute(select(JobRecord).where(JobRecord.job_id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return
        now = datetime.utcnow()
        job.status = JobStatus.COMPLETED.value
        job.updated_at = now
        job.completed_at = now
        job.result_pointer = result_pointer
        job.error_message = None

        # Record job completion in audit log
        await record_audit_event(
            session,
            event_type=AuditEventType.JOB_COMPLETED,
            title=f"Execution completed: {job.title or job_id}",
            job_id=job_id,
            task_id=job.task_id,
            agent=job.owner,
            action_by=job.owner,
            description=f"Job completed successfully, artifact written to {result_pointer}",
            event_data={"artifact_path": result_pointer},
        )

        # Trigger automated learning cycle
        try:
            reflection_id = await AutomatedLearningService.trigger_learning_cycle(
                session, job_id, result_pointer
            )
            if reflection_id:
                logger.info("Automated learning triggered for job_id=%s reflection_id=%s",
                          job_id, reflection_id)
        except Exception as e:
            logger.warning("Automated learning failed for job_id=%s: %s", job_id, e)

        await session.commit()
        logger.info("Completed job_id=%s artifact=%s", job_id, result_pointer)


async def fail_job(job_id: str, error: str) -> None:
    """Mark job FAILED with error message."""
    async with async_session() as session:
        result = await session.execute(select(JobRecord).where(JobRecord.job_id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return
        job.status = JobStatus.FAILED.value
        job.updated_at = datetime.utcnow()
        job.error_message = error[:500]

        # Record job failure in audit log
        await record_audit_event(
            session,
            event_type=AuditEventType.JOB_FAILED,
            title=f"Execution failed: {job.title or job_id}",
            job_id=job_id,
            task_id=job.task_id,
            agent=job.owner,
            action_by=job.owner,
            description=f"Job failed with error: {error[:200]}",
            event_data={"error": error[:500]},
        )

        await session.commit()
        logger.error("Failed job_id=%s error=%s", job_id, error[:200])


# ── Main loop ─────────────────────────────────────────────────────────────────

async def worker_loop(owner: str, timeout: int) -> None:
    settings = get_settings()
    redis_client = await get_redis_client(settings.bizbrain_redis_url)
    queue = RedisQueueService(redis_client)

    logger.info("Worker started owner=%s queue=%s", owner, queue.get_queue_name(owner))

    try:
        while True:
            job_id = await queue.dequeue_job(owner=owner, timeout=timeout)
            if not job_id:
                continue

            # Step 1: Activate
            goal, title, task_type = await activate_job(job_id, owner)
            if goal is None:
                continue

            effective_goal = goal or "Complete the assigned task."
            effective_title = title or f"Job {job_id}"
            effective_task_type = task_type or "content_prep"

            # Step 2: Execute through the real assigned agent runtime
            try:
                async with async_session() as llm_session:
                    prompt = await build_execution_prompt(
                        goal=effective_goal,
                        title=effective_title,
                        task_type=effective_task_type,
                        owner=owner,
                        session=llm_session,
                    )
                runtime_result = await call_agent_runtime(prompt=prompt, job_id=job_id)
                output = runtime_result["final"]
            except Exception as e:
                await fail_job(job_id, str(e))
                continue

            # Step 3: Write artifact
            artifact_path = write_output(
                job_id=job_id,
                title=effective_title,
                owner=owner,
                engine=str(runtime_result.get("engine")),
                content=output,
                output_base=settings.output_dir,
                runtime_evidence={
                    key: value
                    for key, value in runtime_result.items()
                    if key not in {"final"}
                },
            )

            # Step 4: Mark completed
            await complete_job(job_id, artifact_path)

            # Step 5: Notify Discord
            await notify_discord(
                webhook_url=settings.discord_webhook_url,
                job_id=job_id,
                title=effective_title,
                owner=owner,
                preview=output,
            )

    finally:
        await redis_client.close()


def main() -> None:
    owner = os.getenv("FLOW_QUEUE_OWNER", "openclaw")
    timeout = int(os.getenv("FLOW_QUEUE_TIMEOUT_SECONDS", "5"))
    asyncio.run(worker_loop(owner=owner, timeout=timeout))


if __name__ == "__main__":
    main()
