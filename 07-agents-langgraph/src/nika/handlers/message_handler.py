import logging
from dataclasses import dataclass

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from langchain_core.documents import Document

from nika.config import Config
from nika.services.agent_service import AgentService
from nika.services.chat_history import ChatHistory
from nika.services.chitchat import is_chitchat, is_reference_question
from nika.services.evaluation import EvaluationService, evaluation_error_message
from nika.services.indexer import Indexer
from nika.services.insulin_calculator import InsulinCalculator
from nika.services.llm_client import LlmClient
from nika.services.meal_log import MealExtraction, MealLogStore
from nika.services.meal_report import MealReport
from nika.services.rag_service import format_sources
from nika.services.transcribe_client import TranscribeClient

RAG_STATUS_TEXT = "Ищу в руководстве…"
AGENT_STATUS_TEXT = "Думаю…"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HandlerReply:
    text: str
    history_text: str


class MessageHandler:
    def __init__(
        self,
        config: Config,
        llm: LlmClient,
        history: ChatHistory,
        meal_log: MealLogStore,
        insulin: InsulinCalculator,
        transcribe: TranscribeClient,
        agent: AgentService,
        indexer: Indexer,
    ) -> None:
        self._config = config
        self._llm = llm
        self._history = history
        self._meal_log = meal_log
        self._insulin = insulin
        self._transcribe = transcribe
        self._agent = agent
        self._indexer = indexer
        self._evaluation = EvaluationService(config, agent)
        self._report = MealReport(meal_log, llm)
        self.router = Router()

    def register(self) -> Router:
        self.router.message.register(self.handle_start, CommandStart())
        self.router.message.register(self.handle_reset, Command("reset"))
        self.router.message.register(self.handle_reset_log, Command("reset_log"))
        self.router.message.register(self.handle_help, Command("help"))
        self.router.message.register(self.handle_example, Command("example"))
        self.router.message.register(self.handle_coeffs, Command("coeffs"))
        self.router.message.register(self.handle_report_day, Command("report_day"))
        self.router.message.register(self.handle_report_week, Command("report_week"))
        self.router.message.register(self.handle_index, Command("index"))
        self.router.message.register(self.handle_index_status, Command("index_status"))
        self.router.message.register(
            self.handle_evaluate_dataset,
            Command("evaluate_dataset"),
        )
        self.router.message.register(self.handle_text, F.text & ~F.text.startswith("/"))
        self.router.message.register(self.handle_photo, F.photo)
        self.router.message.register(self.handle_voice, F.voice)
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
        self._agent.reset_thread(message.from_user.id)
        await message.answer("История диалога сброшена. Можем начать сначала.")

    async def handle_reset_log(self, message: Message) -> None:
        self._meal_log.clear()
        await message.answer("Учёт приёмов пищи очищен.")

    async def handle_help(self, message: Message) -> None:
        sources_hint = (
            "Источники в ответах: SHOW_SOURCES=true в .env\n"
            if not self._config.show_sources
            else "Источники в RAG-ответах: включены\n"
        )
        rag_mode = self._config.rag_retrieval_mode
        await message.answer(
            "Я Ника — ассистентка по диабету.\n"
            "Помогаю с ХЕ, питанием и контекстом инсулина.\n"
            "Принимаю текст, фото и голосовые сообщения.\n"
            "Не назначаю дозы — только справочная информация.\n\n"
            "Учёт и отчёты:\n"
            "/report_day — сводка за день\n"
            "/report_week — сводка за неделю\n"
            "/coeffs — коэффициенты расчёта\n"
            "/reset_log — очистить учёт\n\n"
            "Справочник (агент + tools):\n"
            f"Режим retrieval: {rag_mode}\n"
            "(semantic | hybrid | hybrid_rerank в .env)\n"
            "Tools: rag_search, glucose_unit_converter\n"
            "/index — переиндексировать документы\n"
            "/index_status — статус индекса\n"
            f"{sources_hint}"
            "/evaluate_dataset — оценка качества (RAGAS)\n"
            "  нужны LANGSMITH_API_KEY и датасет в LangSmith\n\n"
            "/reset — сбросить историю диалога\n"
            "/example — примеры\n"
            "/help — эта справка"
        )

    async def handle_coeffs(self, message: Message) -> None:
        await message.answer(
            "Текущие коэффициенты:\n"
            f"• Углеводный (CARB_RATIO): {self._config.carb_ratio:g} г/ЕД\n"
            f"• Чувствительность (INSULIN_SENSITIVITY): "
            f"{self._config.insulin_sensitivity:g} ммоль/л на 1 ЕД\n"
            f"• Целевой сахар мин (TARGET_GLUCOSE_MIN): "
            f"{self._config.target_glucose_min:g} ммоль/л\n"
            f"• Целевой сахар макс (TARGET_GLUCOSE_MAX): "
            f"{self._config.target_glucose_max:g} ммоль/л\n"
            f"• БЖЕ (FPU_RATIO): {self._config.fpu_ratio:g} г/БЖЕ"
        )

    async def handle_report_day(self, message: Message) -> None:
        try:
            answer = self._report.day_report()
        except Exception:
            logger.exception("Report day error")
            await message.answer("Не удалось сформировать отчёт. Попробуй позже.")
            return

        await message.answer(answer)

    async def handle_report_week(self, message: Message) -> None:
        status = await message.answer("Формирую отчёт за неделю…")
        try:
            answer = await self._report.week_report()
        except Exception:
            logger.exception("Report week error")
            await status.edit_text("Не удалось сформировать отчёт. Попробуй позже.")
            return

        await status.delete()
        await message.answer(answer)

    async def handle_example(self, message: Message) -> None:
        await message.answer(
            "Примеры:\n\n"
            "• Съел овсянку 200 г, сахар 6.2, завтрак\n"
            "• Фото тарелки с едой\n"
            "• Голосом: съел банан, сахар 5.8\n"
            "• /report_day — сводка за день\n"
            "• /coeffs — мои коэффициенты\n"
            "• Что такое гипогликемия? — справочный вопрос (агент + rag_search)"
        )

    async def handle_index(self, message: Message) -> None:
        status = await message.answer("Индексирую руководство…")
        try:
            count = await self._indexer.aindex()
        except FileNotFoundError:
            await status.edit_text("PDF не найден. Проверь DATA_PDF в .env.")
            return
        except Exception:
            logger.exception("Index error")
            await status.edit_text("Не удалось проиндексировать. Попробуй позже.")
            return
        await status.edit_text(f"Готово. Проиндексировано {count} чанков.")

    async def handle_index_status(self, message: Message) -> None:
        count = self._indexer.chunk_count
        if count == 0:
            await message.answer("Индекс пуст. Запусти /index или перезапусти бота.")
            return
        await message.answer(f"Проиндексировано {count} чанков.")

    async def handle_evaluate_dataset(self, message: Message) -> None:
        if not self._config.langsmith_api_key:
            await message.answer(
                "LangSmith API key не настроен.\n"
                "Установи LANGSMITH_API_KEY в .env для evaluation."
            )
            return

        if not self._config.openrouter_api_key:
            await message.answer(
                "OpenRouter API key не настроен.\n"
                "RAGAS evaluation требует OPENROUTER_API_KEY в .env."
            )
            return

        if self._indexer.chunk_count == 0:
            await message.answer(
                "Индекс пуст. Запусти /index или перезапусти бота."
            )
            return

        command_parts = (message.text or "").split(maxsplit=1)
        dataset_name = command_parts[1] if len(command_parts) > 1 else None
        resolved_name = dataset_name or self._config.langsmith_dataset

        status = await message.answer(
            f"Запускаю evaluation датасета: {resolved_name}\n"
            "Это может занять несколько минут…"
        )

        try:
            result = await self._evaluation.evaluate_dataset(dataset_name)
        except ValueError as error:
            logger.error("Evaluation validation error: %s", error)
            await status.edit_text(evaluation_error_message(error))
            return
        except Exception as error:
            logger.exception("Evaluation error")
            await status.edit_text(evaluation_error_message(error))
            return

        await status.edit_text(self._evaluation.format_report(result))

    async def handle_text(self, message: Message) -> None:
        if not message.from_user:
            return

        user_id = message.from_user.id
        text = message.text or ""
        logger.info("user_id=%s incoming: %s", user_id, text)

        try:
            reply = await self._handle_message(text, message)
        except Exception:
            logger.exception("LLM error for user_id=%s", user_id)
            await message.answer("Не удалось получить ответ. Попробуй позже.")
            return

        logger.info("user_id=%s response_len=%d", user_id, len(reply.text))
        self._history.add_user(user_id, text)
        self._history.add_assistant(user_id, reply.history_text)

        await message.answer(reply.text)

    async def handle_photo(self, message: Message) -> None:
        if not message.from_user or not message.photo or message.bot is None:
            return

        user_id = message.from_user.id
        caption = message.caption or ""
        logger.info("user_id=%s incoming photo caption=%s", user_id, caption)
        await message.answer("Смотрю фото, подожди немного...")

        photo = message.photo[-1]
        file = await message.bot.get_file(photo.file_id)
        if file.file_path is None:
            await message.answer("Не удалось скачать фото. Попробуй ещё раз.")
            return

        downloaded = await message.bot.download_file(file.file_path)
        if downloaded is None:
            await message.answer("Не удалось скачать фото. Попробуй ещё раз.")
            return

        image_bytes = downloaded.read()

        try:
            extraction = (
                await self._llm.analyze_photo(image_bytes, caption)
            ).sanitize()
            answer = self._process_photo_extraction(extraction)
        except Exception:
            logger.exception("LLM photo error for user_id=%s", user_id)
            await message.answer("Не удалось разобрать фото. Попробуй позже.")
            return

        user_text = f"[фото]{f' {caption}' if caption else ''}"
        logger.info("user_id=%s response_len=%d", user_id, len(answer))
        self._history.add_user(user_id, user_text)
        self._history.add_assistant(user_id, answer)

        await message.answer(answer)

    async def handle_voice(self, message: Message) -> None:
        if not message.from_user or not message.voice or message.bot is None:
            return

        user_id = message.from_user.id
        logger.info("user_id=%s incoming voice", user_id)
        await message.answer("Слушаю голосовое, подожди немного...")

        file = await message.bot.get_file(message.voice.file_id)
        if file.file_path is None:
            await message.answer("Не удалось скачать аудио. Попробуй ещё раз.")
            return

        downloaded = await message.bot.download_file(file.file_path)
        if downloaded is None:
            await message.answer("Не удалось скачать аудио. Попробуй ещё раз.")
            return

        try:
            transcript = await self._transcribe.transcribe(downloaded.read())
            reply = await self._handle_message(transcript, message)
        except Exception:
            logger.exception("Voice error for user_id=%s", user_id)
            await message.answer("Не удалось распознать голос. Попробуй ещё раз.")
            return

        user_text = f"[голос] {transcript}"
        logger.info("user_id=%s response_len=%d", user_id, len(reply.text))
        self._history.add_user(user_id, user_text)
        self._history.add_assistant(user_id, reply.history_text)

        await message.answer(reply.text)

    async def _handle_message(
        self,
        text: str,
        message: Message | None = None,
    ) -> HandlerReply:
        extraction = (await self._llm.extract_meal(text)).sanitize()
        if extraction.should_log:
            answer = self._process_extraction(extraction)
            return HandlerReply(text=answer, history_text=answer)

        require_search = (
            extraction.is_reference_question or is_reference_question(text)
        )
        status = None
        if message is not None and not is_chitchat(text):
            status_text = (
                RAG_STATUS_TEXT if require_search else AGENT_STATUS_TEXT
            )
            status = await message.answer(status_text)
        try:
            user_id = message.from_user.id if message and message.from_user else 0
            result = await self._agent.answer(
                user_id,
                text,
                require_search=require_search,
            )
            return HandlerReply(
                text=self._format_agent_response(result.answer, result.documents),
                history_text=result.answer,
            )
        finally:
            if status is not None:
                await status.delete()

    def _format_agent_response(
        self,
        answer: str,
        documents: list[Document],
    ) -> str:
        response = answer
        if self._config.show_sources and documents:
            sources = format_sources(documents)
            if sources:
                response = f"{response}\n\n{sources}"
        return response

    def _process_photo_extraction(self, extraction: MealExtraction) -> str:
        if not extraction.should_log:
            return (
                "На фото не вижу еду. Пришли фото блюда или опиши приём пищи текстом."
            )

        if extraction.needs_clarification:
            return extraction.build_clarification_reply()

        if extraction.carbs_g is None and extraction.bread_units is None:
            return extraction.build_clarification_reply()

        return self._process_extraction(extraction)

    def _process_extraction(self, extraction: MealExtraction) -> str:
        if extraction.needs_clarification:
            return extraction.build_clarification_reply()

        self._meal_log.append(extraction.to_meal_entry())
        return self._build_log_reply(extraction)

    def _build_log_reply(self, extraction: MealExtraction) -> str:
        base = extraction.build_reply()
        recommendation = self._insulin.recommend(
            carbs_g=extraction.carbs_g,
            bread_units=extraction.bread_units,
            proteins_g=extraction.proteins_g,
            fats_g=extraction.fats_g,
            sugar_before=extraction.sugar_before,
            bolus_minutes_before=extraction.bolus_minutes_before,
        )
        if recommendation is None:
            note = extraction.insulin_note()
            if note:
                return f"{base}\n\n{note}"
            return base
        return f"{base}\n\n{recommendation.format_message()}"
