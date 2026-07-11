import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

DEFAULT_SYSTEM_PROMPT = (
    "Ты — Ника, дружелюбный Telegram-ассистент. "
    "Отвечай на русском языке, кратко и по делу. "
    "Ты не Google, не Gemini и не ChatGPT — ты Ника."
)


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    openrouter_api_key: str
    llm_provider: str
    llm_base_url: str
    llm_model: str
    system_prompt: str

    @classmethod
    def from_env(cls) -> "Config":
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set")

        return cls(
            telegram_bot_token=token,
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
            llm_provider=os.getenv("LLM_PROVIDER", "openrouter"),
            llm_base_url=os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1"),
            llm_model=os.getenv("LLM_MODEL", "openai/gpt-4o-mini"),
            system_prompt=os.getenv("SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT),
        )
