"""Загрузка tools с MCP-сервера mcp-nika-agent."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger(__name__)

DEFAULT_MCP_SERVER_URL = "http://127.0.0.1:8000/mcp"


async def load_mcp_tools(server_url: str = DEFAULT_MCP_SERVER_URL) -> list[BaseTool]:
    """Подключиться к MCP и вернуть tools. При ошибке — [] и warning."""
    try:
        client = MultiServerMCPClient(
            {
                "nika": {
                    "transport": "streamable_http",
                    "url": server_url,
                }
            }
        )
        tools = await client.get_tools()
        names = [getattr(tool, "name", "?") for tool in tools]
        logger.info("MCP tools loaded from %s: %s", server_url, names)
        return list(tools)
    except Exception:
        logger.warning(
            "MCP unavailable at %s — continuing without MCP tools "
            "(rag_search + glucose_unit_converter only)",
            server_url,
            exc_info=True,
        )
        return []


def mcp_tool_names(tools: list[Any]) -> list[str]:
    return [str(getattr(tool, "name", "?")) for tool in tools]
