import io
import logging

from openai import AsyncOpenAI

from nika.config import Config

logger = logging.getLogger(__name__)


class TranscribeClient:
    def __init__(self, config: Config) -> None:
        self._client = AsyncOpenAI(
            base_url=config.audio_base_url,
            api_key=config.audio_api_key,
        )
        self._model = config.model_audio

    async def transcribe(self, audio_bytes: bytes, filename: str = "voice.ogg") -> str:
        buffer = io.BytesIO(audio_bytes)
        buffer.name = filename
        logger.info("STT transcribe: model=%s file=%s", self._model, filename)
        response = await self._client.audio.transcriptions.create(
            model=self._model,
            file=buffer,
            language="ru",
        )
        text = response.text.strip()
        if not text:
            raise ValueError("STT returned empty transcript")
        logger.info("STT transcript: %s", text)
        return text
