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
import shutil
import subprocess
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
from app.services.runtime_output_validation import (
    requires_media_artifacts,
    validate_artifact_contract,
    validate_runtime_output,
)
from app.models.audit_log import AuditEventType


logging.basicConfig(
    level=os.getenv("FLOW_WORKER_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("flow.queue_worker")

# ── System prompts per agent ──────────────────────────────────────────────────

SYSTEM_PROMPTS: dict[str, str] = {
    "hermes": (
        "You are Hermes Agent, the creative production lead. Use your installed tools to "
        "create the finished deliverables requested by the task. Strategy and prose are not "
        "substitutes for requested media or files. Follow the supplied output contract exactly."
    ),
    "openclaw": (
        "You are OpenClaw, a sharp business analyst and operations strategist. "
        "You handle classification, routing decisions, research briefs, and structured analysis. "
        "Create the requested inspectable files when the output contract requires them. "
        "Do not claim completion when a required file is missing."
    ),
    "agent_zero": (
        "You are Agent Zero, a senior full-stack developer and implementation specialist. "
        "You build landing pages, write code, create structured deliverables, and handle "
        "complex multi-step implementations. Create complete, inspectable deliverables in the "
        "assigned workspace. Do not return code blocks when the task requires actual files."
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
    output_required: str,
    inputs: dict,
    job_workspace: Path,
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
        f"**Required observable output:** {output_required or 'A finished text artifact.'}\n\n"
        f"**Job workspace:** {job_workspace}\n\n"
    )
    if inputs:
        user_message += f"**Inputs:**\n```json\n{json.dumps(inputs, indent=2)}\n```\n\n"

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
        "Complete the requested work now. If the required output names files, video, audio, "
        "images, code, or a report, create those real files under the exact job workspace above. "
        "Do not return a plan, storyboard, specification, shell command, or Markdown description "
        "as a substitute. End with a concise manifest of the files you actually created. "
        "If a required source or capability is unavailable, say so truthfully and do not claim "
        "completion. Do not publish, deploy, schedule, or change an external account unless the "
        "task contains a recorded approval authorizing that exact action."
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


async def call_agent_runtime(
    prompt: str,
    job_id: str,
    *,
    engine: str | None = None,
    runtime_url: str | None = None,
) -> dict:
    """Call the assigned installed agent. No direct model fallback is permitted."""
    engine = (engine or os.getenv("FLOW_EXECUTION_ENGINE", "")).strip()
    runtime_url = (runtime_url or os.getenv("FLOW_RUNTIME_URL", "")).strip()
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


async def run_creative_review_pipeline(
    *,
    job_id: str,
    title: str,
    goal: str,
    output_required: str,
    job_workspace: Path,
) -> list[dict]:
    """Run the real Agent Zero review and OpenClaw packaging stages."""
    agent_zero_url = os.getenv("FLOW_AGENT_ZERO_RUNTIME_URL", "http://agent-zero").strip()
    openclaw_url = os.getenv(
        "FLOW_OPENCLAW_RUNTIME_URL",
        "http://openclaw-agent:18790",
    ).strip()

    review_prompt = (
        "# Role\n"
        "You are Agent Zero acting as the independent creative completion validator.\n\n"
        "# Task\n"
        f"Title: {title}\n"
        f"Goal: {goal}\n"
        f"Required output: {output_required}\n"
        f"Workspace: {job_workspace}\n\n"
        "Inspect the real files in the workspace. Use ffprobe or equivalent checks for every "
        "video. Verify file count, dimensions, duration, readability, safe text placement, "
        "logo transparency, and the exact requested creative constraints. Do not approve a "
        "plan or a prose-only substitute. Do not alter the creative files. Write the factual "
        "result to validation-report.md in the workspace. The report must list every inspected "
        "file and show pass or fail for each requirement. End the report with exactly "
        "OVERALL: PASS or OVERALL: FAIL."
    )
    review_result = await call_agent_runtime(
        review_prompt,
        f"{job_id}-agent-zero-review",
        engine="agent_zero",
        runtime_url=agent_zero_url,
    )
    validate_runtime_output(str(review_result["final"]))

    package_prompt = (
        "# Role\n"
        "You are OpenClaw acting as the delivery packager for a staged creative review.\n\n"
        "# Task\n"
        f"Title: {title}\n"
        f"Required output: {output_required}\n"
        f"Workspace: {job_workspace}\n\n"
        "Inspect the existing files only. Do not rewrite, rerender, publish, upload, or delete "
        "anything. Create package-manifest.json in the workspace with each deliverable's relative "
        "path, byte size, and role. Include validation-report.md. Return a concise statement of "
        "the manifest path after the file has actually been written."
    )
    package_result = await call_agent_runtime(
        package_prompt,
        f"{job_id}-openclaw-package",
        engine="openclaw",
        runtime_url=openclaw_url,
    )
    validate_runtime_output(str(package_result["final"]))

    validation_report = job_workspace / "validation-report.md"
    package_manifest = job_workspace / "package-manifest.json"
    missing = [
        path.name
        for path in (validation_report, package_manifest)
        if not path.is_file() or path.stat().st_size == 0
    ]
    if missing:
        raise RuntimeError(
            "Creative workflow completion gate failed: missing "
            + ", ".join(missing)
        )
    report_text = validation_report.read_text(encoding="utf-8").upper()
    if "OVERALL: PASS" not in report_text or "OVERALL: FAIL" in report_text:
        raise RuntimeError("Agent Zero creative validation did not return OVERALL: PASS")

    return [
        {
            "stage": "agent_zero_validation",
            **{key: value for key, value in review_result.items() if key != "final"},
        },
        {
            "stage": "openclaw_packaging",
            **{key: value for key, value in package_result.items() if key != "final"},
        },
    ]


def build_render_verification_prompt(
    *,
    title: str,
    goal: str,
    output_required: str,
    job_workspace: Path,
    render_manifest: dict,
) -> str:
    """Build a short Hermes verification prompt after deterministic rendering.

    An approved render profile is already a production instruction. Loading the
    entire Canon and asking a model to restate the brief before rendering adds
    latency without improving the media. Hermes verifies the real render
    manifest after the tool runs; Agent Zero and OpenClaw remain independent
    downstream gates.
    """
    return (
        "# Role\n"
        "You are Hermes Agent verifying a completed creative-tool run.\n\n"
        "# Task\n"
        f"Title: {title}\n"
        f"Goal: {goal}\n"
        f"Required output: {output_required}\n"
        f"Workspace: {job_workspace}\n"
        f"Render manifest: {json.dumps(render_manifest, separators=(',', ':'))}\n\n"
        "Confirm that the manifest contains three distinct staged concept videos, "
        "one contact sheet, one transparent wordmark, and published=false. Inspect "
        "the named files in the workspace. Do not rewrite, rerender, publish, upload, "
        "or delete anything. Respond in no more than six short lines. State the files "
        "you verified and whether the package is ready for independent QC."
    )


def run_render_profile(inputs: dict, job_workspace: Path) -> dict | None:
    """Execute a repository-backed renderer for an explicitly requested profile."""
    profile = str(inputs.get("render_profile") or "").strip()
    if not profile:
        return None
    if profile != "tbtx_social_concepts_v1":
        raise RuntimeError(f"Unsupported creative render profile: {profile}")

    source_files = inputs.get("source_files")
    if not isinstance(source_files, list) or len(source_files) < 2:
        raise RuntimeError(
            "tbtx_social_concepts_v1 requires at least two source_files"
        )
    command = [
        "python3",
        "/app/scripts/render_tbtx_social_concepts.py",
        "--workspace",
        str(job_workspace),
        "--source-a",
        str(source_files[0]),
        "--source-b",
        str(source_files[1]),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=int(os.getenv("FLOW_RENDER_TIMEOUT_SECONDS", "900")),
        check=False,
    )
    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(
            "Creative renderer failed: "
            + (details[-1_500:] if details else f"exit {completed.returncode}")
        )
    logger.info(
        "Creative render profile completed profile=%s workspace=%s",
        profile,
        job_workspace,
    )
    manifest_path = job_workspace / "render-manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(
            "Creative renderer exited successfully without render-manifest.json"
        )
    return json.loads(manifest_path.read_text(encoding="utf-8"))


# ── Output writer ─────────────────────────────────────────────────────────────

def write_output(
    job_id: str,
    title: str,
    owner: str,
    engine: str,
    content: str,
    output_base: str,
    job_workspace: Path,
    produced_files: list[Path],
    runtime_evidence: dict | None = None,
) -> str:
    """Write LLM output to disk. Returns the path written."""
    output_dir = Path(output_base) / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "output.md"
    metadata_path = output_dir / "metadata.json"
    files_dir = output_dir / "files"

    output_path.write_text(content, encoding="utf-8")

    staged_files: list[dict[str, object]] = []
    for source_path in produced_files:
        relative_path = source_path.relative_to(job_workspace)
        destination = files_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)
        staged_files.append(
            {
                "relative_path": str(relative_path),
                "review_path": str(destination),
                "size_bytes": destination.stat().st_size,
            }
        )

    metadata = {
        "job_id": job_id,
        "title": title,
        "owner": owner,
        "execution_engine": engine,
        "completed_at": datetime.utcnow().isoformat(),
        "output_file": str(output_path),
        "job_workspace": str(job_workspace),
        "artifacts": staged_files,
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

async def activate_job(
    job_id: str,
    owner: str,
) -> tuple[str | None, str | None, str | None, str | None, dict]:
    """Mark job ACTIVE and return the persisted execution contract."""
    async with async_session() as session:
        result = await session.execute(select(JobRecord).where(JobRecord.job_id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            logger.warning("Dequeued unknown job_id=%s owner=%s", job_id, owner)
            return None, None, None, None, {}

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
        return job.goal, job.title, job.task_type, job.output_required, job.inputs or {}


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
            goal, title, task_type, output_required, inputs = await activate_job(job_id, owner)
            if goal is None:
                continue

            effective_goal = goal or "Complete the assigned task."
            effective_title = title or f"Job {job_id}"
            effective_task_type = task_type or "content_prep"
            effective_output_required = output_required or "A finished text artifact."
            run_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S%f")
            job_workspace = (
                Path(os.getenv("FLOW_AGENT_WORKSPACE", "/workspace"))
                / "jobs"
                / job_id
                / f"run-{run_stamp}"
            )
            job_workspace.mkdir(parents=True, exist_ok=False)

            # Step 2: Execute through the real assigned agent runtime
            try:
                async with async_session() as llm_session:
                    prompt = await build_execution_prompt(
                        goal=effective_goal,
                        title=effective_title,
                        task_type=effective_task_type,
                        owner=owner,
                        output_required=effective_output_required,
                        inputs=inputs,
                        job_workspace=job_workspace,
                        session=llm_session,
                    )
                render_manifest = run_render_profile(inputs, job_workspace)
                if render_manifest is None:
                    runtime_result = await call_agent_runtime(prompt=prompt, job_id=job_id)
                    output = validate_runtime_output(runtime_result["final"])
                else:
                    runtime_result = await call_agent_runtime(
                        prompt=build_render_verification_prompt(
                            title=effective_title,
                            goal=effective_goal,
                            output_required=effective_output_required,
                            job_workspace=job_workspace,
                            render_manifest=render_manifest,
                        ),
                        job_id=f"{job_id}-hermes-render-verification",
                    )
                    validate_runtime_output(runtime_result["final"])
                    output = (
                        "Repository-backed creative renderer completed the assigned "
                        "profile and staged the following manifest:\n\n"
                        + json.dumps(render_manifest, indent=2)
                    )
                produced_files = validate_artifact_contract(
                    effective_output_required,
                    job_workspace,
                    pre_review=requires_media_artifacts(effective_output_required),
                )
                workflow_evidence: list[dict] = []
                if requires_media_artifacts(effective_output_required):
                    workflow_evidence = await run_creative_review_pipeline(
                        job_id=job_id,
                        title=effective_title,
                        goal=effective_goal,
                        output_required=effective_output_required,
                        job_workspace=job_workspace,
                    )
                    produced_files = validate_artifact_contract(
                        effective_output_required,
                        job_workspace,
                    )
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
                job_workspace=job_workspace,
                produced_files=produced_files,
                runtime_evidence={
                    key: value
                    for key, value in runtime_result.items()
                    if key not in {"final"}
                }
                | {"workflow_stages": workflow_evidence},
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
