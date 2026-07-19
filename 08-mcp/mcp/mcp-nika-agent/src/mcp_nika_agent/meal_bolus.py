"""Оценка ХЕ и болюса на еду (справочный расчёт для MCP)."""

from __future__ import annotations

from typing import Any

# Как в головном InsulinCalculator Ники.
GRAMS_PER_XE = 12.0


def calculate_meal_bolus(
    *,
    carbs_g: float,
    carb_ratio: float = 12.0,
    current_glucose_mmol: float | None = None,
    target_glucose_mmol: float = 6.0,
    insulin_sensitivity: float = 2.0,
    proteins_g: float = 0.0,
    fats_g: float = 0.0,
    fpu_ratio: float = 10.0,
    include_fpu: bool = False,
) -> dict[str, Any]:
    """Оценить ХЕ, дозу на углеводы, коррекцию и опционально БЖЕ."""
    xe = carbs_g / GRAMS_PER_XE
    carb_dose = carbs_g / carb_ratio if carb_ratio > 0 else 0.0

    correction_dose = 0.0
    if current_glucose_mmol is not None and insulin_sensitivity > 0:
        correction_dose = (current_glucose_mmol - target_glucose_mmol) / insulin_sensitivity

    fpu_dose = 0.0
    if include_fpu and fpu_ratio > 0:
        fpu_dose = (proteins_g + fats_g) / fpu_ratio

    total = max(0.0, carb_dose + correction_dose + fpu_dose)

    return {
        "carbs_g": round(carbs_g, 1),
        "xe": round(xe, 2),
        "grams_per_xe": GRAMS_PER_XE,
        "carb_ratio": carb_ratio,
        "carb_dose_iu": round(carb_dose, 2),
        "current_glucose_mmol": current_glucose_mmol,
        "target_glucose_mmol": target_glucose_mmol,
        "insulin_sensitivity": insulin_sensitivity,
        "correction_dose_iu": round(correction_dose, 2),
        "include_fpu": include_fpu,
        "proteins_g": proteins_g,
        "fats_g": fats_g,
        "fpu_ratio": fpu_ratio,
        "fpu_dose_iu": round(fpu_dose, 2),
        "total_dose_iu": round(total, 2),
        "disclaimer": (
            "Справочный расчёт, не назначение. Решение о дозе — за пользователем "
            "и лечащим врачом."
        ),
    }


def format_meal_bolus_result(payload: dict[str, Any]) -> str:
    lines = [
        f"Углеводы: {payload['carbs_g']} г → {payload['xe']} ХЕ "
        f"(хлебные единицы; 1 ХЕ = {payload['grams_per_xe']} г углеводов).",
        f"Доза на углеводы: {payload['carb_dose_iu']} ЕД (единиц инсулина); "
        f"углеводный коэффициент {payload['carb_ratio']} "
        f"(граммов углеводов на 1 ЕД).",
    ]
    if payload["current_glucose_mmol"] is not None:
        lines.append(
            f"Коррекция: {payload['correction_dose_iu']} ЕД "
            f"(сахар {payload['current_glucose_mmol']} → цель "
            f"{payload['target_glucose_mmol']} ммоль/л; "
            f"чувствительность {payload['insulin_sensitivity']} "
            f"(на сколько ммоль/л снижает 1 ЕД))."
        )
    if payload["include_fpu"]:
        lines.append(
            f"БЖЕ (белково-жировые единицы): {payload['fpu_dose_iu']} ЕД "
            f"(белки {payload['proteins_g']} г + жиры {payload['fats_g']} г; "
            f"коэффициент БЖЕ {payload['fpu_ratio']} "
            f"(граммов белков+жиров на 1 ЕД))."
        )
    lines.append(f"Итого ориентир: {payload['total_dose_iu']} ЕД (единиц инсулина).")
    lines.append(payload["disclaimer"])
    return "\n".join(lines)
