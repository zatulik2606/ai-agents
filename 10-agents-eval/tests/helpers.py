"""Вспомогательные функции для e2e-траекторий агента Ники."""

from __future__ import annotations

import logging

from langchain_core.messages import BaseMessage

from nika.services.agent_service import AgentService

logger = logging.getLogger(__name__)


async def extract_trajectory(
    agent: AgentService,
    thread_id: str,
    user_message: str,
) -> list[BaseMessage]:
    """Запустить один ход агента и вернуть полную траекторию messages."""
    await agent.answer(thread_id, user_message)
    return agent.get_trajectory(thread_id)


def print_trajectory(trajectory: list[BaseMessage]) -> None:
    """Лог траектории для отладки падающих тестов."""
    logger.info("\n%s", "=" * 60)
    logger.info("AGENT TRAJECTORY")
    logger.info("%s", "=" * 60)

    for index, message in enumerate(trajectory, start=1):
        msg_type = type(message).__name__
        logger.info("\n%d. %s", index, msg_type)

        content = getattr(message, "content", None)
        if content:
            logger.info("   Content: %s", str(content)[:200])

        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls:
            for tool_call in tool_calls:
                name = tool_call.get("name", "?")
                args = tool_call.get("args", {})
                logger.info("   Tool: %s", name)
                logger.info("      Args: %s", args)

        name = getattr(message, "name", None)
        if name:
            logger.info("   ToolMessage name: %s", name)

    logger.info("\n%s\n", "=" * 60)
