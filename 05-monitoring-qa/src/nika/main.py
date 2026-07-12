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
from nika.services.rag_service import RagService
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
    indexer = Indexer(config)
    rag = RagService(config, indexer)
    try:
        chunk_count = await asyncio.to_thread(indexer.reindex_all)
        logger.info("Vector index ready: document_count=%d", chunk_count)
    except FileNotFoundError as error:
        logger.warning("PDF indexing skipped: %s", error)
    except Exception:
        logger.exception("PDF indexing failed")
    dp.include_router(
        MessageHandler(
            config,
            llm,
            history,
            meal_log,
            insulin,
            transcribe,
            rag,
            indexer,
        ).register(),
    )
    logger.info(
        "Config loaded: provider=%s text=%s image=%s audio=%s",
        config.llm_provider,
        config.model_text,
        config.model_image,
        config.model_audio,
    )
    logger.info(
        "RAG config: pdf=%s embedding_provider=%s embedding=%s model=%s "
        "retriever_k=%s openai_base_url=%s",
        config.data_pdf,
        config.embedding_provider,
        config.model_embedding,
        config.model_rag,
        config.retriever_k,
        config.openai_base_url,
    )
    logger.info("Ника: starting polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
