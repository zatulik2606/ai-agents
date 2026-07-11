from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from nika.services.llm_client import LlmClient


class MessageHandler:
    def __init__(self, llm: LlmClient) -> None:
        self._llm = llm
        self.router = Router()

    def register(self) -> Router:
        self.router.message.register(self.handle_start, CommandStart())
        self.router.message.register(self.handle_text, F.text & ~F.text.startswith("/"))
        return self.router

    async def handle_start(self, message: Message) -> None:
        await message.answer("Привет! Я Ника. Напиши мне сообщение.")

    async def handle_text(self, message: Message) -> None:
        answer = await self._llm.ask(message.text or "")
        await message.answer(answer)
