import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher

from nika.config import Config
from nika.handlers.message_handler import MessageHandler
from nika.services.chat_history import ChatHistory
from nika.services.indexer import Indexer
from nika.services.insulin_calculator import InsulinCalculator
from nika.services.llm_client import LlmClient
from nika.services.meal_log import MealLogStore
from nika.services.transcribe_client import TranscribeClient

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
    history = ChatHistory()
    meal_log = MealLogStore(config.data_file)
    insulin = InsulinCalculator(config)
    transcribe = TranscribeClient(config)
    dp.include_router(
        MessageHandler(config, llm, history, meal_log, insulin, transcribe).register(),
    )
    logger.info(
        "Config loaded: provider=%s text=%s image=%s audio=%s",
        config.llm_provider,
        config.model_text,
        config.model_image,
        config.model_audio,
    )
    logger.info(
        "RAG config: pdf=%s embedding=%s retriever_k=%s openai_base_url=%s",
        config.data_pdf,
        config.model_embedding,
        config.retriever_k,
        config.openai_base_url,
    )
    try:
        indexer = Indexer(config)
        chunk_count = await indexer.aindex()
        logger.info("Vector index ready: chunk_count=%d", chunk_count)
    except FileNotFoundError as error:
        logger.warning("PDF indexing skipped: %s", error)
    except Exception:
        logger.exception("PDF indexing failed")
    logger.info("Ника: starting polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
