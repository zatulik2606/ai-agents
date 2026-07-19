from langchain_core.tools import StructuredTool

# Фиксированный коэффициент (как курсы в currency_converter-заглушке).
# 1 ммоль/л ≈ 18 мг/дл.
_UNIT_TO_MMOL: dict[str, float] = {
    "mmol_l": 1.0,
    "mmol": 1.0,
    "ммоль": 1.0,
    "ммоль/л": 1.0,
    "mg_dl": 18.0,
    "mg/dl": 18.0,
    "мг/дл": 18.0,
    "мгдл": 18.0,
}

GLUCOSE_UNIT_CONVERTER_DESCRIPTION = """\
Конвертирует глюкозу крови между ммоль/л и мг/дл.

Вызывай, когда пользователь просит перевести значение сахара из одних единиц в другие
(например: «180 мг/дл это сколько ммоль?», «5.5 ммоль в мг/дл»).

Не вызывай для справочных вопросов о причинах/лечении — там нужен rag_search.
Не вызывай для записи приёма пищи.

Args:
    value: числовое значение глюкозы
    from_unit: исходные единицы (mmol_l | mg_dl | ммоль/л | мг/дл)
    to_unit: целевые единицы (mmol_l | mg_dl | ммоль/л | мг/дл)"""


def _normalize_unit(unit: str) -> str:
    key = unit.strip().lower().replace(" ", "")
    aliases = {
        "mmoll": "mmol_l",
        "mmol_l": "mmol_l",
        "mmol": "mmol_l",
        "ммоль": "mmol_l",
        "ммоль/л": "mmol_l",
        "ммольл": "mmol_l",
        "mgdl": "mg_dl",
        "mg_dl": "mg_dl",
        "mg/dl": "mg_dl",
        "мг/дл": "mg_dl",
        "мгдл": "mg_dl",
    }
    normalized = aliases.get(key)
    if normalized is None:
        msg = (
            f"Неизвестные единицы: {unit!r}. "
            "Допустимы mmol_l / mg_dl (ммоль/л / мг/дл)."
        )
        raise ValueError(msg)
    return normalized


def convert_glucose(value: float, from_unit: str, to_unit: str) -> str:
    src = _normalize_unit(from_unit)
    dst = _normalize_unit(to_unit)
    if value < 0:
        return "Значение глюкозы не может быть отрицательным."

    mmol = value / _UNIT_TO_MMOL[src]
    converted = mmol * _UNIT_TO_MMOL[dst]
    labels = {"mmol_l": "ммоль/л", "mg_dl": "мг/дл"}
    return f"{value:g} {labels[src]} = {converted:.2f} {labels[dst]}"


def create_glucose_unit_converter_tool() -> StructuredTool:
    def glucose_unit_converter(value: float, from_unit: str, to_unit: str) -> str:
        """Конвертирует глюкозу между ммоль/л и мг/дл."""
        try:
            return convert_glucose(value, from_unit, to_unit)
        except ValueError as error:
            return str(error)

    return StructuredTool.from_function(
        func=glucose_unit_converter,
        name="glucose_unit_converter",
        description=GLUCOSE_UNIT_CONVERTER_DESCRIPTION,
    )
