from __future__ import annotations

import asyncio

from app.core.scheduler import start_scheduler, stop_scheduler


async def _run_forever() -> None:
    start_scheduler()
    try:
        await asyncio.Event().wait()
    finally:
        stop_scheduler()


def main() -> None:
    asyncio.run(_run_forever())


if __name__ == "__main__":
    main()
