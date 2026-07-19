from dataclasses import dataclass

from nika.config import Config

DISCLAIMER = (
    "Информация справочная и не заменяет консультацию специалиста."
)
GRAMS_PER_BREAD_UNIT = 12.0
DEFAULT_BOLUS_MINUTES = 15


@dataclass(frozen=True)
class InsulinRecommendation:
    bread_units: float
    total_dose: float
    bolus_minutes_before: int

    def format_message(self) -> str:
        xe_text = f"{self.bread_units:.1f}".rstrip("0").rstrip(".")
        dose_text = f"{self.total_dose:.1f}".rstrip("0").rstrip(".")
        return (
            f"На {xe_text} ХЕ рекомендую доколоть {dose_text} ЕД "
            f"за {self.bolus_minutes_before} мин до еды "
            f"(углеводы + коррекция + БЖЕ). {DISCLAIMER}"
        )


class InsulinCalculator:
    def __init__(self, config: Config) -> None:
        self._carb_ratio = config.carb_ratio
        self._sensitivity = config.insulin_sensitivity
        self._target_glucose_min = config.target_glucose_min
        self._target_glucose_max = config.target_glucose_max
        self._fpu_ratio = config.fpu_ratio

    def recommend(
        self,
        carbs_g: float | None,
        bread_units: float | None,
        proteins_g: float | None,
        fats_g: float | None,
        sugar_before: float | None,
        bolus_minutes_before: int | None,
    ) -> InsulinRecommendation | None:
        effective_carbs = carbs_g
        if effective_carbs is None and bread_units is not None:
            effective_carbs = bread_units * GRAMS_PER_BREAD_UNIT

        if effective_carbs is None:
            return None

        carb_dose = effective_carbs / self._carb_ratio
        correction = 0.0
        if sugar_before is not None:
            correction = self._correction(sugar_before)

        proteins = proteins_g or 0.0
        fats = fats_g or 0.0
        fpu_dose = (proteins + fats) / self._fpu_ratio if (proteins or fats) else 0.0

        total_dose = _round_dose(carb_dose + correction + fpu_dose)
        if total_dose <= 0:
            return None

        xe = (
            bread_units
            if bread_units is not None
            else effective_carbs / GRAMS_PER_BREAD_UNIT
        )
        minutes = (
            bolus_minutes_before
            if bolus_minutes_before is not None
            else DEFAULT_BOLUS_MINUTES
        )

        return InsulinRecommendation(
            bread_units=xe,
            total_dose=total_dose,
            bolus_minutes_before=minutes,
        )

    def _correction(self, sugar_before: float) -> float:
        if self._target_glucose_min <= sugar_before <= self._target_glucose_max:
            return 0.0
        if sugar_before > self._target_glucose_max:
            return (sugar_before - self._target_glucose_max) / self._sensitivity
        return (sugar_before - self._target_glucose_min) / self._sensitivity


def _round_dose(value: float) -> float:
    return round(value * 2) / 2
