from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from nika.services.chat_history import ChatHistory
from nika.services.llm_client import LlmClient


class MessageHandler:
    def __init__(self, llm: LlmClient, history: ChatHistory) -> None:
        self._llm = llm
        self._history = history
        self.router = Router()

    def register(self) -> Router:
        self.router.message.register(self.handle_start, CommandStart())
        self.router.message.register(self.handle_text, F.text & ~F.text.startswith("/"))
        return self.router

    async def handle_start(self, message: Message) -> None:
        await message.answer("Привет! Я Ника. Напиши мне сообщение.")

    async def handle_text(self, message: Message) -> None:
        if not message.from_user:
            return

        user_id = message.from_user.id
        text = message.text or ""
        history = self._history.get(user_id)

        answer = await self._llm.ask(text, history)
        self._history.add(user_id, "user", text)
        self._history.add(user_id, "assistant", answer)

        await message.answer(answer)
