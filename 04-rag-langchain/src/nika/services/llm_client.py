import base64
import logging

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionContentPartParam,
    ChatCompletionMessageParam,
)

from nika.config import Config
from nika.services.meal_log import MealExtraction

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """\
Ты — Ника, ассистентка по диабету. Классифицируешь сообщение и извлекаешь данные \
о приёме пищи, если это запись.

Правила классификации (взаимоисключающие):
- should_log=true — пользователь фиксирует КОНКРЕТНЫЙ приём: что съел, сахар сейчас, \
доколку («съел банан», «сахар 6.2», «доколю 3 ЕД на ужин»).
- is_reference_question=true — справочный вопрос БЕЗ записи приёма: «сколько инъекций \
в день», «что такое гипогликемия», «как хранить инсулин», «сколько раз колоть».
- should_log=false и is_reference_question=false — приветствие, «ты кто», small talk.

Важно: упоминание инсулина/инъекций в ВОПРОСЕ — is_reference_question, не should_log.
should_log и is_reference_question не могут быть true одновременно.

Примеры:
- «Съел банан 120 г, сахар 5.8» → should_log=true, is_reference_question=false
- «Сколько инъекций инсулина необходимо в день?» → should_log=false, \
is_reference_question=true
- «Что такое гипогликемия?» → should_log=false, is_reference_question=true
- «Привет, ты кто?» → should_log=false, is_reference_question=false
- «Доколю 3 ЕД за 15 мин, овсянка 200 г» → should_log=true, is_reference_question=false

Правила извлечения (если should_log=true):
- needs_clarification=true — только если продукт совсем не определить.
- Если источник — описание фото, оцени порцию, БЖУ и ХЕ по видимому размеру.
- product и quantity — только на русском языке.
- carbs_g, proteins_g, fats_g обязательны — оцени по справочнику для любого продукта.
- Огурец ~3 г угл/100 г, помидор ~4 г/100 г, банан ~20 г/100 г.
- bread_units = carbs_g / 12, если не указано иное.
- sugar_before — только ммоль/л; null, если пользователь не указал.
- bolus_minutes_before — 15, если не указано иное.
- reply_text — краткий черновик на русском (не показывается пользователю).
- Пиши ТОЛЬКО на русском. Термины: ХЕ, БЖЕ, ммоль/л. Без Biocarb, carbs и т.п.
- meal_type: breakfast, lunch, dinner, snack или null."""

PHOTO_DESCRIBE_PROMPT = """\
На фото еда или продукт (фрукт, овощ, блюдо). Ответь СТРОГО в формате:

Продукт: <название на русском>
Порция: <число г или штук, оценка по размеру на фото>
Детали: <кратко, 1 предложение>

Обязательно назови продукт. Оцени вес по видимому размеру.
Запрещено писать «сложно определить», «не вижу», «невозможно»."""

PHOTO_EXTRACTION_PROMPT = """\
Ты — Ника. Извлекаешь данные о еде по описанию фото.

Правила:
- should_log=true всегда, если в описании есть продукт.
- needs_clarification=false, если продукт назван — оцени БЖУ по справочнику.
- product — кратко на русском (помидор, яблоко, хлеб).
- quantity — только «150 г» или «1 шт», без длинных фраз.
- Оцени carbs_g, proteins_g, fats_g, bread_units (1 ХЕ = 12 г углеводов).
- sugar_before — только из подписи, ммоль/л.
- bolus_minutes_before — 15, если не указано.
- reply_text — краткий черновик на русском (не показывается пользователю).
- Пиши ТОЛЬКО на русском. Термины: ХЕ, БЖЕ, ммоль/л.
- meal_type: breakfast, lunch, dinner, snack или null."""


class LlmClient:
    def __init__(self, config: Config) -> None:
        self._client = AsyncOpenAI(
            base_url=config.llm_base_url,
            api_key=config.openrouter_api_key,
        )
        self._image_client = AsyncOpenAI(
            base_url=config.image_base_url,
            api_key=config.image_api_key,
        )
        self._model_text = config.model_text
        self._model_image = config.model_image
        self._model_audio = config.model_audio
        self._system_prompt = config.system_prompt
        self._use_cloud_structured = (
            config.image_base_url != config.llm_base_url
        )

    @property
    def model_image(self) -> str:
        return self._model_image

    @property
    def model_audio(self) -> str:
        return self._model_audio

    async def ask(self, text: str, history: list[BaseMessage]) -> str:
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": self._system_prompt},
        ]
        for item in history:
            if isinstance(item, HumanMessage):
                messages.append({"role": "user", "content": str(item.content)})
            elif isinstance(item, AIMessage):
                messages.append(
                    {"role": "assistant", "content": str(item.content)},
                )
        messages.append({"role": "user", "content": text})
        logger.info(
            "LLM request: model=%s messages=%d",
            self._model_text,
            len(messages),
        )
        response = await self._client.chat.completions.create(
            model=self._model_text,
            messages=messages,
        )
        content = response.choices[0].message.content
        return content or ""

    async def ask_brief(self, text: str) -> str:
        client, model = self._brief_client_model()
        logger.info("LLM ask_brief: model=%s", model)
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты Ника, ассистентка по диабету. "
                        "Отвечай кратко, только на русском, 2–3 предложения."
                    ),
                },
                {"role": "user", "content": text},
            ],
        )
        content = response.choices[0].message.content
        return content or ""

    def _brief_client_model(self) -> tuple[AsyncOpenAI, str]:
        if self._use_cloud_structured:
            return self._image_client, self._model_image
        return self._client, self._model_text

    async def extract_meal(self, text: str) -> MealExtraction:
        return await self._parse_meal(text, EXTRACTION_SYSTEM_PROMPT)

    async def _parse_meal(
        self,
        text: str,
        system_prompt: str,
    ) -> MealExtraction:
        client, model = self._structured_client_model()
        logger.info("LLM parse_meal: model=%s", model)
        response = await client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            response_format=MealExtraction,
        )
        parsed = response.choices[0].message.parsed
        if parsed is None:
            raise ValueError("LLM returned empty meal extraction")
        return parsed

    def _structured_client_model(self) -> tuple[AsyncOpenAI, str]:
        if self._use_cloud_structured:
            return self._image_client, self._model_image
        return self._client, self._model_text

    async def analyze_photo(
        self,
        image_bytes: bytes,
        caption: str = "",
    ) -> MealExtraction:
        if caption.strip():
            extraction = await self._extract_meal_from_photo(
                f"Пользователь отправил фото еды. Подпись: {caption}",
            )
            return extraction.finalize_for_photo(caption)

        description = await self._describe_photo(image_bytes, caption)
        logger.info("photo description: %s", description)

        extraction = await self._extract_meal_from_photo(
            f"Описание фото: {description}",
        )
        finalized = extraction.finalize_for_photo(description)

        if not finalized.should_log:
            return MealExtraction(
                should_log=False,
                needs_clarification=False,
                reply_text=_photo_failed_message(),
            )
        return finalized

    async def _extract_meal_from_photo(self, text: str) -> MealExtraction:
        return await self._parse_meal(text, PHOTO_EXTRACTION_PROMPT)

    async def _describe_photo(self, image_bytes: bytes, caption: str) -> str:
        image_b64 = base64.standard_b64encode(image_bytes).decode()
        prompt = PHOTO_DESCRIBE_PROMPT
        if caption:
            prompt = f"{prompt}\n\nПодпись пользователя: {caption}"

        user_content: list[ChatCompletionContentPartParam] = [
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
            },
        ]
        logger.info("LLM describe_photo: model=%s", self._model_image)
        response = await self._image_client.chat.completions.create(
            model=self._model_image,
            messages=[{"role": "user", "content": user_content}],
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("LLM returned empty photo description")
        return content


def _photo_failed_message() -> str:
    return (
        "Не смогла разобрать фото. Попробуй:\n"
        "• сделать фото ближе, при хорошем свете;\n"
        "• добавить подпись: «1 помидор, 150 г, сахар 6.2»;\n"
        "• или напиши текстом, что съел.\n\n"
        "Информация справочная и не заменяет консультацию специалиста."
    )
