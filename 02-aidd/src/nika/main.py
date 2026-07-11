import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher

from nika.config import Config
from nika.handlers.message_handler import MessageHandler

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
    dp.include_router(MessageHandler().register())
    logger.info("Ника: starting polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
