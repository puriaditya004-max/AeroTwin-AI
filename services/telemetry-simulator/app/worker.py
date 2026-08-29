from __future__ import annotations

import asyncio
import os

from app.logging import log_event
from app.runtime import ScenarioRunner
from app.settings import get_settings

try:
    import redis.asyncio as redis_async
except ImportError:  # pragma: no cover
    redis_async = None

from stream.publisher import RedisPublisher, RetryingPublisher


class M1Worker:
    def __init__(self, runner: ScenarioRunner | None = None):
        self.settings = get_settings()
        self.runner = runner or ScenarioRunner(self.settings)

    async def run(self) -> None:
        if redis_async is None:
            raise RuntimeError("redis-py is required for the M1 worker")

        redis_client = redis_async.from_url(self.settings.redisUrl)
        inner = RedisPublisher(redis_client, self.settings.streams.output, self.settings.streams.field)
        self.runner.publisher = RetryingPublisher(inner, self.settings.publish)
        self.runner.redis = redis_client
        log_event("worker_started", stream=self.settings.streams.output, redisUrl=self.settings.redisUrl)

        default_scenario = os.getenv("M1_DEFAULT_SCENARIO")
        if default_scenario:
            await self.runner.start(default_scenario)

        try:
            while True:
                await self.runner.follow_desired()
                if self.runner._task is None or self.runner._task.done():
                    if self.runner.state.status == "running":
                        self.runner._task = asyncio.create_task(self.runner._run_loop())
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            await self.runner.stop()
            raise
        finally:
            await redis_client.aclose()


async def main() -> None:
    await M1Worker().run()


if __name__ == "__main__":
    asyncio.run(main())
