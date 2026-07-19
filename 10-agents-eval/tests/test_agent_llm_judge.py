"""E2E LLM-as-a-Judge тесты агента Ники (agentevals)."""

from __future__ import annotations

import logging

import pytest
from agentevals.trajectory.llm import (
    TRAJECTORY_ACCURACY_PROMPT_WITH_REFERENCE,
    create_async_trajectory_llm_as_judge,
)
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from nika.config import Config
from tests.helpers import extract_trajectory, print_trajectory

logger = logging.getLogger(__name__)


async def _judge_with_reference(
    actual: list,
    reference: list,
    *,
    label: str,
) -> dict:
    judge_model = Config.from_env().agentevals_llm_model
    evaluator = create_async_trajectory_llm_as_judge(
        prompt=TRAJECTORY_ACCURACY_PROMPT_WITH_REFERENCE,
        model=judge_model,
    )
    result = await evaluator(outputs=actual, reference_outputs=reference)
    score = result.get("score", 0)
    comment = result.get("comment", "No comment")
    logger.info("=" * 60)
    logger.info("LLM-AS-JUDGE RESULT: %s", label)
    logger.info("   Score: %s", score)
    logger.info("   Comment: %s", comment)
    logger.info("   Model: %s", judge_model)
    logger.info("   Trajectory length: %s", len(actual))
    logger.info("=" * 60)
    return result


async def test_search_products_llm_judge(agent_fixture) -> None:
    """Вопрос про полоски Contour → уместная траектория с search_products."""
    if "search_products" not in agent_fixture.mcp_tool_names:
        pytest.skip("MCP недоступен — запусти make run-mcp-nika")

    user_message = "Какие полоски к Contour Plus?"
    actual = await extract_trajectory(agent_fixture, "test_products_judge_1", user_message)
    print_trajectory(actual)

    reference = [
        HumanMessage(content=user_message),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "search_products",
                    "args": {"query": "Contour Plus полоски"},
                    "id": "call_1",
                }
            ],
        ),
        ToolMessage(
            content='[{"name": "Contour Plus", "type": "test_strips"}]',
            name="search_products",
            tool_call_id="call_1",
        ),
        AIMessage(
            content=(
                "Для глюкометра Contour Plus подходят тест-полоски "
                "Contour Plus / Contour Plus One."
            )
        ),
    ]

    result = await _judge_with_reference(
        actual, reference, label="search_products"
    )
    score = result.get("score", 0)
    comment = result.get("comment", "No comment")

    # bool True == 1.0; float score — порог как в эталоне курса
    assert score > 0.7, (
        "Ожидали LLM-as-a-Judge score > 0.7 для search_products.\n"
        f"Actual score: {score}\n"
        f"Comment: {comment}\n"
        f"Trajectory length: {len(actual)}"
    )


async def test_glucose_converter_llm_judge(agent_fixture) -> None:
    """Конвертация единиц → judge сверяет траекторию с эталоном glucose_unit_converter."""
    user_message = "Переведи 180 мг/дл в ммоль/л"
    actual = await extract_trajectory(
        agent_fixture, "test_glucose_judge_1", user_message
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
                        "value": 180,
                        "from_unit": "mg_dl",
                        "to_unit": "mmol_l",
                    },
                    "id": "call_1",
                }
            ],
        ),
        ToolMessage(
            content="180 мг/дл = 10.00 ммоль/л",
            name="glucose_unit_converter",
            tool_call_id="call_1",
        ),
        AIMessage(
            content=(
                "180 мг/дл это 10.00 ммоль/л. "
                "Информация справочная и не заменяет консультацию специалиста."
            )
        ),
    ]

    result = await _judge_with_reference(
        actual, reference, label="glucose_unit_converter"
    )
    score = result.get("score", 0)
    comment = result.get("comment", "No comment")

    assert score > 0.7, (
        "Ожидали LLM-as-a-Judge score > 0.7 для glucose_unit_converter.\n"
        f"Actual score: {score}\n"
        f"Comment: {comment}\n"
        f"Trajectory length: {len(actual)}"
    )
