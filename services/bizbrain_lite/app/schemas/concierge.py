"""Pydantic schemas for Concierge endpoints."""

from typing import Any

from pydantic import BaseModel, Field


class ConciergeBookingRequest(BaseModel):
    goals: str = Field(
        description="Describe what you want to achieve with your AI integration.",
        min_length=20,
    )
    current_situation: str = Field(
        default="",
        description="Brief description of your current setup and constraints.",
    )
    preferred_timeline: str = Field(
        default="",
        description="When do you want to see results? (e.g. '30 days', 'ASAP')",
    )
    extra_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Any additional structured context (links, files, metrics).",
    )


class ConciergeBookingResponse(BaseModel):
    booking_id: str
    user_id: str
    status: str
    goals: str
    context_data: dict[str, Any]
    created_at: str
