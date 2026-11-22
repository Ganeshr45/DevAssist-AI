from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.core import rate_limit


@pytest.mark.asyncio
async def test_limit_rejects_requests_over_quota(monkeypatch):
    monkeypatch.setattr(rate_limit.redis, "eval", AsyncMock(return_value=5))
    with pytest.raises(HTTPException) as error:
        await rate_limit.enforce_limit("chat:user", 4, 60)
    assert error.value.status_code == 429
    assert error.value.headers["Retry-After"] == "60"


@pytest.mark.asyncio
async def test_production_fails_closed_when_redis_is_unavailable(monkeypatch):
    monkeypatch.setattr(rate_limit.settings, "app_env", "production")
    monkeypatch.setattr(rate_limit.redis, "eval", AsyncMock(side_effect=OSError("offline")))
    with pytest.raises(HTTPException) as error:
        await rate_limit.enforce_limit("chat:user", 4, 60)
    assert error.value.status_code == 503
