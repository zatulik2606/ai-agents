from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message


class MessageHandler:
    def __init__(self) -> None:
        self.router = Router()

    def register(self) -> Router:
        self.router.message.register(self.handle_start, CommandStart())
        self.router.message.register(self.handle_text, F.text & ~F.text.startswith("/"))
        return self.router

    async def handle_start(self, message: Message) -> None:
        await message.answer("Привет! Я Ника. Напиши мне сообщение.")

    async def handle_text(self, message: Message) -> None:
        await message.answer(f"Получила: {message.text}")
