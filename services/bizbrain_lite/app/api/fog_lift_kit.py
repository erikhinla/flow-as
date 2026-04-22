"""
Fog Lift Kit API – digital, login-gated product.

All endpoints require a valid JWT (any tier).

GET /v1/fog-lift-kit          - overview + module list
GET /v1/fog-lift-kit/modules  - full module catalog
GET /v1/fog-lift-kit/modules/{module_id} - single module content
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_jwt

router = APIRouter(prefix="/fog-lift-kit", tags=["fog-lift-kit"])

# ---------------------------------------------------------------------------
# In-memory kit content (v1 — move to DB/CMS as content grows)
# ---------------------------------------------------------------------------

_MODULES: dict[str, dict] = {
    "clarity": {
        "module_id": "clarity",
        "title": "Clarity: Know Your AI Starting Point",
        "summary": "Assess where you currently stand with AI and identify your top friction points.",
        "steps": [
            "List the top 3 repetitive tasks that consume your week.",
            "Rate each task: How much time? How much mental load?",
            "Identify which tasks involve writing, researching, or decision-making.",
            "Write one sentence describing the biggest bottleneck in your work today.",
        ],
        "outcome": "A personal AI friction map you can act on immediately.",
    },
    "map": {
        "module_id": "map",
        "title": "Map: Design Your AI Integration Plan",
        "summary": "Turn your friction map into a prioritized action plan.",
        "steps": [
            "Pick your single highest-friction task from the Clarity module.",
            "Research 2–3 AI tools that address that task (use the curated list below).",
            "Choose one tool to pilot for 7 days.",
            "Define what 'success' looks like in plain language.",
        ],
        "outcome": "A 7-day AI pilot plan with a clear success metric.",
    },
    "lift": {
        "module_id": "lift",
        "title": "Lift: Run Your First AI Workflow",
        "summary": "Execute your pilot, capture results, and build the habit.",
        "steps": [
            "Set up your chosen tool (follow the quick-start guide).",
            "Use it for your target task every day for 7 days.",
            "Log time saved and quality notes each day (template provided).",
            "At day 7: decide to keep, swap, or escalate the tool.",
        ],
        "outcome": "A completed AI pilot with real before/after data.",
    },
}

_KIT_OVERVIEW = {
    "product": "Fog Lift Kit",
    "version": "1.0",
    "tagline": "Clear the fog. Start using AI today.",
    "description": (
        "A three-module, interactive digital kit that takes you from AI confusion to "
        "a running workflow in 7 days — no technical background required."
    ),
    "modules": [m["module_id"] for m in _MODULES.values()],
    "next_step": {
        "label": "Ready to go deeper?",
        "description": "Get your personalized AI Readiness Report — a bespoke analysis of your business.",
        "action": "POST /v1/ai-readiness/intake",
    },
}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("")
async def kit_overview(claims: dict = Depends(require_jwt)) -> dict:
    """
    Return kit overview and module list.

    Requires: any valid JWT (free tier or above).
    """
    return {**_KIT_OVERVIEW, "user_id": claims["sub"], "tier": claims["tier"]}


@router.get("/modules")
async def list_modules(claims: dict = Depends(require_jwt)) -> dict:
    """
    Return the full module catalog.

    Requires: any valid JWT (free tier or above).
    """
    return {
        "modules": list(_MODULES.values()),
        "count": len(_MODULES),
    }


@router.get("/modules/{module_id}")
async def get_module(module_id: str, claims: dict = Depends(require_jwt)) -> dict:
    """
    Return content for a single kit module.

    Requires: any valid JWT (free tier or above).
    """
    module = _MODULES.get(module_id)
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{module_id}' not found. Available: {list(_MODULES.keys())}",
        )
    return module
