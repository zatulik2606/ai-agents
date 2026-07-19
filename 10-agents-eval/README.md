# Ника — Telegram-ассистент по диабету + ReAct-агент

Telegram-бот: учёт питания и инсулина, фото/голос, отчёты и справочные ответы
через **ReAct-агент** (`create_agent` + tools: `rag_search`, `glucose_unit_converter`, MCP).
Мониторинг (LangSmith, источники), оценка ответа (RAGAS) и e2e траекторий (`agentevals`).

## Требования

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Telegram Bot Token
- OpenRouter API key (для агента, vision, audio, RAGAS, LLM-as-a-Judge)
- PDF и JSON в `data/` (см. раздел [Данные](#данные))

## Быстрый старт

Нужны **два терминала**: MCP-сервер (tools) и Telegram-бот.

```bash
cd 10-agents-eval
cp .env.example .env
# заполнить TELEGRAM_BOT_TOKEN, OPENROUTER_API_KEY (или IMAGE_OPENROUTER_API_KEY)
# опционально: MCP_SERVER_URL=http://127.0.0.1:8000/mcp
# опционально: AGENT_RUN_LIMIT=3  (для e2e лучше >=5)
# опционально: AGENTEVALS_LLM_MODEL=openai:gpt-4o

# Terminal 1 — MCP-сервер mcp-nika-agent (streamable-http :8000)
make run-mcp-nika

# Terminal 2 — Telegram-бот
make run
```

Без `make run-mcp-nika` бот стартует, но MCP-tools
(`search_products`, `food_nutrition`, `calculate_meal_bolus`,
`order_care_product`, `register_cgm_sensor`) недоступны.

### Безопасность агента

- **HITL** — `order_care_product` и `register_cgm_sensor` требуют Accept / Reject
- **PII** — номера карт в ответах маскируются (`PIIMiddleware`)
- **Rate limits** — `AGENT_RUN_LIMIT` (дефолт 3) на model/tool calls за ход

Примеры:
- «Закажи полоски Contour на имя IVAN PETROV» → Accept → маскированный номер карты
- «Зарегистрируй сенсор FreeStyle Libre 3 на имя IVAN PETROV» → Accept/Reject

При старте бот переиндексирует документы. В логах:

```
Vector index ready: document_count=...
RAG config: pdf=... embedding=... model=...
Monitoring: show_sources=false langsmith=enabled dataset=05-rag-qa-dataset
```

## Данные

Каталог `data/`:

| Файл | Назначение |
|------|------------|
| `rukovodstvo_..._178.pdf` | Основное PDF-руководство (105 стр.) |
| `diabetes_*.json` | Готовые справочные тексты для RAG |
| `meals.json` | Учёт приёмов пищи (создаётся ботом) |

Если PDF отсутствует — скопируй из референсного проекта `05-monitoring-qa/data/`
или положи свой файл и укажи путь в `DATA_PDF`.

## Переменные RAG

| Переменная | Назначение |
|------------|------------|
| `OPENAI_BASE_URL` | OpenRouter для LangChain |
| `MODEL_EMBEDDING` | Модель эмбеддингов |
| `EMBEDDING_PROVIDER` | `openai` или `huggingface` |
| `HUGGINGFACE_EMBEDDING_MODEL` | Модель HF (если `EMBEDDING_PROVIDER=huggingface`) |
| `HUGGINGFACE_DEVICE` | `cpu` или `mps` / `cuda` |
| `MODEL_RAG` | LLM для RAG (в гибриде дефолт — `MODEL_IMAGE`) |
| `RAG_RETRIEVAL_MODE` | `semantic` \| `hybrid` \| `hybrid_rerank` |
| `SEMANTIC_RETRIEVER_K` | Top-K semantic search |
| `BM25_RETRIEVER_K` | Top-K BM25 |
| `HYBRID_RETRIEVER_K` | Top-K после fusion |
| `RERANKER_FETCH_K` | Кандидатов на вход reranker |
| `RERANKER_K` | Top-K после reranker |
| `MODEL_CROSSENCODER` | Модель cross-encoder |
| `DATA_PDF` | Путь к PDF |
| `SHOW_SOURCES` | `true` — показывать источники в ответах |

### Режимы Advanced RAG

| Режим | Описание |
|-------|----------|
| `semantic` | Только vector search |
| `hybrid` | Semantic + BM25 → RRF fusion |
| `hybrid_rerank` | Hybrid → cross-encoder reranker |

```env
RAG_RETRIEVAL_MODE=hybrid
EMBEDDING_PROVIDER=huggingface
HUGGINGFACE_EMBEDDING_MODEL=intfloat/multilingual-e5-base
HUGGINGFACE_DEVICE=cpu
```

## Мониторинг и оценка качества

### Источники в ответах

```env
SHOW_SOURCES=true
```

Бот добавляет блок «📚 Источники: …» с файлом и страницами retrieved chunks.

### LangSmith трейсинг

```env
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_TRACING_V2=true
LANGSMITH_PROJECT=06-rag-assistant
```

RAG-запросы автоматически попадают в LangSmith UI — код менять не нужно.

### Синтез Q&A-датасета

```bash
make dataset          # синтез из PDF + JSON → datasets/05-rag-qa-dataset.json
make dataset-upload   # загрузка в LangSmith (нужен LANGSMITH_API_KEY)
```

Синтез берёт 2 случайных чанка из каждого PDF и готовые Q&A из `diabetes_*.json`.

### Evaluation через RAGAS

В Telegram:

```
/evaluate_dataset
/evaluate_dataset my-dataset-name
```

Требуется: `LANGSMITH_API_KEY`, `OPENROUTER_API_KEY`, проиндексированный RAG,
датасет в LangSmith (`LANGSMITH_DATASET`).

**6 метрик RAGAS:**

| Метрика | Что измеряет |
|---------|--------------|
| faithfulness | Нет галлюцинаций вне контекста |
| answer_relevancy | Релевантность ответа вопросу |
| answer_correctness | Правильность vs эталон |
| answer_similarity | Похожесть на эталон |
| context_recall | Полнота найденного контекста |
| context_precision | Точность retrieval |

Результаты загружаются в LangSmith как feedback.

> RAGAS оценивает **качество ответа и контекста** (`/evaluate_dataset`).
> Траектории tools агента — отдельный контур ниже (`agentevals`).

### E2E-тесты агента (agentevals)

Траекторная оценка: какие tools вызвал агент и насколько это уместно.
Референс — `docs/references/agent-evaluation.ipynb`, детали — `docs/vision.md` §18.
Отчёт — [report.md](report.md).

```bash
# Terminal 1 (нужен для search_products-тестов)
make run-mcp-nika

# Terminal 2
make test-deterministic   # match-evaluators (быстрые)
make test-llm-judge       # LLM-as-a-Judge (медленнее, нужен structured output)
make test-all             # все тесты в tests/
```

| Переменная | Назначение |
|------------|------------|
| `AGENTEVALS_LLM_MODEL` | Модель судьи, формат `provider:model` (дефолт `openai:gpt-4o`) |
| `AGENT_RUN_LIMIT` | Лимит model/tool calls за ход; в тестах поднимается до 5 |
| `AGENT_RUN_LIMIT_TEST` | Опционально переопределить лимит только для pytest |

Структура:

```
tests/
├── conftest.py                 # agent fixture (индекс + AgentService)
├── helpers.py                  # extract_trajectory, print_trajectory
├── test_agent_deterministic.py # trajectory match
└── test_agent_llm_judge.py     # LLM-as-a-Judge
```

**Детерминированные** (`create_trajectory_match_evaluator`): `superset` / `subset`,
args `ignore` или `exact` — сценарии `rag_search`, `glucose_unit_converter`,
`search_products`.

**LLM-as-a-Judge** (`create_async_trajectory_llm_as_judge`): сравнение с reference
траекторией; модель должна стабильно отдавать structured output.

## Гибрид Ollama + OpenRouter

```env
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434/v1
MODEL_TEXT=deepseek-r1:latest

OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=sk-or-...
MODEL_IMAGE=google/gemini-2.5-flash
```

Диалог и учёт — Ollama; RAG, фото, голос — OpenRouter.

## Docker

```bash
make docker-run
```

PDF и `meals.json` монтируются из `./data`. Для Ollama с хоста:

```env
LLM_BASE_URL=http://host.docker.internal:11434/v1
```

## Команды бота

| Команда | Действие |
|---------|----------|
| `/index` | Переиндексация документов |
| `/index_status` | Число чанков в индексе |
| `/evaluate_dataset` | RAGAS-оценка датасета LangSmith |
| `/report_day`, `/report_week` | Отчёты по учёту |
| `/coeffs` | Коэффициенты расчёта инсулина |
| `/reset` | Сброс истории диалога |
| `/reset_log` | Сброс учёта приёмов пищи |
| `/help`, `/example` | Справка и примеры |

Справочный вопрос → агент (`rag_search` / MCP); запись о еде → учёт.

## Устранение неполадок

| Проблема | Решение |
|----------|---------|
| «PDF не найден» | Положи PDF в `data/`, проверь `DATA_PDF` |
| «LangSmith API key не настроен» | Задай `LANGSMITH_API_KEY` в `.env` |
| «Dataset not found» | `make dataset-upload` или укажи имя: `/evaluate_dataset имя` |
| «Индекс пуст» | `/index` или перезапусти бота |
| `TelegramConflictError` | Запущено два бота — оставь один `make run` |
| Rate limit / 429 | Подожди и повтори; смени `RAGAS_LLM_MODEL` на платную модель |
| Нет ключа OpenRouter | `OPENROUTER_API_KEY` нужен для RAGAS / judge |
| `Model call limits exceeded` | Подними `AGENT_RUN_LIMIT` (для чата и e2e) |
| `search_products` skip в тестах | Запусти `make run-mcp-nika` до pytest |
| LLM-judge падает / нет structured output | Смени `AGENTEVALS_LLM_MODEL` (например `openai:gpt-4o`) |

## Документация

- [docs/idea.md](docs/idea.md) — идея
- [docs/vision.md](docs/vision.md) — архитектура (§14 RAGAS, §18 e2e agentevals)
- [docs/tasklist.md](docs/tasklist.md) — план итераций
- [report.md](report.md) — отчёт по ДЗ-10 (результаты e2e)
