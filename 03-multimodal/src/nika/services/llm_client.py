import logging

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from nika.config import Config
from nika.services.chat_history import ChatMessage
from nika.services.meal_log import MealExtraction

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """\
Ты — Ника, ассистентка по диабету. Извлекаешь данные о приёме пищи из сообщения.

Правила:
- should_log=true — если пользователь сообщает о еде, сахаре, инсулине или доколке.
- should_log=false — для общих вопросов, приветствий, «кто ты» и т.п.
- needs_clarification=true — если should_log=true, но нет продукта/блюда.
- Оцени ХЕ (1 ХЕ ≈ 12 г углеводов), если можно.
- reply_text — ответ от первого лица, женский род, спокойно и поддерживающе.
- В reply_text всегда добавляй дисклеймер:
  «Информация справочная и не заменяет консультацию специалиста».
- meal_type: breakfast, lunch, dinner, snack или null."""


class LlmClient:
    def __init__(self, config: Config) -> None:
        self._client = AsyncOpenAI(
            base_url=config.llm_base_url,
            api_key=config.openrouter_api_key,
        )
        self._model = config.llm_model
        self._system_prompt = config.system_prompt

    async def ask(self, text: str, history: list[ChatMessage]) -> str:
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": self._system_prompt},
        ]
        for item in history:
            if item["role"] == "user":
                messages.append({"role": "user", "content": item["content"]})
            else:
                messages.append({"role": "assistant", "content": item["content"]})
        messages.append({"role": "user", "content": text})
        logger.info("LLM request: model=%s messages=%d", self._model, len(messages))
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
        )
        content = response.choices[0].message.content
        return content or ""

    async def extract_meal(self, text: str) -> MealExtraction:
        logger.info("LLM extract_meal: model=%s", self._model)
        response = await self._client.beta.chat.completions.parse(
            model=self._model,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            response_format=MealExtraction,
        )
        parsed = response.choices[0].message.parsed
        if parsed is None:
            raise ValueError("LLM returned empty meal extraction")
        return parsed
