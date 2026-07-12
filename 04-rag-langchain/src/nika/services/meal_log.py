import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "Информация справочная и не заменяет консультацию специалиста."
)
GRAMS_PER_BREAD_UNIT = 12.0
DEFAULT_BOLUS_MINUTES = 15


@dataclass
class MealEntry:
    datetime: datetime
    product: str
    quantity: str
    proteins_g: float | None = None
    fats_g: float | None = None
    carbs_g: float | None = None
    bread_units: float | None = None
    sugar_before: float | None = None
    sugar_after: float | None = None
    insulin_dose: float | None = None
    bolus_minutes_before: int | None = None
    meal_type: str | None = None
    notes: str = ""


class MealExtraction(BaseModel):
    should_log: bool = Field(
        description=(
            "True, если пользователь сообщает о приёме пищи, сахаре или инсулине"
        ),
    )
    needs_clarification: bool = Field(
        description="True, если для записи не хватает ключевых данных",
    )
    product: str | None = None
    quantity: str | None = None
    proteins_g: float | None = None
    fats_g: float | None = None
    carbs_g: float | None = None
    bread_units: float | None = None
    sugar_before: float | None = None
    sugar_after: float | None = None
    insulin_dose: float | None = None
    bolus_minutes_before: int | None = None
    meal_type: str | None = None
    notes: str = ""
    reply_text: str = Field(
        description="Ответ Нике: спокойно, от женского лица, с дисклеймером",
    )

    def to_meal_entry(self) -> MealEntry:
        return MealEntry(
            datetime=datetime.now(),
            product=self.product or "не указано",
            quantity=self.quantity or "не указано",
            proteins_g=self.proteins_g,
            fats_g=self.fats_g,
            carbs_g=self.carbs_g,
            bread_units=self.bread_units,
            sugar_before=self.sugar_before,
            sugar_after=self.sugar_after,
            insulin_dose=self.insulin_dose,
            bolus_minutes_before=self.bolus_minutes_before,
            meal_type=self.meal_type,
            notes=self.notes,
        )

    def sanitize(self) -> "MealExtraction":
        bolus = self.bolus_minutes_before
        if bolus is None or bolus < 5 or bolus > 120:
            bolus = DEFAULT_BOLUS_MINUTES

        return self.model_copy(
            update={
                "sugar_before": _normalize_glucose(self.sugar_before),
                "sugar_after": _normalize_glucose(self.sugar_after),
                "bolus_minutes_before": bolus,
                "bread_units": self._normalized_bread_units(),
            },
        )

    def _normalized_bread_units(self) -> float | None:
        if self.bread_units is not None:
            return self.bread_units
        if self.carbs_g is not None:
            return self.carbs_g / GRAMS_PER_BREAD_UNIT
        return None

    def finalize_for_photo(self, description: str) -> "MealExtraction":
        product = _clean_product(self.product) or _guess_product(description)
        quantity = _clean_quantity(self.quantity)
        has_nutrition = (
            self.carbs_g is not None
            or self.bread_units is not None
            or (self.proteins_g is not None and self.proteins_g > 0)
        )
        needs_clarification = product is None and not has_nutrition

        return self.model_copy(
            update={
                "product": product,
                "quantity": quantity,
                "needs_clarification": needs_clarification,
                "should_log": product is not None or has_nutrition,
            },
        )

    def display_product(self) -> str | None:
        product = _clean_product(self.product)
        return product

    def display_quantity(self) -> str | None:
        return _clean_quantity(self.quantity)

    def bread_units_estimate(self) -> float | None:
        if self.bread_units is not None:
            return self.bread_units
        if self.carbs_g is not None:
            return self.carbs_g / GRAMS_PER_BREAD_UNIT
        return None

    def build_reply(self) -> str:
        lines = ["Записала приём пищи."]
        if self.product:
            lines.append(f"• Продукт: {self.product}")
        if self.quantity and self.quantity not in {"?", "не указано"}:
            lines.append(f"• Порция: {self.quantity}")

        if self.carbs_g is not None:
            carbs_text = f"{self.carbs_g:.0f}".rstrip("0").rstrip(".")
            lines.append(f"• Углеводы: ~{carbs_text} г")

        xe = self.bread_units_estimate()
        if xe is not None:
            xe_text = f"{xe:.1f}".rstrip("0").rstrip(".")
            lines.append(f"• Хлебные единицы: ~{xe_text} ХЕ")
        elif self.carbs_g is None:
            lines.append("• Углеводы: не удалось оценить")

        if self.proteins_g is not None or self.fats_g is not None:
            proteins = self.proteins_g or 0
            fats = self.fats_g or 0
            lines.append(f"• Белки: {proteins:g} г, жиры: {fats:g} г")
            bje = (proteins + fats) / 10
            if bje > 0:
                bje_text = f"{bje:.1f}".rstrip("0").rstrip(".")
                lines.append(f"• БЖЕ для доколки: ~{bje_text}")

        if self.sugar_before is not None:
            sugar_text = f"{self.sugar_before:.1f}".rstrip("0").rstrip(".")
            lines.append(f"• Сахар до еды: {sugar_text} ммоль/л")

        lines.append("")
        lines.append(DISCLAIMER)
        return "\n".join(lines)

    def insulin_note(self) -> str | None:
        xe = self.bread_units_estimate()
        if xe is None:
            return (
                "Не удалось оценить углеводы — уточни состав блюда.\n\n"
                f"{DISCLAIMER}"
            )
        if xe < 0.5:
            xe_text = f"{xe:.1f}".rstrip("0").rstrip(".")
            return (
                f"Углеводов мало (~{xe_text} ХЕ) — доколка на еду обычно не нужна.\n\n"
                f"{DISCLAIMER}"
            )
        return None

    def build_clarification_reply(self) -> str:
        product = self.display_product()
        lines: list[str] = []

        if product:
            lines.append(f"На фото вижу {product}.")
        else:
            lines.append("На фото что-то съедобное, но название не уверена.")

        quantity = self.display_quantity()
        if quantity:
            lines.append(f"Примерная порция: {quantity}.")

        xe = self.bread_units_estimate()
        if xe is not None and xe > 0:
            xe_text = f"{xe:.1f}".rstrip("0").rstrip(".")
            lines.append(f"Ориентировочно ~{xe_text} ХЕ.")

        if self.proteins_g or self.fats_g:
            proteins = self.proteins_g or 0
            fats = self.fats_g or 0
            bje = (proteins + fats) / 10
            if bje > 0:
                bje_text = f"{bje:.1f}".rstrip("0").rstrip(".")
                lines.append(f"БЖЕ для доколки: ~{bje_text}.")

        lines.append(
            "Подскажи порцию в граммах и сахар (ммоль/л) — посчитаю точнее."
        )
        lines.append("")
        lines.append(DISCLAIMER)
        return "\n".join(lines)


class MealLogStore:
    def __init__(self, data_file: str) -> None:
        self._path = Path(data_file)
        self._entries: list[MealEntry] = []
        self._load()

    def append(self, entry: MealEntry) -> None:
        self._entries.append(entry)
        self._save()
        logger.info("meal log: appended entry product=%s", entry.product)

    def get_all(self) -> list[MealEntry]:
        return list(self._entries)

    def get_since(self, since: datetime) -> list[MealEntry]:
        return [entry for entry in self._entries if entry.datetime >= since]

    def clear(self) -> None:
        self._entries = []
        self._save()
        logger.info("meal log: cleared")

    def _load(self) -> None:
        if not self._path.exists():
            return

        raw = json.loads(self._path.read_text(encoding="utf-8"))
        self._entries = [_entry_from_dict(item) for item in raw]
        logger.info(
            "meal log: loaded %d entries from %s",
            len(self._entries),
            self._path,
        )

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = [_entry_to_dict(entry) for entry in self._entries]
        self._path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _entry_to_dict(entry: MealEntry) -> dict[str, object]:
    data = asdict(entry)
    data["datetime"] = entry.datetime.isoformat()
    return data


def _entry_from_dict(data: dict[str, object]) -> MealEntry:
    datetime_raw = data["datetime"]
    if not isinstance(datetime_raw, str):
        raise ValueError("meal entry datetime must be a string")

    return MealEntry(
        datetime=datetime.fromisoformat(datetime_raw),
        product=_require_str(data, "product"),
        quantity=_require_str(data, "quantity"),
        proteins_g=_optional_float(data, "proteins_g"),
        fats_g=_optional_float(data, "fats_g"),
        carbs_g=_optional_float(data, "carbs_g"),
        bread_units=_optional_float(data, "bread_units"),
        sugar_before=_optional_float(data, "sugar_before"),
        sugar_after=_optional_float(data, "sugar_after"),
        insulin_dose=_optional_float(data, "insulin_dose"),
        bolus_minutes_before=_optional_int(data, "bolus_minutes_before"),
        meal_type=_optional_str(data, "meal_type"),
        notes=_optional_str(data, "notes") or "",
    )


def _require_str(data: dict[str, object], key: str) -> str:
    value = data[key]
    if not isinstance(value, str):
        raise ValueError(f"meal entry {key} must be a string")
    return value


def _optional_str(data: dict[str, object], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"meal entry {key} must be a string")
    return value


def _optional_float(data: dict[str, object], key: str) -> float | None:
    value = data.get(key)
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    raise ValueError(f"meal entry {key} must be a number")


def _optional_int(data: dict[str, object], key: str) -> int | None:
    value = data.get(key)
    if value is None:
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    raise ValueError(f"meal entry {key} must be an integer")


def _normalize_glucose(value: float | None) -> float | None:
    if value is None:
        return None
    if value > 33:
        if 40 <= value <= 600:
            return round(value / 18.0, 1)
        return None
    if value < 1:
        return None
    return value


def _clean_product(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    if cleaned.lower() in {"null", "none", "не указано", "?"}:
        return None
    if len(cleaned) < 2:
        return None
    return cleaned


def _clean_quantity(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    if cleaned.lower() in {"null", "none", "не указано", "?"}:
        return None
    if len(cleaned) > 30:
        return None
    return cleaned


def _guess_product(description: str) -> str | None:
    lower = description.lower()
    if "продукт:" in lower:
        for line in description.splitlines():
            if line.lower().startswith("продукт:"):
                return _clean_product(line.split(":", 1)[1].strip())
    return None
