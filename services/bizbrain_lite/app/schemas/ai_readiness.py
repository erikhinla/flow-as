"""Pydantic schemas for AI Readiness endpoints."""

from typing import Any
from pydantic import BaseModel, Field


class AIReadinessIntakeRequest(BaseModel):
    """
    Intake form for the AI Readiness Report.

    Fields are intentionally broad so the snapshot generator can surface
    the most relevant guidance for each user's context.
    """

    industry: str = Field(description="Your industry or business type.")
    role: str = Field(description="Your role or title.")
    team_size: int = Field(ge=1, description="Number of people on your team.")
    biggest_challenge: str = Field(
        description="The single biggest challenge in your work right now."
    )
    current_ai_tools: list[str] = Field(
        default_factory=list,
        description="AI tools you are already using (empty list if none).",
    )
    ai_goals: list[str] = Field(
        description="Top 1–3 outcomes you want AI to help you achieve."
    )
    budget_range: str = Field(
        description=(
            "Monthly budget range for AI tooling. "
            "Examples: '$0–$50', '$50–$200', '$200–$500', '$500+'."
        )
    )
    technical_comfort: str = Field(
        description=(
            "Self-rated technical comfort with AI. "
            "One of: 'beginner', 'intermediate', 'advanced'."
        )
    )
    extra_context: str = Field(
        default="",
        description="Anything else you'd like us to know.",
    )


class AIReadinessReportResponse(BaseModel):
    report_id: str
    user_id: str
    status: str
    snapshot_text: str | None
    intake_data: dict[str, Any]
