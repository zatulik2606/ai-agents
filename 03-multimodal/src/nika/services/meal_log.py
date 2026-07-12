import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


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
