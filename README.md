# AI Agents — домашние задания

Репозиторий с домашними заданиями по курсу [**AI-driven разработка ИИ-агентов**](https://github.com/aidialogs/llmstart-ai-agents).

## Участник

**Затуливетров Евгений Викторович**

## Прогресс по модулям

| Модуль | Тема | Статус |
|--------|------|--------|
| М01 | Основы LLM и стандартные API | ✅ |
| М02 | AI-driven разработка с Cursor | ✅ |
| М03 | Мультимодальность и локальный запуск LLM | ✅ |
| М04 | RAG с LangChain: от теории к практике | ✅ |
| М05 | Мониторинг и оценка качества RAG-систем | ✅ |
| М06 | Advanced RAG | ✅ |
| М07 | Агенты с LangChain и LangGraph | ✅ |
| М08 | Model Context Protocol (MCP) | ✅ |
| М09 | Безопасность агентных систем | ⬜ |
| М10 | Оценка качества агентов | ⬜ |
| М11 | Мультиагентные системы | ⬜ |

**Легенда:** ✅ — выполнено · 🔄 — в работе · ⬜ — не начато

## Структура репозитория

Папки добавляются по мере выполнения заданий:

```
ai-agents/
├── 01-llm-api/   # М01: CLI LLM-бот (OpenRouter) ✅
├── 02-aidd/      # М02: Telegram-бот «Ника» (aiogram + OpenRouter) ✅
├── 03-multimodal/ # М03: мультимодальный бот (текст, фото, голос) ✅
├── 04-rag-langchain/ # М04: RAG-бот (LangChain + PDF) ✅
├── 05-monitoring-qa/ # М05: мониторинг и оценка RAG (LangSmith, RAGAS) ✅
├── 06-advanced-rag/  # М06: Advanced RAG (hybrid retrieval, reranking) ✅
├── 07-agents-langgraph/ # М07: ReAct-агент (LangChain/LangGraph) ✅
├── 08-mcp/       # М08: Model Context Protocol (MCP) ✅
├── m09/          # М09: Безопасность агентных систем
├── m10/          # М10: Оценка качества агентов
├── m11/          # М11: Мультиагентные системы
└── README.md
```

## Как запускать

Общие требования: **Python 3.12**, [uv](https://docs.astral.sh/uv/), ключ [OpenRouter](https://openrouter.ai/).  
С М02 нужен ещё **Telegram Bot Token**. Подробности — в README (или `.env.example`) каждого модуля.

```bash
git clone https://github.com/zatulik2606/ai-agents.git
cd ai-agents
```

### М01 — CLI LLM-бот (`01-llm-api/`)

Консольный чат с LLM через OpenRouter (история диалога, `/stats`).

```bash
cd 01-llm-api
make setup
# создайте .env: OPENROUTER_API_KEY, MODEL_NAME (см. README модуля)
make run
```

### М02 — Telegram-бот «Ника» (`02-aidd/`)

Диалог в Telegram: system prompt, история, `/start` `/help` `/reset`.

```bash
cd 02-aidd
cp .env.example .env
# TELEGRAM_BOT_TOKEN, OPENROUTER_API_KEY
make run
```

### М03 — Мультимодальность (`03-multimodal/`)

Ника: текст, фото (vision), голос (STT), учёт еды и инсулина, отчёты.

```bash
cd 03-multimodal
cp .env.example .env
# TELEGRAM_BOT_TOKEN, OPENROUTER_API_KEY
# опционально: MODEL_IMAGE / MODEL_AUDIO, гибрид Ollama
make run
```

### М04 — RAG с LangChain (`04-rag-langchain/`)

Справочные ответы по PDF-руководству + маршрутизация учёт / RAG.

```bash
cd 04-rag-langchain
cp .env.example .env
# TELEGRAM_BOT_TOKEN, OPENROUTER_API_KEY; PDF в data/ (DATA_PDF)
make run
```

### М05 — Мониторинг и оценка (`05-monitoring-qa/`)

Источники в ответах, LangSmith, синтез датасета, RAGAS (`/evaluate_dataset`).

```bash
cd 05-monitoring-qa
cp .env.example .env
# TELEGRAM_BOT_TOKEN, OPENROUTER_API_KEY, LANGSMITH_API_KEY, LANGSMITH_TRACING_V2
# PDF + diabetes_*.json в data/
make run

# датасет (опционально):
make dataset && make dataset-upload
```

### М06 — Advanced RAG (`06-advanced-rag/`)

Hybrid retrieval (semantic + BM25) и cross-encoder rerank (`RAG_RETRIEVAL_MODE`).

```bash
cd 06-advanced-rag
cp .env.example .env
# TELEGRAM_BOT_TOKEN, OPENROUTER_API_KEY; data/ как в М05
# RAG_RETRIEVAL_MODE=semantic|hybrid|hybrid_rerank
make run
```

### М07 — Агенты LangChain / LangGraph (`07-agents-langgraph/`)

ReAct-агент: tools `rag_search`, `glucose_unit_converter` + MemorySaver.

```bash
cd 07-agents-langgraph
cp .env.example .env
# TELEGRAM_BOT_TOKEN, OPENROUTER_API_KEY; data/ как в М05–М06
make run
```

### М08 — Model Context Protocol (`08-mcp/`)

Те же возможности, плюс MCP-tools: `search_products`, `food_nutrition`, `calculate_meal_bolus`.  
Нужны **два терминала**: сначала MCP-сервер, потом бот.

```bash
cd 08-mcp
cp .env.example .env
# TELEGRAM_BOT_TOKEN, OPENROUTER_API_KEY
# опционально: MCP_SERVER_URL=http://127.0.0.1:8000/mcp

# Terminal 1 — MCP-сервер (streamable-http :8000)
make run-mcp-nika

# Terminal 2 — Telegram-бот
make run
```

Без `make run-mcp-nika` бот стартует, но MCP-tools недоступны (graceful degradation).
