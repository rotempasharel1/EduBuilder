import os
from datetime import timedelta

import anyio
from redis.asyncio import Redis
from sqlmodel import Session, create_engine, select

from poseai_backend.models import Plan

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./app.db")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
MAX_CONCURRENCY = int(os.environ.get("WORKER_MAX_CONCURRENCY", "3"))
MAX_RETRIES = int(os.environ.get("WORKER_MAX_RETRIES", "3"))
RETRY_DELAY_SECONDS = float(os.environ.get("WORKER_RETRY_DELAY_SECONDS", "2"))
DIGEST_TTL = timedelta(days=7)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
redis = Redis.from_url(REDIS_URL, decode_responses=True)


def fetch_public_plans() -> list[Plan]:
    with Session(engine) as session:
        statement = select(Plan).where(Plan.is_public == True)  # noqa: E712
        return list(session.exec(statement).all())


def save_digest_to_db(plan_id: str, digest: str) -> None:
    with Session(engine) as session:
        plan = session.get(Plan, plan_id)
        if plan is None:
            return
        plan.weekly_digest = digest
        session.add(plan)
        session.commit()


async def generate_digest_for_plan(title: str, goal: str, level: str) -> str | None:
    if not title.strip():
        return None
    return f"Weekly focus: {title} — practice {goal.lower()} with {level.lower()} consistency."


async def process_plan(plan_id: str, title: str, goal: str, level: str, limiter: anyio.CapacityLimiter) -> None:
    async with limiter:
        cache_key = f"plan_digest_processed:{plan_id}"
        if await redis.get(cache_key):
            print(f"[Worker] Skipping {plan_id} ({title}) - already processed recently.")
            return

        digest: str | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                digest = await generate_digest_for_plan(title, goal, level)
            except Exception:
                digest = None

            if digest:
                break

            if attempt < MAX_RETRIES:
                print(f"[Worker] Retrying {plan_id} (attempt {attempt}/{MAX_RETRIES})...")
                await anyio.sleep(RETRY_DELAY_SECONDS)

        if not digest:
            print(f"[Worker] FAILED | {title} | Could not generate digest.")
            return

        await anyio.to_thread.run_sync(save_digest_to_db, plan_id, digest)
        await redis.setex(cache_key, DIGEST_TTL, "1")
        print(f"[Worker] SUCCESS | {title} | Digest: {digest[:100]}...")


async def main() -> None:
    print("[Worker] Starting background refresh worker...")
    try:
        plans = await anyio.to_thread.run_sync(fetch_public_plans)
        if not plans:
            print("[Worker] No public plans found. Exiting.")
            return

        limiter = anyio.CapacityLimiter(MAX_CONCURRENCY)
        async with anyio.create_task_group() as task_group:
            for plan in plans:
                task_group.start_soon(
                    process_plan,
                    plan.id,
                    plan.title,
                    plan.goal,
                    plan.level,
                    limiter,
                )
    finally:
        close_method = getattr(redis, "aclose", None) or getattr(redis, "close", None)
        if close_method is not None:
            result = close_method()
            if hasattr(result, "__await__"):
                await result

    print("[Worker] Finished processing all plans.")


if __name__ == "__main__":
    anyio.run(main)
