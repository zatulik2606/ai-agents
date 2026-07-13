import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, time, timedelta

from nika.services.llm_client import LlmClient
from nika.services.meal_log import (
    DISCLAIMER,
    GRAMS_PER_BREAD_UNIT,
    MealEntry,
    MealLogStore,
)

logger = logging.getLogger(__name__)
WEEK_ANALYSIS_TIMEOUT_SEC = 45.0


@dataclass(frozen=True)
class PeriodStats:
    entries_count: int
    total_xe: float
    total_carbs_g: float
    total_insulin: float
    avg_sugar_before: float | None
    avg_sugar_after: float | None


class MealReport:
    def __init__(self, meal_log: MealLogStore, llm: LlmClient) -> None:
        self._meal_log = meal_log
        self._llm = llm

    def day_report(self) -> str:
        entries = self._entries_for_day()
        return self._format_report("день", entries)

    async def week_report(self) -> str:
        entries = self._entries_for_week()
        base = self._format_report("неделю", entries)
        if not entries:
            return base

        prompt = (
            "Проанализируй кратко динамику сахаров и доколок за неделю "
            f"(женский род, 2–3 предложения, только на русском):\n\n"
            f"{_strip_disclaimer(base)}"
        )
        try:
            analysis = await asyncio.wait_for(
                self._llm.ask_brief(prompt),
                timeout=WEEK_ANALYSIS_TIMEOUT_SEC,
            )
        except Exception:
            logger.exception("Week analysis failed")
            return base

        if not analysis.strip():
            return base

        return _append_analysis(base, analysis)

    def _entries_for_day(self) -> list[MealEntry]:
        since = datetime.combine(datetime.now().date(), time.min)
        return self._meal_log.get_since(since)

    def _entries_for_week(self) -> list[MealEntry]:
        since = datetime.now() - timedelta(days=7)
        return self._meal_log.get_since(since)

    def _format_report(self, period_label: str, entries: list[MealEntry]) -> str:
        if not entries:
            return f"За {period_label} записей нет."

        stats = _aggregate(entries)
        lines = [
            f"Сводка за {period_label}:",
            f"• Записей: {stats.entries_count}",
            f"• ХЕ всего: {_fmt(stats.total_xe)}",
            f"• Углеводы всего: {_fmt(stats.total_carbs_g)} г",
            f"• Инсулин всего: {_fmt(stats.total_insulin)} ЕД",
        ]

        if stats.avg_sugar_before is not None:
            avg = _fmt(stats.avg_sugar_before)
            lines.append(f"• Сахар до еды (средний): {avg} ммоль/л")
        if stats.avg_sugar_after is not None:
            avg = _fmt(stats.avg_sugar_after)
            lines.append(f"• Сахар после еды (средний): {avg} ммоль/л")

        lines.append("")
        lines.append(_bolus_note(entries))
        lines.append("")
        lines.append(DISCLAIMER)
        return "\n".join(lines)


def _aggregate(entries: list[MealEntry]) -> PeriodStats:
    total_xe = 0.0
    total_carbs = 0.0
    total_insulin = 0.0
    sugars_before: list[float] = []
    sugars_after: list[float] = []

    for entry in entries:
        if entry.bread_units is not None:
            total_xe += entry.bread_units
        elif entry.carbs_g is not None:
            total_xe += entry.carbs_g / GRAMS_PER_BREAD_UNIT

        if entry.carbs_g is not None:
            total_carbs += entry.carbs_g

        if entry.insulin_dose is not None:
            total_insulin += entry.insulin_dose
        if entry.sugar_before is not None:
            sugars_before.append(entry.sugar_before)
        if entry.sugar_after is not None:
            sugars_after.append(entry.sugar_after)

    return PeriodStats(
        entries_count=len(entries),
        total_xe=total_xe,
        total_carbs_g=total_carbs,
        total_insulin=total_insulin,
        avg_sugar_before=_avg(sugars_before),
        avg_sugar_after=_avg(sugars_after),
    )


def _bolus_note(entries: list[MealEntry]) -> str:
    pairs = [
        (entry.sugar_before, entry.sugar_after)
        for entry in entries
        if entry.sugar_before is not None and entry.sugar_after is not None
    ]
    if not pairs:
        return "Анализ доколок: мало данных о сахаре до и после еды."

    improved = sum(1 for before, after in pairs if after < before)
    return (
        f"Анализ доколок: сахар снизился в {improved} "
        f"из {len(pairs)} случаев с измерениями до/после."
    )


def _avg(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _fmt(value: float) -> str:
    text = f"{value:.1f}".rstrip("0").rstrip(".")
    return text


def _strip_disclaimer(text: str) -> str:
    suffix = f"\n\n{DISCLAIMER}"
    if text.endswith(suffix):
        return text[: -len(suffix)]
    return text


def _append_analysis(base: str, analysis: str) -> str:
    body = _strip_disclaimer(base)
    return f"{body}\n\n{analysis.strip()}\n\n{DISCLAIMER}"
