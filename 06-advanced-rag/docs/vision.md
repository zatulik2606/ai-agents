# Техническое видение проекта

> **Ника** — Telegram-бот, дружелюбная ассистентка для человека с диабетом.
> Ведёт учёт питания и инсулина, оценивает ХЕ, рассчитывает доколку,
> обрабатывает текст, фото блюд и аудио, отвечает на справочные вопросы через RAG
> по PDF-руководству. Роль задаётся системным промптом.
> RAG дополнен мониторингом (LangSmith, отображение источников), синтезом Q&A-датасетов,
> автоматической оценкой качества через RAGAS и **Advanced RAG**: hybrid retrieval
> (semantic + BM25), cross-encoder reranker, три режима через конфиг.

---

## 1. Технологии

### Язык и рантайм

- **Python 3.12**

### Управление зависимостями

- **uv** — единственный инструмент для управления проектом:
  - `pyproject.toml` — декларация зависимостей и метаданных
  - `uv.lock` — фиксация версий
  - создание и активация venv
  - установка пакетов (`uv sync`, `uv add`)

### Основные зависимости

| Пакет | Назначение |
|-------|------------|
| `aiogram` 3.x | Telegram Bot API, метод polling |
| `openai` | Клиент для LLM / VLM / STT (совместимый API) |
| `python-dotenv` | Загрузка переменных окружения из `.env` |
| `pydantic` | Structured output от LLM, валидация записей |
| `langchain` | RAG-цепочки, messages, retriever |
| `langchain-openai` | ChatOpenAI, OpenAIEmbeddings (OpenRouter-compatible) |
| `langchain-community` | PyPDFLoader, BM25Retriever |
| `langchain-text-splitters` | RecursiveCharacterTextSplitter |
| `langsmith` | Трейсинг RAG-запросов, датасеты, feedback |
| `ragas` ≥0.2.0 | Метрики качества RAG |
| `datasets` | Зависимость RAGAS для batch evaluation |
| `rank-bm25` | BM25-индекс для keyword retrieval |
| `sentence-transformers` | Cross-encoder reranker (локально) |

### Инструменты качества кода

| Инструмент | Назначение |
|------------|------------|
| `ruff` | Линтинг и форматирование |
| `mypy` | Статическая проверка типов |

### Модели (текст, изображение, аудио)

Один `openai` SDK, три роли — каждая со своей моделью в `.env`:

| Роль | Переменная | Назначение |
|------|------------|------------|
| Текст + structured output | `MODEL_TEXT` | Извлечение данных, диалог, отчёты |
| Vision | `MODEL_IMAGE` | Оценка блюда/порции по фото |
| Транскрипция | `MODEL_AUDIO` | Speech-to-text (Whisper и аналоги) |
| Эмбеддинги | `MODEL_EMBEDDING` | Векторизация чанков для semantic retrieval |
| Cross-encoder | `MODEL_CROSSENCODER` | Reranker в режиме `hybrid_rerank` |

Модели могут совпадать (например, одна multimodal на всё), но в конфиге задаются отдельно.

### RAG (LangChain + OpenRouter)

Референсы пайплайна:
- query transformation + базовая цепочка — `notebooks/naive-rag.ipynb`, `rag_query_transform_chain`
- hybrid retrieval и reranker — `docs/references/advanced-hybrid-rag.ipynb` (Part 1, Part 2)

| Компонент | Решение |
|-----------|---------|
| Vector store | `InMemoryVectorStore` (in-memory, без персистентности) |
| BM25 index | `BM25Retriever` + `rank-bm25`, in-memory по тем же чанкам |
| Источник | PDF в `DATA_PDF` + JSON в `data/` |
| Режим retrieval | `RAG_RETRIEVAL_MODE`: `semantic` \| `hybrid` \| `hybrid_rerank` |
| Semantic top-K | `SEMANTIC_RETRIEVER_K` |
| BM25 top-K | `BM25_RETRIEVER_K` |
| Hybrid top-K | `HYBRID_RETRIEVER_K` (после fusion) |
| Reranker | cross-encoder: `RERANKER_FETCH_K` кандидатов → `RERANKER_K` в контекст |
| Query transform | LLM переформулирует запрос с учётом истории **до** retrieval |
| Провайдер LLM/RAG | OpenRouter: `OPENAI_BASE_URL=https://openrouter.ai/api/v1` |

**Режимы retrieval:**

| Режим | Что происходит |
|-------|----------------|
| `semantic` | только vector search, top `SEMANTIC_RETRIEVER_K` |
| `hybrid` | semantic + BM25 → fusion (RRF) → top `HYBRID_RETRIEVER_K` |
| `hybrid_rerank` | hybrid → cross-encoder → top `RERANKER_K` |

**Провайдер embeddings** (`EMBEDDING_PROVIDER`):

| Провайдер | Реализация | Когда |
|-----------|------------|-------|
| `openai` | `OpenAIEmbeddings` через OpenRouter | Облако, совместимость с API |
| `huggingface` | `HuggingFaceEmbeddings` | Локальные модели, без API |

Аналогично для RAGAS: `RAGAS_EMBEDDING_PROVIDER` (`openai` \| `huggingface`) + `RAGAS_EMBEDDING_MODEL`.

`Config` **маппит** `OPENAI_BASE_URL` из `.env` на `base_url` LangChain-клиентов;
если переменная не задана — fallback на `LLM_BASE_URL`. Ключ — `OPENROUTER_API_KEY`.

Провайдер переключается через `LLM_PROVIDER`:

| Провайдер | `LLM_BASE_URL` | Когда |
|-----------|----------------|-------|
| `openrouter` | `https://openrouter.ai/api/v1` | Разработка, облако |
| `ollama` | `http://localhost:11434/v1` | Продакшен, медданные локально |

**Гибридный режим:** текст локально (Ollama), фото и structured extraction — в облаке:

| Переменная | Назначение |
|------------|------------|
| `IMAGE_LLM_BASE_URL` | URL для vision и structured output |
| `IMAGE_OPENROUTER_API_KEY` | API-ключ для image |
| `AUDIO_LLM_BASE_URL` | URL для STT |
| `AUDIO_OPENROUTER_API_KEY` | API-ключ для audio |

Если `IMAGE_LLM_BASE_URL` ≠ `LLM_BASE_URL`, structured extraction и анализ отчётов идут через `MODEL_IMAGE`.

### Сборка и запуск

| Инструмент | Назначение |
|------------|------------|
| `Makefile` | Единая точка входа: install, run, docker-build, docker-run |
| `Docker` | Локальный запуск в контейнере (один `Dockerfile`) |

### Что намеренно не используем

- FastAPI / веб-фреймворки
- База данных, Redis, очереди
- ORM
- CI/CD

---

## 2. Принципы разработки

### KISS

- Минимум абстракций — только то, что нужно для работы бота
- Без паттернов «на будущее» (Repository, Factory, DI-контейнеры)
- Код читается сверху вниз без прыжков по десятку файлов

### ООП: 1 класс = 1 файл

- Каждый класс — отдельный файл с тем же именем: `llm_client.py` → `class LlmClient`
- Исключение: `dataclass` / `TypedDict` / Pydantic-модели — в том же файле, где используются

### Слои (минимум)

| Слой | Назначение |
|------|------------|
| `handlers/` | Реакция на события Telegram (текст, фото, голос, команды) |
| `services/` | Бизнес-логика (LLM, учёт, расчёт инсулина, транскрипция) |
| `config.py` | Настройки и системный промпт |
| `main.py` | Точка входа, запуск polling |

### Async

- Весь код асинхронный: `aiogram` + `openai` async client

### История диалога

- In-memory per user: `list[BaseMessage]` — `SystemMessage`, `HumanMessage`, `AIMessage` (LangChain)
- Сброс: команда `/reset` или перезапуск бота
- Одна история для учёта, RAG и свободного диалога

### Типизация

- Аннотации типов везде
- `mypy` в strict-режиме (или близко к нему)

### Именование

- `snake_case` — файлы, функции, переменные
- `PascalCase` — классы

---

## 3. Структура проекта

```
06-advanced-rag/
├── src/nika/
│   ├── main.py
│   ├── config.py              # Config + DEFAULT_SYSTEM_PROMPT
│   ├── handlers/
│   │   └── message_handler.py # текст, фото, голос, команды
│   └── services/
│       ├── chat_history.py    # LangChain messages per user
│       ├── llm_client.py      # ask + extract_meal + analyze_photo
│       ├── transcribe_client.py
│       ├── meal_log.py        # MealLogStore + MealEntry
│       ├── meal_report.py     # сводки за день / неделю
│       ├── insulin_calculator.py
│       ├── indexer.py         # PDF/JSON → chunks → vector store + BM25
│       ├── hybrid_retriever.py # semantic + BM25 fusion (режим hybrid)
│       ├── reranker.py        # cross-encoder reranker
│       ├── rag_service.py     # LCEL: query transform → retrieve → answer
│       ├── dataset_synthesizer.py  # синтез Q&A из чанков
│       └── evaluation.py      # RAGAS evaluation → LangSmith feedback
├── data/
│   ├── meals.json             # учёт (создаётся автоматически)
│   └── *.pdf, *.json          # документы для RAG и готовые Q&A
├── datasets/
│   └── 05-rag-qa-dataset.json # синтезированный датасет
├── docs/
│   ├── idea.md
│   ├── vision.md
│   ├── tasklist.md
│   ├── prompting.md
│   └── references/
│       └── advanced-hybrid-rag.ipynb  # референс hybrid + reranker
├── pyproject.toml
├── Makefile                   # dataset, dataset-upload
└── Dockerfile
```

---

## 4. Роль и системный промпт

Ника — ассистентка для человека с диабетом. Роль задаётся в `DEFAULT_SYSTEM_PROMPT` (`config.py`), переопределяется через `SYSTEM_PROMPT` в `.env`.

### Поведение

- Женский род, первое лицо: «рада», «поняла», «подскажу», «готова помочь»
- Представляется по имени «Ника», когда уместно
- Помогает с ХЕ, питанием, учётом, расчётом доколки на БЖЕ

### Правила безопасности

- Спокойный, поддерживающий тон
- Не назначает дозы инсулина — только рекомендации, решение за пользователем
- Дисклеймер в каждом ответе по медицинской тематике:
  «Информация справочная и не заменяет консультацию специалиста»
- Уточняющие вопросы при нехватке данных

---

## 5. Модель данных

### Таблица учёта — `MealEntry`

Один пользователь. Запись приёма пищи / сахара / инсулина:

| Поле | Тип | Пример |
|------|-----|--------|
| `datetime` | ISO datetime | `2026-07-12T08:30` |
| `product` | str | «Овсянка на молоке» |
| `quantity` | str | «200 г» |
| `proteins_g` | float \| null | 8.0 |
| `fats_g` | float \| null | 5.0 |
| `carbs_g` | float \| null | 42.0 |
| `bread_units` | float \| null | 3.5 |
| `sugar_before` | float \| null | 6.2 |
| `sugar_after` | float \| null | 5.8 |
| `insulin_dose` | float \| null | 3.0 |
| `bolus_minutes_before` | int \| null | 15 |
| `meal_type` | str \| null | breakfast / lunch / dinner / snack |
| `notes` | str | состав, способ приготовления, самочувствие |

### Хранение — `MealLogStore`

- JSON-файл на диске: `DATA_FILE` (дефолт `data/meals.json`)
- Операции: append, чтение за период (день / неделя)
- Сброс учёта: команда `/reset_log` (отдельно от `/reset` истории диалога)

### In-memory

| Данные | Где | Жизненный цикл |
|--------|-----|----------------|
| История диалога per user | `ChatHistory` | до `/reset` или перезапуска |
| Векторный индекс | `Indexer` → `InMemoryVectorStore` | до перезапуска; обновляется `/index` и при старте |
| BM25-индекс | `Indexer` → `BM25Retriever` | те же чанки, тот же жизненный цикл |
| Настройки | `Config` из `.env` | при старте |

---

## 6. Работа с LLM

### Маршрутизация текстовых сообщений

```
текст (или транскрипт голоса)
    → extract_meal() — классификация
        → запись о еде → MealLogStore → InsulinCalculator → ответ
        → справочный вопрос → RagService.answer() → ответ по PDF
```

Фото — только учёт (VLM), без RAG.

### Диалог (fallback)

- `LlmClient.ask()` — резерв для случаев вне учёта и RAG (если понадобится)
- Модель: `MODEL_TEXT`

### Structured output — извлечение записи

`LlmClient.extract_meal(text)`:

- Вход: текст сообщения (или транскрипт аудио)
- Выход: Pydantic-модель `MealExtraction` — поля `MealEntry` + `reply_text` + `needs_clarification`
- API: `response_format` / JSON schema
- Модель: `MODEL_TEXT` (или `MODEL_IMAGE` в гибридном режиме)

**Поток записи приёма пищи:**

```
сообщение → extract_meal() → MealEntry → MealLogStore.append()
                           → InsulinCalculator.recommend() (если данных достаточно)
                           → reply_text + рекомендация + дисклеймер
```

### VLM — анализ фото

`LlmClient.analyze_photo(image_bytes, caption)`:

- Два шага: vision описывает фото → structured extraction парсит в `MealExtraction`
- Если есть подпись к фото — vision пропускается, парсинг идёт по тексту подписи
- Фото продукта/блюда (не упаковки) → base64 в multimodal message
- Модель оценивает тип продукта, размер порции, состав, БЖУ/ХЕ
- Результат → `MealExtraction` → дальше тот же поток, что для текста
- Vision: `MODEL_IMAGE`; extraction: `MODEL_IMAGE` в гибридном режиме

### Ошибки

- Лог + понятное сообщение пользователю
- `logger.exception` при сбое API

---

## 7. Работа с аудио (голосовые сообщения)

### Выбор подхода

| Подход | Решение | Почему не выбрали |
|--------|---------|-------------------|
| Telegram Bot API | ❌ | Нет API транскрибации для ботов |
| Whisper API (облако) | ✅ **наш выбор** | Простота, русский, ~$0.006/мин |
| Локальный Whisper / Vosk | запасной | Приватность, но сложнее и нужен GPU |
| Yandex SpeechKit | запасной | Лучший русский, но ~1 ₽/мин и IAM |
| Gemini multimodal STT | ❌ | Overkill и дороже для чистого STT |

### Архитектура

`TranscribeClient` — отдельный сервис, 1 класс = 1 файл.

```
голосовое (F.voice)
    → bot.download_file(.ogg)
    → TranscribeClient.transcribe(bytes, language="ru")
    → transcript
    → _handle_message() — тот же поток, что для текста
        → extract_meal() → MealLogStore → InsulinCalculator
        → или RagService для справочного вопроса
```

### Конфигурация (гибрид)

| Переменная | Пример | Назначение |
|------------|--------|------------|
| `MODEL_AUDIO` | `openai/whisper-1` | Модель STT |
| `AUDIO_LLM_BASE_URL` | `https://openrouter.ai/api/v1` | Endpoint Whisper |
| `AUDIO_OPENROUTER_API_KEY` | `sk-or-...` | Ключ (отдельно от text/image) |

В гибридном режиме текст — Ollama локально, STT — OpenRouter.

### Детали реализации

- Формат Telegram: Ogg Opus (`.ogg`) — **без конвертации**, Whisper принимает напрямую
- Язык: `language="ru"` — явно, не auto-detect
- Лимит бота: 20 MB на файл (для голосовых достаточно, обычно < 1 мин)
- Пользователю: «Слушаю голосовое, подожди немного…» на время STT
- Ошибки: лог + «Не удалось распознать голос» — бот не падает
- История: `[голос] {transcript}` сохраняется в `ChatHistory`

### Стоимость и приватность

- ~$0.006/мин (~0.5 ₽ за 30-секундное голосовое)
- Аудио передаётся в OpenRouter → OpenAI Whisper
- Альтернатива для 152-ФЗ: локальный `faster-whisper` на своём GPU

---

## 8. Расчёт инсулина

`InsulinCalculator` — чистая математика, без LLM.

### Коэффициенты

Из `.env` или стандартные дефолты:

| Переменная | Дефолт | Смысл |
|------------|--------|-------|
| `CARB_RATIO` | 12 | г углеводов на 1 ЕД |
| `INSULIN_SENSITIVITY` | 2.0 | на сколько ммоль/л снижает 1 ЕД |
| `TARGET_GLUCOSE_MIN` | 5.0 | нижняя граница целевого сахара, ммоль/л |
| `TARGET_GLUCOSE_MAX` | 10.0 | верхняя граница целевого сахара, ммоль/л |
| `FPU_RATIO` | 10 | г (белки + жиры) на 1 БЖЕ для доколки |

### Формула (рекомендация, не назначение)

```
доза_на_углеводы = углеводы_г / CARB_RATIO
коррекция = 0, если TARGET_GLUCOSE_MIN ≤ сахар_до ≤ TARGET_GLUCOSE_MAX
коррекция = (сахар_до − TARGET_GLUCOSE_MAX) / INSULIN_SENSITIVITY, если сахар_до > MAX
коррекция = (сахар_до − TARGET_GLUCOSE_MIN) / INSULIN_SENSITIVITY, если сахар_до < MIN
доколка_на_БЖЕ = (белки + жиры) / FPU_RATIO
итого = доза_на_углеводы + коррекция (+ доколка при необходимости)
```

Ответ Нике: «На X ХЕ рекомендую доколоть Y ЕД за Z минут до еды» + дисклеймер.

---

## 9. Сценарии работы

| Сценарий | Как |
|----------|-----|
| Первый контакт | `/start` — приветствие Ники |
| Запись приёма пищи (текст) | structured output → JSON → ответ с ХЕ и рекомендацией |
| Фото блюда | VLM → structured output → JSON → ответ |
| Голосовое сообщение | STT → текст → учёт или RAG |
| Справочный вопрос | `RagService` — query transform + retrieval (режим из конфига) + ответ |
| Переиндексация | `/index` — полная переиндексация PDF |
| Статус индекса | `/index_status` — число чанков |
| Отчёт за день | `/report_day` → агрегация из JSON |
| Отчёт за неделю | `/report_week` → агрегация + `LlmClient.ask_brief()` (Gemini в гибриде) |
| Коэффициенты | `/coeffs` — показать текущие значения |
| Сброс диалога | `/reset` |
| Сброс учёта | `/reset_log` |
| Справка | `/help`, `/example` |
| Оценка RAG | `/evaluate_dataset` — RAGAS-метрики на датасете LangSmith |

---

## 10. Конфигурирование

Переменные в `.env` (шаблон — `.env.example`):

| Переменная | Дефолт | Назначение |
|------------|--------|------------|
| `TELEGRAM_BOT_TOKEN` | — | Токен бота |
| `OPENROUTER_API_KEY` | — | API-ключ (пустой для Ollama) |
| `LLM_PROVIDER` | `openrouter` | `openrouter` \| `ollama` |
| `LLM_BASE_URL` | openrouter URL | URL API |
| `MODEL_TEXT` | `openai/gpt-4o-mini` | Текст, диалог |
| `MODEL_IMAGE` | `openai/gpt-4o-mini` | Vision + structured extraction (гибрид) |
| `MODEL_AUDIO` | `openai/whisper-1` | Транскрипция |
| `IMAGE_LLM_BASE_URL` | = `LLM_BASE_URL` | URL для vision / extraction |
| `IMAGE_OPENROUTER_API_KEY` | = `OPENROUTER_API_KEY` | Ключ для image |
| `AUDIO_LLM_BASE_URL` | = `LLM_BASE_URL` | URL для STT |
| `AUDIO_OPENROUTER_API_KEY` | = `OPENROUTER_API_KEY` | Ключ для audio |
| `SYSTEM_PROMPT` | дефолт в `config.py` | Роль (опционально) |
| `DATA_FILE` | `data/meals.json` | Файл учёта |
| `CARB_RATIO` | `12` | Углеводный коэффициент |
| `INSULIN_SENSITIVITY` | `2.0` | Чувствительность к инсулину |
| `TARGET_GLUCOSE_MIN` | `5.0` | Целевой сахар, мин |
| `TARGET_GLUCOSE_MAX` | `10.0` | Целевой сахар, макс |
| `FPU_RATIO` | `10` | Коэффициент БЖЕ |
| `OPENAI_BASE_URL` | = `LLM_BASE_URL` | URL для LangChain (OpenRouter); маппится в `Config` |
| `MODEL_EMBEDDING` | `openai/text-embedding-3-small` | Эмбеддинги для semantic retrieval |
| `EMBEDDING_PROVIDER` | `openai` | `openai` \| `huggingface` |
| `RAG_RETRIEVAL_MODE` | `semantic` | `semantic` \| `hybrid` \| `hybrid_rerank` |
| `SEMANTIC_RETRIEVER_K` | `4` | Top-K для semantic search |
| `BM25_RETRIEVER_K` | `4` | Top-K для BM25 |
| `HYBRID_RETRIEVER_K` | `4` | Top-K после fusion semantic+BM25 |
| `RERANKER_FETCH_K` | `10` | Кандидатов на вход reranker |
| `RERANKER_K` | `4` | Top-K после reranker (в контекст LLM) |
| `MODEL_CROSSENCODER` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Модель cross-encoder |
| `RETRIEVER_K` | `4` | **Deprecated** — alias для `SEMANTIC_RETRIEVER_K` (обратная совместимость) |
| `DATA_PDF` | путь к PDF в `data/` | Источник для индексации |
| `SHOW_SOURCES` | `false` | Показывать источники в RAG-ответах |
| `LANGSMITH_API_KEY` | — | Ключ LangSmith |
| `LANGSMITH_TRACING_V2` | `true` | Автотрейсинг LangChain |
| `LANGSMITH_PROJECT` | — | Имя проекта в LangSmith |
| `LANGSMITH_DATASET` | — | Датасет по умолчанию для evaluation |
| `RAGAS_LLM_MODEL` | — | LLM для RAGAS-метрик |
| `RAGAS_EMBEDDING_MODEL` | — | Embeddings для RAGAS-метрик |
| `RAGAS_EMBEDDING_PROVIDER` | `openai` | `openai` \| `huggingface` |

---

## 11. RAG: индексация и пайплайн

### Indexer

`Indexer` — 1 класс = 1 файл (`indexer.py`).

```
PDF (DATA_PDF) + JSON (data/)
    → PyPDFLoader / JSON loader
    → RecursiveCharacterTextSplitter
    → OpenAIEmbeddings или HuggingFaceEmbeddings (MODEL_EMBEDDING, EMBEDDING_PROVIDER)
    → InMemoryVectorStore
    → BM25Retriever (те же чанки, in-memory)
```

- `index()` — полная переиндексация, возвращает число чанков
- `chunk_count` — текущий размер индекса
- Вызывается при старте (`main.py`) и по команде `/index`
- Чанки хранятся в памяти — нужны и для vector store, и для BM25

### Hybrid retriever

`HybridRetriever` — 1 класс = 1 файл (`hybrid_retriever.py`).

- Semantic retriever из `Indexer.as_semantic_retriever(k=SEMANTIC_RETRIEVER_K)`
- BM25 retriever из `Indexer.as_bm25_retriever(k=BM25_RETRIEVER_K)`
- Fusion: Reciprocal Rank Fusion (RRF) по образцу `advanced-hybrid-rag.ipynb` Part 1
- Возвращает top `HYBRID_RETRIEVER_K` уникальных документов

### Reranker

`Reranker` — 1 класс = 1 файл (`reranker.py`).

- `sentence_transformers.CrossEncoder` с моделью `MODEL_CROSSENCODER`
- Вход: query + top `RERANKER_FETCH_K` документов от hybrid retriever
- Выход: top `RERANKER_K` документов по score cross-encoder
- Референс — `advanced-hybrid-rag.ipynb` Part 2

### RagService

`RagService` — 1 класс = 1 файл (`rag_service.py`).

Цепочка в LCEL-стиле; query transformation **сохраняется** (как в `naive-rag.ipynb`):

```
вопрос + history (LangChain messages)
    → query transformation (MODEL_RAG)
    → retrieval (по RAG_RETRIEVAL_MODE):
        semantic    → semantic retriever
        hybrid      → HybridRetriever
        hybrid_rerank → HybridRetriever → Reranker
    → generation: system + history + context chunks
    → AIMessage → ответ пользователю
```

- Retriever выбирается по `RAG_RETRIEVAL_MODE` при инициализации `RagService`
- Контекст — только retrieved chunks, без галлюцинаций вне базы
- История — те же `HumanMessage` / `AIMessage`, что и для учёта
- Async-обёртка над sync LangChain там, где API синхронный (`asyncio.to_thread`)
- При старте логируется активный режим retrieval и параметры K

### Команды индексации

| Команда | Действие |
|---------|----------|
| `/index` | Полная переиндексация PDF |
| `/index_status` | «Проиндексировано N чанков» или «Индекс пуст» |

---

## 12. Логгирование

- Стандартный `logging`, уровень INFO
- Логи: старт, модели, входящие сообщения, запросы LLM/VLM/STT/RAG, индексация, ошибки
- `logger.exception` при сбое API

---

## 13. Сборка и деплой

```bash
make run          # локально
make docker-run   # в контейнере
```

Деплой на сервер — вне текущего scope.

---

## 14. Мониторинг и оценка качества RAG

### Отображение источников

- `RagService.answer()` возвращает ответ и retrieved documents
- При `SHOW_SOURCES=true` handler добавляет блок «📚 Источники: …» с путём к файлу и страницами
- Референс форматирования — `rag-evaluation-practice.ipynb`

### LangSmith трейсинг

- Включение через `LANGSMITH_*` в `.env` — LangChain подхватывает автоматически, код не меняется
- Провайдер LLM/embeddings — OpenRouter (`OPENAI_BASE_URL=https://openrouter.ai/api/v1`)

### Синтез датасетов — `dataset_synthesizer.py`

- 2 чанка на каждый PDF в `data/`, LLM генерирует Q&A по каждому чанку
- Готовые Q&A подгружаются из JSON-файлов в `data/` (если есть)
- Сохранение: `datasets/05-rag-qa-dataset.json`
- Загрузка в LangSmith с проверкой дубликатов
- `make dataset`, `make dataset-upload`

### Evaluation — `evaluation.py`

- Команда `/evaluate_dataset` — полный цикл по референсу `rag-evaluation-practice.ipynb` (§5)
- 6 метрик RAGAS: faithfulness, answer_relevancy, answer_correctness, answer_similarity, context_recall, context_precision
- Модели RAGAS — `RAGAS_LLM_MODEL`, `RAGAS_EMBEDDING_MODEL`, `RAGAS_EMBEDDING_PROVIDER`
- Результаты загружаются в LangSmith как feedback
- Evaluation использует тот же `RAG_RETRIEVAL_MODE`, что и бот — для честного сравнения режимов
