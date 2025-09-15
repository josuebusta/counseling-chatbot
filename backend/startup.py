import asyncio
import logging
from contextlib import asynccontextmanager

from tasks.maintenance import run_periodic_maintenance


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(run_periodic_maintenance())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            logger.info("Background task cancelled")
