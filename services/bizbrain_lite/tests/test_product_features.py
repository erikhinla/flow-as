"""
Tests for auth, fog-lift-kit, ai-readiness, and concierge endpoints.

These tests use FastAPI's TestClient with a fully mocked database and
in-memory user store so they run without Postgres or Redis.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_jwt(user_id: str = "user-1", email: str = "test@example.com", tier: str = "free") -> str:
    from app.services.auth_service import create_access_token
    return create_access_token(user_id=user_id, email=email, tier=tier)


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------

class TestAuthRegister:
    def test_register_new_user(self):
        """POST /v1/auth/register creates a user and returns a JWT."""
        mock_user = MagicMock()
        mock_user.user_id = "u1"
        mock_user.email = "new@example.com"
        mock_user.tier = "free"
        mock_user.hashed_password = "hashed"
        mock_user.is_active = True

        with (
            patch("app.api.auth.auth_service.get_user_by_email", new=AsyncMock(return_value=None)),
            patch("app.api.auth.auth_service.create_user", new=AsyncMock(return_value=mock_user)),
            patch("app.config.database.get_db_session", return_value=_noop_session()),
        ):
            client = TestClient(app)
            resp = client.post(
                "/v1/auth/register",
                json={"email": "new@example.com", "password": "password123"},
            )
        assert resp.status_code == 201
        body = resp.json()
        assert "access_token" in body
        assert body["tier"] == "free"
        assert body["email"] == "new@example.com"

    def test_register_duplicate_email_returns_409(self):
        """POST /v1/auth/register returns 409 when email already exists."""
        mock_user = MagicMock()
        with (
            patch("app.api.auth.auth_service.get_user_by_email", new=AsyncMock(return_value=mock_user)),
            patch("app.config.database.get_db_session", return_value=_noop_session()),
        ):
            client = TestClient(app)
            resp = client.post(
                "/v1/auth/register",
                json={"email": "existing@example.com", "password": "password123"},
            )
        assert resp.status_code == 409

    def test_register_short_password_returns_422(self):
        """POST /v1/auth/register rejects passwords shorter than 8 chars."""
        client = TestClient(app)
        resp = client.post(
            "/v1/auth/register",
            json={"email": "x@example.com", "password": "short"},
        )
        assert resp.status_code == 422


class TestAuthLogin:
    def test_login_success(self):
        """POST /v1/auth/login returns JWT on valid credentials."""
        from app.services.auth_service import hash_password

        mock_user = MagicMock()
        mock_user.user_id = "u1"
        mock_user.email = "user@example.com"
        mock_user.tier = "free"
        mock_user.hashed_password = hash_password("password123")
        mock_user.is_active = True

        with (
            patch("app.api.auth.auth_service.get_user_by_email", new=AsyncMock(return_value=mock_user)),
            patch("app.config.database.get_db_session", return_value=_noop_session()),
        ):
            client = TestClient(app)
            resp = client.post(
                "/v1/auth/login",
                json={"email": "user@example.com", "password": "password123"},
            )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password_returns_401(self):
        """POST /v1/auth/login returns 401 on wrong password."""
        from app.services.auth_service import hash_password

        mock_user = MagicMock()
        mock_user.user_id = "u1"
        mock_user.email = "user@example.com"
        mock_user.tier = "free"
        mock_user.hashed_password = hash_password("correctpassword")
        mock_user.is_active = True

        with (
            patch("app.api.auth.auth_service.get_user_by_email", new=AsyncMock(return_value=mock_user)),
            patch("app.config.database.get_db_session", return_value=_noop_session()),
        ):
            client = TestClient(app)
            resp = client.post(
                "/v1/auth/login",
                json={"email": "user@example.com", "password": "wrongpassword"},
            )
        assert resp.status_code == 401

    def test_login_unknown_email_returns_401(self):
        """POST /v1/auth/login returns 401 when user not found."""
        with (
            patch("app.api.auth.auth_service.get_user_by_email", new=AsyncMock(return_value=None)),
            patch("app.config.database.get_db_session", return_value=_noop_session()),
        ):
            client = TestClient(app)
            resp = client.post(
                "/v1/auth/login",
                json={"email": "nobody@example.com", "password": "password123"},
            )
        assert resp.status_code == 401


class TestMagicLink:
    def test_magic_link_request_creates_token(self):
        """POST /v1/auth/magic-link returns sent status with token."""
        mock_user = MagicMock()
        mock_user.user_id = "u1"
        mock_user.is_active = True

        with (
            patch("app.api.auth.auth_service.get_user_by_email", new=AsyncMock(return_value=mock_user)),
            patch("app.api.auth.auth_service.create_magic_link_token", new=AsyncMock(return_value="rawtoken123")),
            patch("app.config.database.get_db_session", return_value=_noop_session()),
        ):
            client = TestClient(app)
            resp = client.post("/v1/auth/magic-link", json={"email": "user@example.com"})
        assert resp.status_code == 202
        body = resp.json()
        assert body["status"] == "sent"
        assert "magic_token" in body

    def test_magic_link_verify_success(self):
        """POST /v1/auth/magic-link/verify returns JWT on valid token."""
        mock_user = MagicMock()
        mock_user.user_id = "u1"
        mock_user.email = "user@example.com"
        mock_user.tier = "free"
        mock_user.is_active = True

        with (
            patch("app.api.auth.auth_service.consume_magic_link_token", new=AsyncMock(return_value=mock_user)),
            patch("app.config.database.get_db_session", return_value=_noop_session()),
        ):
            client = TestClient(app)
            resp = client.post("/v1/auth/magic-link/verify", json={"token": "rawtoken123"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_magic_link_verify_invalid_token_returns_401(self):
        """POST /v1/auth/magic-link/verify returns 401 on invalid token."""
        with (
            patch("app.api.auth.auth_service.consume_magic_link_token", new=AsyncMock(return_value=None)),
            patch("app.config.database.get_db_session", return_value=_noop_session()),
        ):
            client = TestClient(app)
            resp = client.post("/v1/auth/magic-link/verify", json={"token": "badtoken"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Fog Lift Kit tests
# ---------------------------------------------------------------------------

class TestFogLiftKit:
    def test_overview_requires_jwt(self):
        """GET /v1/fog-lift-kit without JWT returns 401."""
        client = TestClient(app)
        resp = client.get("/v1/fog-lift-kit")
        assert resp.status_code == 401

    def test_overview_with_valid_jwt(self):
        """GET /v1/fog-lift-kit returns kit overview for authenticated user."""
        token = _make_jwt(tier="free")
        client = TestClient(app)
        resp = client.get("/v1/fog-lift-kit", headers=_auth_header(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["product"] == "Fog Lift Kit"
        assert "modules" in body

    def test_list_modules(self):
        """GET /v1/fog-lift-kit/modules returns all modules."""
        token = _make_jwt(tier="free")
        client = TestClient(app)
        resp = client.get("/v1/fog-lift-kit/modules", headers=_auth_header(token))
        assert resp.status_code == 200
        body = resp.json()
        assert "modules" in body
        assert body["count"] == 3

    def test_get_known_module(self):
        """GET /v1/fog-lift-kit/modules/clarity returns module content."""
        token = _make_jwt(tier="free")
        client = TestClient(app)
        resp = client.get("/v1/fog-lift-kit/modules/clarity", headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.json()["module_id"] == "clarity"

    def test_get_unknown_module_returns_404(self):
        """GET /v1/fog-lift-kit/modules/unknown returns 404."""
        token = _make_jwt(tier="free")
        client = TestClient(app)
        resp = client.get("/v1/fog-lift-kit/modules/unknown", headers=_auth_header(token))
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# AI Readiness tests
# ---------------------------------------------------------------------------

_INTAKE_PAYLOAD = {
    "industry": "SaaS",
    "role": "Founder",
    "team_size": 3,
    "biggest_challenge": "Too much time on manual customer support.",
    "current_ai_tools": ["ChatGPT"],
    "ai_goals": ["Automate support", "Speed up content creation"],
    "budget_range": "$50–$200",
    "technical_comfort": "intermediate",
    "extra_context": "",
}


class TestAIReadiness:
    def test_intake_requires_mid_tier(self):
        """POST /v1/ai-readiness/intake returns 403 for free-tier users."""
        token = _make_jwt(tier="free")
        client = TestClient(app)
        resp = client.post(
            "/v1/ai-readiness/intake",
            json=_INTAKE_PAYLOAD,
            headers=_auth_header(token),
        )
        assert resp.status_code == 403

    def test_intake_requires_jwt(self):
        """POST /v1/ai-readiness/intake returns 401 without JWT."""
        client = TestClient(app)
        resp = client.post("/v1/ai-readiness/intake", json=_INTAKE_PAYLOAD)
        assert resp.status_code == 401

    def test_intake_mid_tier_creates_report(self):
        """POST /v1/ai-readiness/intake creates and returns a report for mid-tier users."""
        from datetime import datetime

        with patch("app.api.ai_readiness.AIReadinessReport") as MockReport:
            instance = MagicMock()
            instance.report_id = "r1"
            instance.user_id = "u1"
            instance.status = "complete"
            instance.snapshot_text = "# AI Readiness Snapshot\n..."
            instance.intake_data = _INTAKE_PAYLOAD
            instance.created_at = datetime.utcnow()
            MockReport.return_value = instance

            mock_db = AsyncMock()
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()

            async def _override():
                yield mock_db

            from app.config.database import get_db_session
            app.dependency_overrides[get_db_session] = _override
            try:
                token = _make_jwt(user_id="u1", tier="mid")
                client = TestClient(app)
                resp = client.post(
                    "/v1/ai-readiness/intake",
                    json=_INTAKE_PAYLOAD,
                    headers=_auth_header(token),
                )
            finally:
                app.dependency_overrides.clear()

        assert resp.status_code == 201
        body = resp.json()
        assert body["report_id"] == "r1"
        assert "snapshot_text" in body

    def test_intake_concierge_tier_also_allowed(self):
        """POST /v1/ai-readiness/intake also works for concierge tier."""
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        with patch("app.api.ai_readiness.AIReadinessReport") as MockReport:
            instance = MagicMock()
            instance.report_id = "r2"
            instance.user_id = "u2"
            instance.status = "complete"
            instance.snapshot_text = "# AI Readiness Snapshot"
            instance.intake_data = _INTAKE_PAYLOAD
            MockReport.return_value = instance

            async def _override():
                yield mock_db

            from app.config.database import get_db_session
            app.dependency_overrides[get_db_session] = _override
            try:
                token = _make_jwt(user_id="u2", tier="concierge")
                client = TestClient(app)
                resp = client.post(
                    "/v1/ai-readiness/intake",
                    json=_INTAKE_PAYLOAD,
                    headers=_auth_header(token),
                )
            finally:
                app.dependency_overrides.clear()

        assert resp.status_code == 201

    def test_snapshot_content_is_non_empty(self):
        """The generated snapshot contains expected sections."""
        from app.api.ai_readiness import _generate_snapshot
        from app.schemas.ai_readiness import AIReadinessIntakeRequest

        intake = AIReadinessIntakeRequest(**_INTAKE_PAYLOAD)
        snapshot = _generate_snapshot(intake)
        assert "AI Readiness Snapshot" in snapshot
        assert "Biggest Challenge" in snapshot
        assert "Recommended 30-Day Roadmap" in snapshot


# ---------------------------------------------------------------------------
# Concierge tests
# ---------------------------------------------------------------------------

_BOOKING_PAYLOAD = {
    "goals": "I want to automate 80% of my customer support using AI agents.",
    "current_situation": "Using Intercom manually, 5h/week.",
    "preferred_timeline": "30 days",
}


class TestConcierge:
    def test_book_requires_concierge_tier(self):
        """POST /v1/concierge/book returns 403 for mid-tier users."""
        token = _make_jwt(tier="mid")
        client = TestClient(app)
        resp = client.post(
            "/v1/concierge/book",
            json=_BOOKING_PAYLOAD,
            headers=_auth_header(token),
        )
        assert resp.status_code == 403

    def test_book_requires_jwt(self):
        """POST /v1/concierge/book returns 401 without JWT."""
        client = TestClient(app)
        resp = client.post("/v1/concierge/book", json=_BOOKING_PAYLOAD)
        assert resp.status_code == 401

    def test_book_concierge_tier_creates_booking(self):
        """POST /v1/concierge/book creates a booking for concierge-tier users."""
        from datetime import datetime

        with patch("app.api.concierge.ConciergeBooking") as MockBooking:
            instance = MagicMock()
            instance.booking_id = "b1"
            instance.user_id = "u3"
            instance.status = "pending"
            instance.goals = _BOOKING_PAYLOAD["goals"]
            instance.context_data = {}
            instance.created_at = datetime.utcnow()
            MockBooking.return_value = instance

            mock_db = AsyncMock()
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()

            async def _override():
                yield mock_db

            from app.config.database import get_db_session
            app.dependency_overrides[get_db_session] = _override
            try:
                token = _make_jwt(user_id="u3", tier="concierge")
                client = TestClient(app)
                resp = client.post(
                    "/v1/concierge/book",
                    json=_BOOKING_PAYLOAD,
                    headers=_auth_header(token),
                )
            finally:
                app.dependency_overrides.clear()

        assert resp.status_code == 201
        body = resp.json()
        assert body["booking_id"] == "b1"
        assert body["status"] == "pending"

    def test_book_requires_minimum_goal_length(self):
        """POST /v1/concierge/book rejects goals shorter than 20 chars."""
        token = _make_jwt(tier="concierge")
        client = TestClient(app)
        resp = client.post(
            "/v1/concierge/book",
            json={**_BOOKING_PAYLOAD, "goals": "Too short"},
            headers=_auth_header(token),
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Helper: no-op async session context manager
# ---------------------------------------------------------------------------

def _noop_session():
    """Return an async generator that yields a no-op mock session."""
    async def _gen():
        yield AsyncMock()
    return _gen()
