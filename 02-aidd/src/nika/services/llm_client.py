from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from nika.config import Config
from nika.services.chat_history import ChatMessage


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
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
        )
        content = response.choices[0].message.content
        return content or ""
