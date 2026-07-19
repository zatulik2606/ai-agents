"""Мок-заказ расходников для диабета (критичная операция для HITL/PII)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Luhn-валидный тестовый номер (Mastercard) — для демо PIIMiddleware.
MOCK_CARD_NUMBER = "5105-1051-0510-5100"


def _payment_system(card_number: str) -> str:
    first = card_number.replace("-", "").replace(" ", "")[:1]
    if first == "4":
        return "Visa"
    if first == "5":
        return "Mastercard"
    if first == "2":
        return "МИР"
    return "Unknown"


def place_care_product_order(*, product_name: str, client_name: str) -> str:
    """Оформить мок-заказ. Номер карты в ответе — без маскирования."""
    holder = client_name.strip().upper()
    product = product_name.strip()
    order_id = f"NIKA-{uuid.uuid4().hex[:8].upper()}"
    expiration = (datetime.now() + timedelta(days=3 * 365)).strftime("%m/%y")
    payment_system = _payment_system(MOCK_CARD_NUMBER)

    logger.info(
        "order_care_product: order_id=%s product=%r client=%s",
        order_id,
        product,
        holder,
    )

    return (
        "Заказ расходников успешно оформлен.\n\n"
        f"Номер заказа: {order_id}\n"
        f"Товар: {product}\n"
        f"Получатель: {holder}\n"
        f"Платёжная система: {payment_system}\n"
        f"Номер карты оплаты: {MOCK_CARD_NUMBER}\n"
        f"Срок действия карты: {expiration}\n"
        "Статус: оплачен (мок)\n\n"
        "CVV не возвращается — учебная мок-операция, не реальный платёж."
    )
