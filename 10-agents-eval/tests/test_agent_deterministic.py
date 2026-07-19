"""E2E match-тесты агента Ники (agentevals trajectory match)."""

from __future__ import annotations

import logging

import pytest
from agentevals.trajectory.match import create_trajectory_match_evaluator
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from tests.helpers import extract_trajectory, print_trajectory

logger = logging.getLogger(__name__)


def _log_match_result(result: dict, *, trajectory_len: int) -> None:
    logger.info("=" * 60)
    logger.info("EVALUATOR RESULT")
    logger.info("   Score: %s", result.get("score"))
    logger.info("   Comment: %s", result.get("comment", "No comment"))
    logger.info("   Trajectory length: %s", trajectory_len)
    logger.info("=" * 60)


async def test_extract_trajectory_returns_messages(agent_fixture) -> None:
    """Smoke: helper возвращает LangChain-messages после одного хода."""
    trajectory = await extract_trajectory(agent_fixture, "smoke_extract_1", "Спасибо")
    print_trajectory(trajectory)

    assert len(trajectory) >= 2
    assert any(isinstance(message, HumanMessage) for message in trajectory)
    assert any(isinstance(message, AIMessage) for message in trajectory)


async def test_rag_search_superset(agent_fixture) -> None:
    """Справочный вопрос → минимум rag_search (superset, args ignore)."""
    user_message = "Что такое гипогликемия?"
    actual = await extract_trajectory(agent_fixture, "test_rag_1", user_message)
    print_trajectory(actual)

    reference = [
        HumanMessage(content=user_message),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "rag_search",
                    "args": {"query": "гипогликемия"},
                    "id": "call_1",
                }
            ],
        ),
        ToolMessage(
            content='{"sources": []}',
            name="rag_search",
            tool_call_id="call_1",
        ),
        AIMessage(content="Гипогликемия — пониженный уровень глюкозы..."),
    ]

    evaluator = create_trajectory_match_evaluator(
        trajectory_match_mode="superset",
        tool_args_match_mode="ignore",
    )
    result = evaluator(outputs=actual, reference_outputs=reference)
    _log_match_result(result, trajectory_len=len(actual))

    assert result["score"], (
        "Ожидали вызов rag_search (superset).\n"
        f"Comment: {result.get('comment', 'No comment')}\n"
        f"Trajectory length: {len(actual)}"
    )


async def test_glucose_unit_converter_superset(agent_fixture) -> None:
    """Конвертация единиц → минимум glucose_unit_converter (superset, args ignore)."""
    user_message = "Переведи 180 мг/дл в ммоль/л"
    actual = await extract_trajectory(agent_fixture, "test_glucose_1", user_message)
    print_trajectory(actual)

    reference = [
        HumanMessage(content=user_message),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "glucose_unit_converter",
                    "args": {
                        "value": 180,
                        "from_unit": "mg_dl",
                        "to_unit": "mmol_l",
                    },
                    "id": "call_1",
                }
            ],
        ),
        ToolMessage(
            content='{"value": 10.0, "unit": "mmol_l"}',
            name="glucose_unit_converter",
            tool_call_id="call_1",
        ),
        AIMessage(content="180 мг/дл это 10.00 ммоль/л."),
    ]

    evaluator = create_trajectory_match_evaluator(
        trajectory_match_mode="superset",
        tool_args_match_mode="ignore",
    )
    result = evaluator(outputs=actual, reference_outputs=reference)
    _log_match_result(result, trajectory_len=len(actual))

    assert result["score"], (
        "Ожидали вызов glucose_unit_converter (superset).\n"
        f"Comment: {result.get('comment', 'No comment')}\n"
        f"Trajectory length: {len(actual)}"
    )


async def test_insulin_storage_rag_superset(agent_fixture) -> None:
    """Справочный вопрос про хранение инсулина → минимум rag_search."""
    user_message = "Как хранить инсулин?"
    actual = await extract_trajectory(
        agent_fixture, "test_rag_insulin_1", user_message
    )
    print_trajectory(actual)

    reference = [
        HumanMessage(content=user_message),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "rag_search",
                    "args": {"query": "хранение инсулина"},
                    "id": "call_1",
                }
            ],
        ),
        ToolMessage(
            content='{"sources": []}',
            name="rag_search",
            tool_call_id="call_1",
        ),
        AIMessage(content="Инсулин хранят в холодильнике..."),
    ]

    evaluator = create_trajectory_match_evaluator(
        trajectory_match_mode="superset",
        tool_args_match_mode="ignore",
    )
    result = evaluator(outputs=actual, reference_outputs=reference)
    _log_match_result(result, trajectory_len=len(actual))

    assert result["score"], (
        "Ожидали вызов rag_search для хранения инсулина (superset).\n"
        f"Comment: {result.get('comment', 'No comment')}\n"
        f"Trajectory length: {len(actual)}"
    )


async def test_glucose_converter_exact_args(agent_fixture) -> None:
    """Конвертация 5.5 ммоль/л → мг/дл с проверкой аргументов (exact)."""
    user_message = "Переведи 5.5 ммоль/л в мг/дл"
    actual = await extract_trajectory(
        agent_fixture, "test_glucose_exact_1", user_message
    )
    print_trajectory(actual)

    reference = [
        HumanMessage(content=user_message),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "glucose_unit_converter",
                    "args": {
                        "value": 5.5,
                        "from_unit": "mmol_l",
                        "to_unit": "mg_dl",
                    },
                    "id": "call_1",
                }
            ],
        ),
        ToolMessage(
            content="5.5 ммоль/л = 99.00 мг/дл",
            name="glucose_unit_converter",
            tool_call_id="call_1",
        ),
        AIMessage(content="5.5 ммоль/л это 99.00 мг/дл."),
    ]

    evaluator = create_trajectory_match_evaluator(
        trajectory_match_mode="superset",
        tool_args_match_mode="exact",
    )
    result = evaluator(outputs=actual, reference_outputs=reference)
    _log_match_result(result, trajectory_len=len(actual))

    assert result["score"], (
        "Ожидали glucose_unit_converter с точными args "
        "(value=5.5, from_unit=mmol_l, to_unit=mg_dl).\n"
        f"Comment: {result.get('comment', 'No comment')}\n"
        f"Trajectory length: {len(actual)}"
    )


async def test_search_products_subset(agent_fixture) -> None:
    """Вопрос про полоски → только search_products, без rag_search (subset)."""
    if "search_products" not in agent_fixture.mcp_tool_names:
        pytest.skip("MCP недоступен — запусти make run-mcp-nika")

    user_message = "Какие полоски к Contour Plus?"
    actual = await extract_trajectory(
        agent_fixture, "test_products_subset_1", user_message
    )
    print_trajectory(actual)

    reference = [
        HumanMessage(content=user_message),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "search_products",
                    "args": {"query": "Contour Plus"},
                    "id": "call_1",
                }
            ],
        ),
        ToolMessage(
            content='{"products": []}',
            name="search_products",
            tool_call_id="call_1",
        ),
        AIMessage(content="Подходят полоски Contour Plus..."),
    ]

    # subset: агент не должен вызывать tools вне reference (напр. rag_search)
    evaluator = create_trajectory_match_evaluator(
        trajectory_match_mode="subset",
        tool_args_match_mode="ignore",
    )
    result = evaluator(outputs=actual, reference_outputs=reference)
    _log_match_result(result, trajectory_len=len(actual))

    assert result["score"], (
        "Ожидали только search_products (subset), без лишних tools.\n"
        f"Comment: {result.get('comment', 'No comment')}\n"
        f"Trajectory length: {len(actual)}"
    )
