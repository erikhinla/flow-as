"""
AI Readiness Report API.

POST /v1/ai-readiness/intake     - submit intake form → generate snapshot (mid+ tier)
GET  /v1/ai-readiness/reports    - list my reports
GET  /v1/ai-readiness/reports/{report_id} - get single report
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_tier
from app.config.database import get_db_session
from app.models.ai_readiness_report import (
    AIReadinessReport,
    REPORT_STATUS_COMPLETE,
    REPORT_STATUS_ERROR,
)
from app.schemas.ai_readiness import AIReadinessIntakeRequest, AIReadinessReportResponse

router = APIRouter(prefix="/ai-readiness", tags=["ai-readiness"])

_MID_PLUS = ("mid", "concierge")


# ---------------------------------------------------------------------------
# Snapshot generator (rule-based v1 — swap for LLM call in v2)
# ---------------------------------------------------------------------------


def _generate_snapshot(intake: AIReadinessIntakeRequest) -> str:
    """
    Produce a plain-text AI Readiness snapshot from intake answers.

    This is a deterministic rule-based generator (v1). Replace with an LLM
    call or template engine as the product matures.
    """
    comfort_advice = {
        "beginner": (
            "Start with no-code AI tools (ChatGPT, Claude, Notion AI) before touching APIs. "
            "Focus on prompting skills first."
        ),
        "intermediate": (
            "You are ready to explore API integrations and automation (Zapier + AI, Make). "
            "Prioritise building repeatable workflows."
        ),
        "advanced": (
            "Consider deploying custom agents or fine-tuned models. "
            "Focus on orchestration, observability, and governance."
        ),
    }.get(
        intake.technical_comfort.lower(),
        "Assess your comfort level honestly and match tool complexity to your skills.",
    )

    current = (
        ", ".join(intake.current_ai_tools) if intake.current_ai_tools else "none yet"
    )
    goals = "\n".join(f"  • {g}" for g in intake.ai_goals)

    snapshot = f"""# AI Readiness Snapshot

## Your Profile
- **Industry:** {intake.industry}
- **Role:** {intake.role}
- **Team size:** {intake.team_size}
- **Technical comfort:** {intake.technical_comfort}
- **Budget range:** {intake.budget_range}/month
- **Tools you already use:** {current}

## Biggest Challenge
> {intake.biggest_challenge}

## Your AI Goals
{goals}

## Readiness Assessment

### Where you are
{"You have existing AI tools to build on — extend your stack intentionally." if intake.current_ai_tools else "You are starting fresh, which means no legacy habits to break — a real advantage."}

### Next best action
{comfort_advice}

### Budget guidance
{"Your budget supports a solid no-code AI stack. Prioritise 1–2 tools rather than spreading thin." if intake.budget_range in ("$0–$50", "$50–$200") else "Your budget unlocks automation platforms and API integrations. Invest in a workflow audit first."}

## Recommended 30-Day Roadmap

**Week 1 — Clarity**
Complete the Fog Lift Kit if you haven't already. Map your top 3 friction points.

**Week 2 — Tool selection**
Pick one AI tool that addresses your biggest challenge. Run a 5-day pilot.

**Week 3 — Integration**
Connect your chosen tool to an existing workflow. Measure time saved.

**Week 4 — Review & expand**
Assess results. Decide what to keep, drop, or scale.

---
*This snapshot was generated from your intake answers. For a bespoke roadmap with
live guidance, book an AI Concierge session: POST /v1/concierge/book*
"""
    return snapshot.strip()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/intake", response_model=AIReadinessReportResponse, status_code=status.HTTP_201_CREATED)
async def submit_intake(
    payload: AIReadinessIntakeRequest,
    claims: dict = Depends(require_tier(*_MID_PLUS)),
    db: AsyncSession = Depends(get_db_session),
) -> AIReadinessReportResponse:
    """
    Submit an AI readiness intake form and receive a generated snapshot.

    Requires: **mid** or **concierge** tier JWT.
    """
    intake_dict = payload.model_dump()
    snapshot = _generate_snapshot(payload)

    report = AIReadinessReport(
        user_id=claims["sub"],
        intake_data=intake_dict,
        snapshot_text=snapshot,
        status=REPORT_STATUS_COMPLETE,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    return AIReadinessReportResponse(
        report_id=report.report_id,
        user_id=report.user_id,
        status=report.status,
        snapshot_text=report.snapshot_text,
        intake_data=report.intake_data,
    )


@router.get("/reports", response_model=list[AIReadinessReportResponse])
async def list_reports(
    claims: dict = Depends(require_tier(*_MID_PLUS)),
    db: AsyncSession = Depends(get_db_session),
) -> list[AIReadinessReportResponse]:
    """
    List all AI readiness reports for the authenticated user.

    Requires: **mid** or **concierge** tier JWT.
    """
    result = await db.execute(
        select(AIReadinessReport)
        .where(AIReadinessReport.user_id == claims["sub"])
        .order_by(AIReadinessReport.created_at.desc())
    )
    rows = result.scalars().all()
    return [
        AIReadinessReportResponse(
            report_id=r.report_id,
            user_id=r.user_id,
            status=r.status,
            snapshot_text=r.snapshot_text,
            intake_data=r.intake_data,
        )
        for r in rows
    ]


@router.get("/reports/{report_id}", response_model=AIReadinessReportResponse)
async def get_report(
    report_id: str,
    claims: dict = Depends(require_tier(*_MID_PLUS)),
    db: AsyncSession = Depends(get_db_session),
) -> AIReadinessReportResponse:
    """
    Retrieve a single AI readiness report by ID.

    Requires: **mid** or **concierge** tier JWT.  Users can only access their own reports.
    """
    result = await db.execute(
        select(AIReadinessReport).where(AIReadinessReport.report_id == report_id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    if report.user_id != claims["sub"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    return AIReadinessReportResponse(
        report_id=report.report_id,
        user_id=report.user_id,
        status=report.status,
        snapshot_text=report.snapshot_text,
        intake_data=report.intake_data,
    )
