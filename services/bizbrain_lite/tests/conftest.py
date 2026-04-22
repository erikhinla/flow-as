"""
conftest.py – test session setup.

aioredis 2.x is incompatible with Python 3.12 (duplicate-base-class error).
Stub it out before any application module is imported so the test suite can
run without a live Redis instance.  This is a workaround for a pre-existing
dependency issue; it does not affect production behaviour.
"""

import sys
from unittest.mock import AsyncMock, MagicMock

# ---------------------------------------------------------------------------
# Stub aioredis before any app module is loaded
# ---------------------------------------------------------------------------

_aioredis_stub = MagicMock()
_aioredis_stub.Redis = MagicMock
_aioredis_stub.from_url = AsyncMock(return_value=MagicMock())

sys.modules.setdefault("aioredis", _aioredis_stub)
