import anyio
import pytest
from unittest.mock import AsyncMock

from scripts.refresh import generate_digest_for_plan, process_plan


@pytest.mark.anyio
async def test_generate_digest_returns_text():
    digest = await generate_digest_for_plan("Tempo squat", "Improve control", "Intermediate")
    assert digest is not None
    assert "Tempo squat" in digest


@pytest.mark.anyio
async def test_process_plan_uses_idempotency(monkeypatch):
    class MockRedis:
        def __init__(self):
            self.store = {}

        async def get(self, key):
            return self.store.get(key)

        async def setex(self, key, time, value):
            self.store[key] = value

    mock_redis = MockRedis()
    monkeypatch.setattr("scripts.refresh.redis", mock_redis)
    monkeypatch.setattr("scripts.refresh.save_digest_to_db", lambda plan_id, digest: None)

    async def mock_generate(*args):
        return "Weekly focus: mock"

    monkeypatch.setattr("scripts.refresh.generate_digest_for_plan", mock_generate)

    limiter = anyio.CapacityLimiter(3)

    await process_plan("plan_id", "Tempo squat", "Improve control", "Intermediate", limiter)
    assert await mock_redis.get("plan_digest_processed:plan_id") == "1"

    monkeypatch.setattr(
        "scripts.refresh.generate_digest_for_plan",
        AsyncMock(side_effect=Exception("Should not be called")),
    )
    await process_plan("plan_id", "Tempo squat", "Improve control", "Intermediate", limiter)
