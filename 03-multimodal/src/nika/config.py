import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

DEFAULT_SYSTEM_PROMPT = """\
Ты — Ника, дружелюбная ассистентка для человека с диабетом.
Представляйся по имени «Ника», если уместно
(первое сообщение или спросили, как тебя зовут).
Говори от первого лица в женском роде: «рада», «поняла», «подскажу», «готова помочь».

Твоя задача — помогать с оценкой углеводов (ХЕ), обсуждением питания
и контекста инсулина.

Ты умеешь:
- помогать оценить ХЕ в продуктах и блюдах;
- обсуждать питание при диабете;
- рассчитывать доколку инсулина на БЖЕ (белково-жировые единицы)
  по коэффициентам, которые указал пользователь.

Важные правила:
- Пиши спокойно и поддерживающе.
- Не назначай дозы инсулина и не подменяй врача.
- Помогай с расчётами только на основе данных пользователя
  (коэффициенты, чувствительность, целевой сахар).
- Всегда добавляй дисклеймер: информация справочная
  и не заменяет консультацию специалиста.
- Если данных мало, задавай уточняющие вопросы.
- Пиши ТОЛЬКО на русском языке. Без английских слов и латиницы."""


DEFAULT_MODEL_TEXT = "openai/gpt-4o-mini"
DEFAULT_MODEL_AUDIO = "openai/whisper-1"

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OLLAMA_BASE_URL = "http://localhost:11434/v1"


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    openrouter_api_key: str
    llm_provider: str
    llm_base_url: str
    model_text: str
    model_image: str
    model_audio: str
    image_base_url: str
    image_api_key: str
    audio_base_url: str
    audio_api_key: str
    system_prompt: str
    data_file: str
    carb_ratio: float
    insulin_sensitivity: float
    target_glucose_min: float
    target_glucose_max: float
    fpu_ratio: float

    @classmethod
    def from_env(cls) -> "Config":
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set")

        provider = os.getenv("LLM_PROVIDER", "openrouter")
        if provider not in {"openrouter", "ollama"}:
            raise ValueError(f"Unknown LLM_PROVIDER: {provider}")

        model_text = (
            os.getenv("MODEL_TEXT")
            or os.getenv("LLM_MODEL")
            or DEFAULT_MODEL_TEXT
        )

        return cls(
            telegram_bot_token=token,
            openrouter_api_key=_api_key(provider),
            llm_provider=provider,
            llm_base_url=_base_url(provider),
            model_text=model_text,
            model_image=os.getenv("MODEL_IMAGE", model_text),
            model_audio=os.getenv("MODEL_AUDIO", DEFAULT_MODEL_AUDIO),
            image_base_url=os.getenv("IMAGE_LLM_BASE_URL") or _base_url(provider),
            image_api_key=_image_api_key(provider),
            audio_base_url=os.getenv("AUDIO_LLM_BASE_URL") or _base_url(provider),
            audio_api_key=_audio_api_key(provider),
            system_prompt=os.getenv("SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT),
            data_file=os.getenv("DATA_FILE", "data/meals.json"),
            carb_ratio=_float_env("CARB_RATIO", 12.0),
            insulin_sensitivity=_float_env("INSULIN_SENSITIVITY", 2.0),
            target_glucose_min=_float_env("TARGET_GLUCOSE_MIN", 5.0),
            target_glucose_max=_float_env("TARGET_GLUCOSE_MAX", 10.0),
            fpu_ratio=_float_env("FPU_RATIO", 10.0),
        )


def _base_url(provider: str) -> str:
    explicit = os.getenv("LLM_BASE_URL")
    if explicit:
        return explicit
    if provider == "ollama":
        return OLLAMA_BASE_URL
    return OPENROUTER_BASE_URL


def _api_key(provider: str) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if provider == "ollama" and not api_key:
        return "ollama"
    return api_key


def _image_api_key(provider: str) -> str:
    image_key = os.getenv("IMAGE_OPENROUTER_API_KEY", "")
    if image_key:
        return image_key
    return _api_key(provider)


def _audio_api_key(provider: str) -> str:
    audio_key = os.getenv("AUDIO_OPENROUTER_API_KEY", "")
    if audio_key:
        return audio_key
    return _api_key(provider)


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    return float(raw)
