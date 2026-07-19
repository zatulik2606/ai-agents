"""Fixtures для e2e-тестов: тот же AgentService / Indexer, что у бота."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

import pytest_asyncio
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# Один ход с tool + ответом не должен упираться в дефолтный AGENT_RUN_LIMIT=3.
os.environ["AGENT_RUN_LIMIT"] = os.getenv("AGENT_RUN_LIMIT_TEST", "5")

# agentevals (openai:…) читает OPENAI_API_KEY; у Ники ключ часто в OpenRouter-переменных.
if not os.getenv("OPENAI_API_KEY"):
    for _key_name in ("OPENROUTER_API_KEY", "IMAGE_OPENROUTER_API_KEY"):
        _value = os.getenv(_key_name, "").strip()
        if _value:
            os.environ["OPENAI_API_KEY"] = _value
            break

logger = logging.getLogger(__name__)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def agent_fixture():
    """Сессионный агент Ники (индекс + MCP graceful). Уникальный thread_id — в тесте."""
    from nika.config import Config
    from nika.services.agent_service import create_nika_agent
    from nika.services.indexer import Indexer
    from nika.services.rag_service import RagService

    config = Config.from_env()
    indexer = Indexer(config)
    try:
        chunk_count = await asyncio.to_thread(indexer.reindex_all)
        logger.info("Test index ready: document_count=%d", chunk_count)
    except FileNotFoundError as error:
        logger.warning("PDF indexing skipped in tests: %s", error)

    rag = RagService(config, indexer)
    agent = await create_nika_agent(config, rag)
    logger.info(
        "Test agent ready: mcp_tools=%s run_limit=%s",
        agent.mcp_tool_names or "none",
        config.agent_run_limit,
    )
    return agent
