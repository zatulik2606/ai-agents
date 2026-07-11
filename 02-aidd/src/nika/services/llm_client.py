from openai import AsyncOpenAI

from nika.config import Config


class LlmClient:
    def __init__(self, config: Config) -> None:
        self._client = AsyncOpenAI(
            base_url=config.llm_base_url,
            api_key=config.openrouter_api_key,
        )
        self._model = config.llm_model
        self._system_prompt = config.system_prompt

    async def ask(self, text: str) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": text},
            ],
        )
        content = response.choices[0].message.content
        return content or ""
