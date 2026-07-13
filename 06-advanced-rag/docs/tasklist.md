# План разработки

> Итерационный план Telegram-бота Ника. Каждый шаг — рабочий инкремент, который можно проверить в Telegram.

---

## 📊 Прогресс

### Спринт 1 — мультимодальный ассистент ✅

| # | Итерация | Статус | Проверка |
|---|----------|--------|----------|
| 0 | Скелет проекта | ✅ Готово | `make run` — polling @NikaVita_bot |
| 1 | Telegram: бот онлайн | ✅ Готово | /start и заглушка на текст |
| 2 | Конфигурация | ✅ Готово | Config из .env, без хардкода |
| 3 | LLM-ответы | ✅ Готово | осмысленный ответ от LLM |
| 4 | Системный промпт | ✅ Готово | Ника представляется как Ника |
| 5 | История диалога | ✅ Готово | контекст в многоходовом диалоге |
| 6 | Команды бота | ✅ Готово | /start, /reset, /help, /example |
| 7 | Make + Docker | ✅ Готово | Dockerfile, docker-build, docker-run |
| 8 | Логирование | ✅ Готово | логи + обработка ошибок LLM |
| 9 | Адаптация роли | ✅ Готово | роль диабет-ассистентки, дисклеймер |
| 10 | Модель данных + JSON | ✅ Готово | MealLogStore, data/meals.json, /reset_log |
| 11 | Учёт из текста | ✅ Готово | structured output → JSON → ответ с ХЕ |
| 12 | Расчёт инсулина | ✅ Готово | рекомендация ЕД + время доколки + дисклеймер |
| 13 | Конфиг моделей | ✅ Готово | MODEL_TEXT/IMAGE/AUDIO, гибрид ollama+openrouter |
| 14 | Фото продуктов | ✅ Готово | Gemini VLM → учёт + расчёт инсулина |
| 15 | Транскрипция аудио | ✅ Готово | Whisper → текст → учёт |
| 16 | Отчёты и команды | ✅ Готово | /report_day, /report_week, /coeffs |
| 17 | Транскрибация голосовых | ✅ Готово | Whisper API, language=ru, голос → учёт |

### Спринт 2 — RAG по руководству

| # | Итерация | Статус | Проверка |
|---|----------|--------|----------|
| 18 | LangChain deps + конфиг RAG | ✅ Готово | RAG-параметры в логах при старте |
| 19 | Загрузка PDF + чанкинг | ✅ Готово | PDF 105 стр. → 225 чанков в логах |
| 20 | Indexer + InMemoryVectorStore | ✅ Готово | 225 чанков, retriever → 4 docs |
| 21 | Query transformation | ✅ Готово | follow-up → query с темой из истории |
| 22 | RAG-цепочка | ✅ Готово | ответ по контексту PDF |
| 23 | История LangChain messages | ✅ Готово | HumanMessage/AIMessage в ChatHistory |
| 24 | Команды + интеграция | ✅ Готово | /index, /index_status, справочный вопрос → RAG |

### Спринт 3 — полировка RAG ✅

| # | Итерация | Статус | Проверка |
|---|----------|--------|----------|
| 25 | RAG через OpenRouter при гибриде | ✅ Готово | RAG model=gemini, base_url=openrouter |
| 26 | UX: «Ищу в руководстве…» | ✅ Готово | статус при RAG-запросе |
| 27 | Промпт + классификация | ✅ Готово | инъекции → RAG, еда → учёт |
| 28 | Документация + Docker | ✅ Готово | README, data volume в docker-run |

### Спринт 4 — мониторинг и оценка качества RAG

| # | Итерация | Статус | Проверка |
|---|----------|--------|----------|
| 29 | ДЗ-5: Источники + LangSmith | ✅ Готово | SHOW_SOURCES + трейсы в LangSmith |
| 30 | ДЗ-5: Синтез датасетов | ✅ Готово | make dataset → JSON, make dataset-upload |
| 31 | ДЗ-5: Evaluation через RAGAS | ✅ Готово | /evaluate_dataset → 6 метрик + feedback |
| 32 | ДЗ-5: Документация и полировка | ✅ Готово | README, .env.example, обработка ошибок |

### Спринт 5 — Advanced RAG

| # | Итерация | Статус | Проверка |
|---|----------|--------|----------|
| 33 | ДЗ-6: Зависимости и конфиг | ✅ Готово | rank-bm25, sentence-transformers; RAG_RETRIEVAL_MODE в логах |
| 34 | ДЗ-6: BM25 + hybrid retrieval | ✅ Готово | semantic+BM25 fusion, follow-up query работает |
| 35 | ДЗ-6: Cross-encoder reranker | ✅ Готово | hybrid_rerank → top-K после rerank |
| 36 | ДЗ-6: RAG pipeline (LCEL) | ✅ Готово | три режима через конфиг; query transform сохранён |
| 37 | ДЗ-6: Провайдеры embeddings | ✅ Готово | openai/huggingface для index и RAGAS |
| 38 | ДЗ-6: Документация и интеграция | ✅ Готово | README, .env.example, /help, логирование режима |

**Легенда:** ⬜ Ожидает · 🔄 В работе · ✅ Готово · ⛔ Заблокировано

**Текущая итерация:** — Спринт 5 завершён  
**Завершено:** 38 / 38

---

## Спринт 1 — итерации

### 0. Скелет проекта

- [x] Структура каталогов и точка входа
- [x] Зависимости через uv
- [x] Бот запускается без ошибок

**Проверка:** `make run` (или аналог) — процесс стартует, polling активен.

---

### 1. Telegram: бот онлайн

- [x] Подключение к Telegram Bot API (polling)
- [x] Ответ на `/start`
- [x] Ответ на текстовое сообщение (заглушка)

**Проверка:** написать боту в Telegram — получить ответ-заглушку.

---

### 2. Конфигурация

- [x] Настройки из переменных окружения
- [x] Шаблон `.env.example`

**Проверка:** бот стартует с токеном из `.env`, без хардкода секретов.

---

### 3. LLM-ответы

- [x] Запрос к OpenRouter через openai-клиент
- [x] Ответ модели отправляется пользователю

**Проверка:** задать вопрос боту — получить осмысленный ответ от LLM.

---

### 4. Системный промпт

- [x] Роль ассистента задаётся в system prompt
- [x] Бот отвечает в заданной роли

**Проверка:** убедиться, что тон и поведение соответствуют роли, а не дефолтной модели.

---

### 5. История диалога

- [x] Контекст сохраняется в памяти per user
- [x] Бот учитывает предыдущие сообщения

**Проверка:** задать уточняющий вопрос — бот отвечает с учётом контекста.

---

### 6. Команды бота

- [x] `/start` — приветствие
- [x] `/reset` — сброс истории
- [x] `/help` — краткая справка

**Проверка:** `/reset` очищает контекст; следующий ответ не ссылается на прошлый диалог.

---

### 7. Make + Docker

- [x] Makefile: install, run, docker-build, docker-run
- [x] Dockerfile для локального запуска

**Проверка:** бот работает через `make run` и через `make docker-run`.

---

### 8. Логирование

- [x] Логи старта, входящих сообщений, ответов LLM
- [x] Логирование ошибок без падения бота

**Проверка:** при ошибке LLM пользователь видит понятное сообщение; детали — в логах.

---

### 9. Адаптация роли (системный промпт)

- [x] Обновить `DEFAULT_SYSTEM_PROMPT` под роль диабет-ассистентки
- [x] Согласовать тексты `/start`, `/help`, `/example` с новой ролью
- [x] Проверить тон: женский род, дисклеймер, уточняющие вопросы

**Проверка:** «ты кто?» → Ника представляется как ассистентка по диабету; ответ на вопрос по ХЕ содержит дисклеймер и не назначает дозы инсулина.

---

### 10. Модель данных + JSON

- [x] `MealEntry` (dataclass) — поля по `vision.md` §5
- [x] `MealLogStore` — чтение/запись `DATA_FILE` (дефолт `data/meals.json`)
- [x] Команда `/reset_log` — очистка учёта (отдельно от `/reset`)
- [x] `DATA_FILE` в `Config` и `.env.example`

**Проверка:** append/load/clear через MealLogStore; `/reset_log` очищает файл.

---

### 11. Учёт из текста

- [x] Pydantic-модель `MealExtraction` для structured output
- [x] `LlmClient.extract_meal()` — извлечение данных из текста
- [x] Обработчик: сообщение с данными о еде → запись в `MealLogStore` → ответ Нике
- [x] Уточняющие вопросы, если `needs_clarification`
- [x] Свободные вопросы по-прежнему через `ask()` с историей

**Проверка:** «Съел овсянку 200 г, сахар 6.2, завтрак» → JSON + ХЕ; «ты кто?» → диалог.

---

### 12. Расчёт инсулина

- [x] `InsulinCalculator` — формула из `vision.md` §8
- [x] Коэффициенты в `Config`: `CARB_RATIO`, `INSULIN_SENSITIVITY`, `TARGET_GLUCOSE_MIN`, `TARGET_GLUCOSE_MAX`, `FPU_RATIO`
- [x] Рекомендация в ответе: доза + время доколки
- [x] Дисклеймер в каждом ответе с рекомендацией по инсулину

**Проверка:** 42 г углеводов, сахар 7.0 → «доколоть 4.5 ЕД за 15 мин» + дисклеймер.

---

### 13. Конфиг моделей

- [x] `LLM_MODEL` → `MODEL_TEXT`; добавить `MODEL_IMAGE`, `MODEL_AUDIO`
- [x] `LlmClient` использует `MODEL_TEXT`; подготовить поля для image/audio
- [x] `LLM_PROVIDER` (`openrouter` / `ollama`) переключает `LLM_BASE_URL`
- [x] Обновить `.env.example` с примерами для обоих провайдеров

**Проверка:** `LLM_PROVIDER=ollama` + deepseek-r1 — диалог и учёт работают локально.

---

### 14. Фото продуктов

- [x] `LlmClient.analyze_photo()` — multimodal запрос через `MODEL_IMAGE`
- [x] Обработчик фото в `message_handler`
- [x] Результат → `MealExtraction` → запись в лог → ответ с ХЕ

**Проверка:** отправить фото тарелки с едой → Ника оценивает порцию, записывает в JSON, отвечает с ХЕ.

---

### 15. Транскрипция аудио

- [x] `TranscribeClient` — транскрипция через `MODEL_AUDIO`
- [x] Обработчик голосовых сообщений в `message_handler`
- [x] Транскрипт → `extract_meal()` → тот же поток, что для текста

**Проверка:** надиктовать «съел банан, сахар 5.8» → транскрипт в логах, запись в JSON, ответ Нике.

---

### 16. Отчёты и команды

- [x] `/report_day` — сводка за день (сахара, ХЕ, инсулин)
- [x] `/report_week` — сводка за неделю + анализ доколок
- [x] `/coeffs` — показать текущие коэффициенты
- [x] Обновить `/help` и `/example` под новый функционал

**Проверка:** `/report_day` выдаёт сводку; `/report_week` — сводку + анализ; `/coeffs` — значения из `.env`.

---

### 17. Транскрибация голосовых сообщений

**Подход:** OpenAI Whisper API через OpenRouter (`openai/whisper-1`, `language=ru`).
Подробнее — `idea.md` §Голосовые, `vision.md` §7.

- [x] `TranscribeClient` — async, OpenAI-compatible `audio.transcriptions.create()`
- [x] Конфиг: `MODEL_AUDIO`, `AUDIO_LLM_BASE_URL`, `AUDIO_OPENROUTER_API_KEY`
- [x] `language="ru"` в запросе Whisper
- [x] Обработчик `handle_voice` в `message_handler`: download → transcribe → `_handle_message()`
- [x] Статус «Слушаю голосовое…» + обработка ошибок без падения бота
- [x] Транскрипт в логах; запись еды → JSON + ответ с ХЕ
- [x] Обновить `idea.md` и `vision.md` (подход STT)

**Проверка:** надиктовать «съел банан 120 г, сахар 5.8» → транскрипт в логах,
запись в `data/meals.json`, ответ Нике с ХЕ и рекомендацией.

---

## Спринт 2 — итерации

> RAG дополняет Спринт 1: учёт, фото, голос и отчёты сохраняются.
> Архитектура — `vision.md` §11. Референс — `notebooks/naive-rag.ipynb`.

### 18. LangChain deps + конфиг RAG

- [x] Зависимости: `langchain`, `langchain-openai`, `langchain-community`, `langchain-text-splitters`
- [x] `Config`: `DATA_PDF`, `RETRIEVER_K`, `MODEL_EMBEDDING`
- [x] Маппинг `OPENAI_BASE_URL` → `base_url` LangChain (fallback на `LLM_BASE_URL`)
- [x] Обновить `.env.example`

**Проверка:** `make run` — бот стартует, в логах видны RAG-параметры из конфига.

---

### 19. Загрузка PDF + чанкинг

- [x] PyPDFLoader для `DATA_PDF`
- [x] RecursiveCharacterTextSplitter — разбиение на чанки
- [x] Лог: число страниц и чанков

**Проверка:** скрипт/сервис загружает PDF из `data/` — в логах > 0 чанков.

---

### 20. Indexer + InMemoryVectorStore

- [x] `Indexer` — embed chunks через `MODEL_EMBEDDING`
- [x] Хранение в `InMemoryVectorStore`
- [x] `chunk_count` — getter для статуса

**Проверка:** после `index()` — `chunk_count > 0`, retriever возвращает документы.

---

### 21. Query transformation

- [x] Цепочка переформулировки запроса с учётом истории (по `naive-rag.ipynb`)
- [x] Вход: последние messages + текущий вопрос
- [x] Выход: standalone query для retriever

**Проверка:** «А что насчёт этого?» после вопроса о гипогликемии → query содержит тему из истории.

---

### 22. RAG-цепочка

- [x] `RagService` — `rag_query_transform_chain`: transform → retrieve (top-K) → generate
- [x] `RETRIEVER_K` из конфига
- [x] Ответ на основе контекста + истории + system prompt

**Проверка:** «Что такое гипогликемия?» → ответ по содержанию PDF, не общие знания модели.

---

### 23. История LangChain messages

- [x] `ChatHistory` хранит `list[BaseMessage]` (HumanMessage, AIMessage, SystemMessage)
- [x] RAG и учёт используют одну историю per user
- [x] `/reset` очищает messages

**Проверка:** уточняющий справочный вопрос — RAG учитывает предыдущий обмен.

---

### 24. Команды + интеграция

- [x] `/index` — полная переиндексация
- [x] `/index_status` — число чанков
- [x] Переиндексация в `main.py` при старте
- [x] Маршрутизация: учёт → extract_meal; справочный вопрос → `RagService`
- [x] Обновить `/help`

**Проверка:** `/index_status` показывает N чанков; «Съел банан…» → учёт;
«Что такое инсулиновая терапия?» → RAG-ответ из руководства.

---

## Спринт 3 — итерации

### 25. RAG через OpenRouter при гибриде

- [x] `RagService` — `openai_base_url` + `openai_api_key` (не Ollama)
- [x] `MODEL_RAG` в Config; в гибриде дефолт — `MODEL_IMAGE`
- [x] Лог `RAG config: model=…` при старте
- [x] Обновить `.env.example`

**Проверка:** при `LLM_PROVIDER=ollama` + `OPENAI_BASE_URL=openrouter` в логах
`model=google/gemini-2.5-flash`; RAG-ответ быстрее deepseek-r1.

---

### 26. UX: «Ищу в руководстве…»

- [x] Статус-сообщение перед RAG-запросом
- [x] Удаление статуса после ответа

**Проверка:** справочный вопрос → «Ищу в руководстве…» → ответ.

---

### 27. Промпт + классификация

- [x] Уточнить `EXTRACTION_SYSTEM_PROMPT` для граничных случаев
- [x] Примеры: инъекции/терапия → RAG; «съел» → учёт
- [x] `_resolve_routing()` в `MealExtraction.sanitize()`

**Проверка:** «Сколько инъекций в день» → RAG; «съел банан» → учёт.

---

### 28. Документация + Docker

- [x] README с запуском и RAG-переменными
- [x] Volume `./data` в `make docker-run`
- [x] `mkdir -p data` в Dockerfile
- [x] Проверка `make docker-build`

**Проверка:** README актуален; `make docker-build` проходит; `make docker-run` с PDF в `data/`.

---

## Спринт 4 — итерации

> Мониторинг и оценка качества RAG. Архитектура — `vision.md` §14.
> Референс — `rag-evaluation-practice.ipynb`.

### 29. ДЗ-5: Источники + LangSmith

- [x] Рефакторинг `RagService`: возврат `answer` + `documents`
- [x] `SHOW_SOURCES` в `Config`; форматирование «📚 Источники: …»
- [x] Handler: показ источников при `SHOW_SOURCES=true`
- [x] `langsmith` в зависимостях; `LANGSMITH_*` в `.env.example`

**Проверка:** `SHOW_SOURCES=true` → источники в ответе; RAG-запросы видны в LangSmith UI.

---

### 30. ДЗ-5: Синтез датасетов

- [x] `dataset_synthesizer.py`: 2 чанка/PDF, LLM Q&A, загрузка JSON Q&A из `data/`
- [x] Сохранение в `datasets/05-rag-qa-dataset.json`
- [x] Загрузка в LangSmith с проверкой дубликатов
- [x] `make dataset`, `make dataset-upload` в Makefile

**Проверка:** `make dataset` создаёт JSON; `make dataset-upload` загружает без дубликатов.

---

### 31. ДЗ-5: Evaluation через RAGAS

- [x] `evaluation.py`: 6 метрик RAGAS, feedback в LangSmith
- [x] `RAGAS_LLM_MODEL`, `RAGAS_EMBEDDING_MODEL` в конфиге
- [x] Команда `/evaluate_dataset` в handler
- [x] Зависимости: `ragas>=0.2.0`, `datasets`

**Проверка:** `/evaluate_dataset` → 6 метрик в Telegram; feedback в LangSmith Experiments.

---

### 32. ДЗ-5: Документация и полировка

- [x] README: источники, LangSmith, dataset, evaluation, RAGAS-метрики
- [x] Обработка ошибок (нет API-ключа, нет датасета, rate limits)
- [x] Обновить `/help`
- [x] Скопировать `data/` из референса (PDF + JSON Q&A)

**Проверка:** полный цикл: dataset → upload → evaluate; README актуален.

---

## Спринт 5 — итерации

> Advanced RAG: hybrid retrieval + cross-encoder reranker.
> Архитектура — `vision.md` §11. Референс — `docs/references/advanced-hybrid-rag.ipynb`.

### 33. ДЗ-6: Зависимости и конфиг

- [x] Зависимости: `rank-bm25`, `sentence-transformers`
- [x] `Config`: `RAG_RETRIEVAL_MODE`, `SEMANTIC_RETRIEVER_K`, `BM25_RETRIEVER_K`, `HYBRID_RETRIEVER_K`, `RERANKER_FETCH_K`, `RERANKER_K`, `MODEL_CROSSENCODER`
- [x] `EMBEDDING_PROVIDER` (`openai` | `huggingface`), `RAGAS_EMBEDDING_PROVIDER`
- [x] Обратная совместимость: `RETRIEVER_K` → `SEMANTIC_RETRIEVER_K`
- [x] Обновить `.env.example`

**Проверка:** `make run` — в логах видны режим retrieval и параметры K.

---

### 34. ДЗ-6: BM25 + hybrid retrieval

- [x] `Indexer`: хранение чанков в памяти, `as_semantic_retriever()`, `as_bm25_retriever()`
- [x] `HybridRetriever`: semantic + BM25 → RRF fusion → top `HYBRID_RETRIEVER_K`
- [x] Референс — `advanced-hybrid-rag.ipynb` Part 1

**Проверка:** `RAG_RETRIEVAL_MODE=hybrid` — справочный вопрос с ключевым словом
(«инъекции») находит релевантный фрагмент; follow-up после вопроса о гипогликемии работает.

---

### 35. ДЗ-6: Cross-encoder reranker

- [x] `Reranker`: `CrossEncoder(MODEL_CROSSENCODER)`, `RERANKER_FETCH_K` → `RERANKER_K`
- [x] Референс — `advanced-hybrid-rag.ipynb` Part 2

**Проверка:** `RAG_RETRIEVAL_MODE=hybrid_rerank` — в логах видно fetch/rerank;
ответ точнее на вопрос с несколькими похожими чанками.

---

### 36. ДЗ-6: RAG pipeline (LCEL)

- [x] `RagService`: выбор retriever по `RAG_RETRIEVAL_MODE` при инициализации
- [x] LCEL-цепочка: query transform → retrieve → generate (как `rag_query_transform_chain`)
- [x] Query transformation с историей **сохранён** — выполняется до retrieval
- [x] `evaluation.py` использует тот же режим retrieval

**Проверка:** переключение `semantic` / `hybrid` / `hybrid_rerank` меняет поведение
без изменения кода; «А что насчёт этого?» после справочного вопроса → корректный follow-up.

---

### 37. ДЗ-6: Провайдеры embeddings

- [x] `create_embeddings()`: `openai` (OpenAIEmbeddings через OpenRouter) | `huggingface` (HuggingFaceEmbeddings)
- [x] RAGAS evaluation: `RAGAS_EMBEDDING_PROVIDER` + `RAGAS_EMBEDDING_MODEL`
- [x] Лог провайдера и модели при индексации

**Проверка:** `EMBEDDING_PROVIDER=huggingface` + локальная модель — индексация и RAG работают;
`/evaluate_dataset` с `RAGAS_EMBEDDING_PROVIDER=huggingface` — метрики считаются.

---

### 38. ДЗ-6: Документация и интеграция

- [x] README: режимы retrieval, env-переменные, примеры конфигов
- [x] Обновить `/help` — режим RAG, команды индексации
- [x] Логирование активного режима при старте
- [x] Скопировать `docs/references/advanced-hybrid-rag.ipynb` (если ещё нет)

**Проверка:** README актуален; полный цикл semantic → hybrid → hybrid_rerank через смену `.env`.
