import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher

from nika.config import Config
from nika.handlers.message_handler import MessageHandler
from nika.services.llm_client import LlmClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    try:
        config = Config.from_env()
    except ValueError as error:
        logger.error("%s", error)
        sys.exit(1)

    bot = Bot(token=config.telegram_bot_token)
    dp = Dispatcher()
    llm = LlmClient(config)
    dp.include_router(MessageHandler(llm).register())
    logger.info("Ника: starting polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
