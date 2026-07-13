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
    try:
        chunk_count = await asyncio.to_thread(indexer.reindex_all)
        logger.info("Vector index ready: document_count=%d", chunk_count)
    except FileNotFoundError as error:
        logger.warning("PDF indexing skipped: %s", error)
    except Exception:
        logger.exception("PDF indexing failed")
    rag = RagService(config, indexer)
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
        "RAG config: mode=%s pdf=%s embedding_provider=%s embedding=%s model=%s "
        "semantic_k=%s bm25_k=%s hybrid_k=%s reranker_fetch_k=%s reranker_k=%s "
        "crossencoder=%s openai_base_url=%s",
        config.rag_retrieval_mode,
        config.data_pdf,
        config.embedding_provider,
        config.model_embedding,
        config.model_rag,
        config.semantic_retriever_k,
        config.bm25_retriever_k,
        config.hybrid_retriever_k,
        config.reranker_fetch_k,
        config.reranker_k,
        config.model_crossencoder,
        config.openai_base_url,
    )
    langsmith_status = "enabled" if config.langsmith_api_key else "disabled"
    logger.info(
        "Monitoring: show_sources=%s langsmith=%s dataset=%s",
        config.show_sources,
        langsmith_status,
        config.langsmith_dataset,
    )
    logger.info("Ника: starting polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
