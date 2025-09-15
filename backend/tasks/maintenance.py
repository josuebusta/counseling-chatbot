import asyncio
import logging
from datetime import datetime

from tools.chat_management import get_chat_history, create_transcript
from tools.support_system import check_inactive_chats


logger = logging.getLogger(__name__)


async def run_periodic_maintenance(interval_seconds: int = 300) -> None:
    """
    Run maintenance tasks periodically.
    Includes: fetch chat history, check inactive chats, create transcripts.
    Retries with a backoff delay on error.
    """
    counter = 0
    while True:
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"Running check #{counter} at {current_time}")

            await get_chat_history()
            await check_inactive_chats()
            await create_transcript()

            logger.info(f"Check #{counter} completed")
            counter += 1
            await asyncio.sleep(interval_seconds)
        except Exception as exc:
            logger.error(f"Error in check #{counter}: {exc}")
            await asyncio.sleep(60)
