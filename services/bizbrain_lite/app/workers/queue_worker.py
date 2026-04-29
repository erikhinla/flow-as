"""
FLOW queue worker — full execution loop.

1. BRPOP job_id from Redis owner queue
2. Mark job ACTIVE in Postgres
3. Call OpenRouter LLM with task context
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

from app.config.database import async_session
from app.config.settings import get_settings
from app.models.flow_job_record import JobRecord, JobStatus
from app.services.redis_queue_service import RedisQueueService, get_redis_client


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


# ── OpenRouter call ───────────────────────────────────────────────────────────

async def call_openrouter(goal: str, title: str, task_type: str, owner: str) -> str:
    """Call OpenRouter LLM and return response text."""
    settings = get_settings()
    api_key = settings.openrouter_api_key
    if not api_key:
        logger.warning("OPENROUTER_API_KEY not set — returning placeholder output")
        return f"# {title}\n\n**[OpenRouter API key not configured]**\n\nGoal: {goal}\n"

    system_prompt = SYSTEM_PROMPTS.get(owner, SYSTEM_PROMPTS["hermes"])
    user_message = f"**Task:** {title}\n\n**Goal:** {goal}\n\n**Task type:** {task_type}\n\nPlease complete this task now."

    payload = {
        "model": settings.openrouter_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": 2048,
        "temperature": 0.7,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://flow-agent-as.io",
        "X-Title": "FLOW Agent AS",
    }

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{settings.openrouter_base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except httpx.HTTPStatusError as e:
        logger.error("OpenRouter HTTP error %s: %s", e.response.status_code, e.response.text[:300])
        raise
    except Exception as e:
        logger.error("OpenRouter call failed: %s", e)
        raise


# ── Output writer ─────────────────────────────────────────────────────────────

def write_output(job_id: str, title: str, owner: str, content: str, output_base: str) -> str:
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
        "completed_at": datetime.utcnow().isoformat(),
        "output_file": str(output_path),
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
        if job.started_at is None:
            job.started_at = now

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

            # Step 2: Generate
            try:
                output = await call_openrouter(
                    goal=effective_goal,
                    title=effective_title,
                    task_type=effective_task_type,
                    owner=owner,
                )
            except Exception as e:
                await fail_job(job_id, str(e))
                continue

            # Step 3: Write artifact
            artifact_path = write_output(
                job_id=job_id,
                title=effective_title,
                owner=owner,
                content=output,
                output_base=settings.output_dir,
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
