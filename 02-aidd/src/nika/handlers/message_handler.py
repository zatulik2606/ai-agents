import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from nika.services.chat_history import ChatHistory
from nika.services.llm_client import LlmClient

logger = logging.getLogger(__name__)


class MessageHandler:
    def __init__(self, llm: LlmClient, history: ChatHistory) -> None:
        self._llm = llm
        self._history = history
        self.router = Router()

    def register(self) -> Router:
        self.router.message.register(self.handle_start, CommandStart())
        self.router.message.register(self.handle_reset, Command("reset"))
        self.router.message.register(self.handle_help, Command("help"))
        self.router.message.register(self.handle_example, Command("example"))
        self.router.message.register(self.handle_text, F.text & ~F.text.startswith("/"))
        return self.router

    async def handle_start(self, message: Message) -> None:
        await message.answer(
            "Привет! Я Ника — твоя ассистентка по диабету. "
            "Рада помочь с ХЕ, питанием и вопросами об инсулине. "
            "Просто напиши вопрос."
        )

    async def handle_reset(self, message: Message) -> None:
        if not message.from_user:
            return
        self._history.clear(message.from_user.id)
        await message.answer("История диалога сброшена. Можем начать сначала.")

    async def handle_help(self, message: Message) -> None:
        await message.answer(
            "Я Ника — ассистентка по диабету.\n"
            "Помогаю с ХЕ, питанием и контекстом инсулина.\n"
            "Не назначаю дозы — только справочная информация.\n\n"
            "/reset — сбросить историю диалога\n"
            "/example — примеры вопросов\n"
            "/help — эта справка"
        )

    async def handle_example(self, message: Message) -> None:
        await message.answer(
            "Примеры вопросов:\n\n"
            "• Сколько ХЕ в банане 120 г?\n"
            "• Как посчитать доколку на 2 БЖЕ при коэффициенте 0.5?\n"
            "• Что учесть в питании при овсянке на молоке?"
        )

    async def handle_text(self, message: Message) -> None:
        if not message.from_user:
            return

        user_id = message.from_user.id
        text = message.text or ""
        logger.info("user_id=%s incoming: %s", user_id, text)

        history = self._history.get(user_id)

        try:
            answer = await self._llm.ask(text, history)
        except Exception:
            logger.exception("LLM error for user_id=%s", user_id)
            await message.answer("Не удалось получить ответ. Попробуй позже.")
            return

        logger.info("user_id=%s response_len=%d", user_id, len(answer))
        self._history.add(user_id, "user", text)
        self._history.add(user_id, "assistant", answer)

        await message.answer(answer)
