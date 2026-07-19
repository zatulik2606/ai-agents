"""Мок-регистрация сенсора CGM (вторая критичная операция для HITL)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def register_sensor(*, sensor_model: str, client_name: str) -> str:
    """Зарегистрировать сенсор. Возвращает номер регистрации (мок)."""
    model = sensor_model.strip()
    holder = client_name.strip().upper()
    registration_id = f"CGM-{uuid.uuid4().hex[:8].upper()}"
    warranty_until = (datetime.now() + timedelta(days=365)).strftime("%d.%m.%Y")

    logger.info(
        "register_cgm_sensor: id=%s model=%r client=%s",
        registration_id,
        model,
        holder,
    )

    return (
        "Сенсор CGM успешно зарегистрирован.\n\n"
        f"Номер регистрации: {registration_id}\n"
        f"Модель: {model}\n"
        f"Владелец: {holder}\n"
        f"Гарантия до: {warranty_until}\n"
        "Статус: активна (мок)\n\n"
        "Учебная мок-операция — реальная регистрация у производителя не выполняется."
    )
