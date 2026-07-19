from __future__ import annotations

import json
import logging
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from mcp_nika_agent.meal_bolus import calculate_meal_bolus, format_meal_bolus_result
from mcp_nika_agent.nutrition_client import lookup_food_nutrition
from mcp_nika_agent.order_care_product import place_care_product_order
from mcp_nika_agent.product_catalog import search_products as catalog_search
from mcp_nika_agent.register_cgm_sensor import register_sensor

logger = logging.getLogger(__name__)

mcp = FastMCP("mcp-nika-agent")


@mcp.tool
def search_products(query: str) -> str:
    """Поиск средств и расходников для диабета (глюкометры, полоски, CGM, помпы, ручки).

    Используй для вопросов о совместимости полосок, моделях CGM/помп и расходниках.
    Данные из каталога сервера — не из PDF-руководства.
    """
    matches = catalog_search(query)
    if not matches:
        return json.dumps(
            {"query": query, "count": 0, "products": []},
            ensure_ascii=False,
        )
    return json.dumps(
        {"query": query, "count": len(matches), "products": matches},
        ensure_ascii=False,
    )


@mcp.tool
def food_nutrition(query: str) -> str:
    """Онлайн-поиск КБЖУ/углеводов продукта питания через Open Food Facts.

    Используй, когда нужны актуальные пищевые данные (белки, жиры, углеводы на 100 г).
    Для сырых продуктов можно передавать русское или английское название
    (банан / banana). В ответе смотри поле summary или best.per_100g.carbohydrates_g.
    Не заменяет учёт приёма пищи пользователя из сообщения/фото.
    """
    try:
        payload = lookup_food_nutrition(query)
    except Exception as exc:
        logger.exception("Open Food Facts request failed")
        return json.dumps(
            {"query": query, "error": str(exc), "count": 0, "items": [], "best": None},
            ensure_ascii=False,
        )
    return json.dumps(payload, ensure_ascii=False)


@mcp.tool(
    name="calculate_meal_bolus",
    description=(
        "Оценка ХЕ (хлебных единиц) и болюса инсулина на еду: "
        "углеводы → ХЕ и ЕД (единицы инсулина), опционально коррекция по сахару "
        "и БЖЕ (белково-жировые единицы). Справочный расчёт, не назначение."
    ),
)
def calculate_meal_bolus_tool(
    carbs_g: Annotated[
        float,
        Field(description="Углеводы в граммах", ge=0, le=500),
    ],
    carb_ratio: Annotated[
        float,
        Field(
            description=(
                "Углеводный коэффициент "
                "(сколько граммов углеводов покрывает 1 ЕД инсулина)"
            ),
            ge=1,
            le=50,
        ),
    ] = 12.0,
    current_glucose_mmol: Annotated[
        float | None,
        Field(
            description="Текущий сахар в ммоль/л (для коррекции); null если не нужен",
            ge=1,
            le=40,
        ),
    ] = None,
    target_glucose_mmol: Annotated[
        float,
        Field(description="Целевой сахар в ммоль/л", ge=3, le=15),
    ] = 6.0,
    insulin_sensitivity: Annotated[
        float,
        Field(
            description=(
                "Чувствительность к инсулину "
                "(на сколько ммоль/л снижает сахар 1 ЕД)"
            ),
            ge=0.5,
            le=20,
        ),
    ] = 2.0,
    proteins_g: Annotated[
        float,
        Field(
            description="Белки в граммах (для расчёта БЖЕ — белково-жировых единиц)",
            ge=0,
            le=300,
        ),
    ] = 0.0,
    fats_g: Annotated[
        float,
        Field(
            description="Жиры в граммах (для расчёта БЖЕ — белково-жировых единиц)",
            ge=0,
            le=300,
        ),
    ] = 0.0,
    fpu_ratio: Annotated[
        float,
        Field(
            description=(
                "Коэффициент БЖЕ "
                "(сколько граммов белков+жиров соответствует 1 ЕД)"
            ),
            ge=1,
            le=50,
        ),
    ] = 10.0,
    include_fpu: Annotated[
        bool,
        Field(
            description=(
                "Учитывать БЖЕ (белково-жировые единицы) в итоговой дозе"
            ),
        ),
    ] = False,
) -> str:
    """Формульный расчёт ХЕ/болюса для домена Ники."""
    payload = calculate_meal_bolus(
        carbs_g=carbs_g,
        carb_ratio=carb_ratio,
        current_glucose_mmol=current_glucose_mmol,
        target_glucose_mmol=target_glucose_mmol,
        insulin_sensitivity=insulin_sensitivity,
        proteins_g=proteins_g,
        fats_g=fats_g,
        fpu_ratio=fpu_ratio,
        include_fpu=include_fpu,
    )
    text = format_meal_bolus_result(payload)
    return json.dumps({"result": payload, "text": text}, ensure_ascii=False)


@mcp.tool(
    name="order_care_product",
    description=(
        "Оформление заказа расходников для диабета (мок): полоски, сенсоры CGM, "
        "ланцеты и т.п. Требует подтверждения пользователя. Возвращает номер "
        "заказа и номер карты оплаты без маскирования."
    ),
)
def order_care_product_tool(
    product_name: Annotated[
        str,
        Field(
            description=(
                "Название или тип расходника "
                "(например: Contour Plus полоски, FreeStyle Libre 3 сенсор)"
            ),
            min_length=2,
            max_length=120,
        ),
    ],
    client_name: Annotated[
        str,
        Field(
            description=(
                "Имя получателя латиницей, как на карте оплаты "
                "(например: IVAN PETROV)"
            ),
            min_length=3,
            max_length=26,
        ),
    ],
) -> str:
    """Мок-заказ расходников. Критичная операция — HITL на стороне агента."""
    return place_care_product_order(
        product_name=product_name,
        client_name=client_name,
    )


@mcp.tool(
    name="register_cgm_sensor",
    description=(
        "Регистрация сенсора CGM для гарантии (мок): модель сенсора и имя "
        "владельца. Требует подтверждения пользователя. Возвращает номер "
        "регистрации."
    ),
)
def register_cgm_sensor_tool(
    sensor_model: Annotated[
        str,
        Field(
            description=(
                "Модель сенсора CGM "
                "(например: FreeStyle Libre 3, Dexcom G6)"
            ),
            min_length=2,
            max_length=80,
        ),
    ],
    client_name: Annotated[
        str,
        Field(
            description=(
                "Имя владельца латиницей "
                "(например: IVAN PETROV)"
            ),
            min_length=3,
            max_length=26,
        ),
    ],
) -> str:
    """Мок-регистрация CGM. Критичная операция — HITL на стороне агента."""
    return register_sensor(sensor_model=sensor_model, client_name=client_name)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
