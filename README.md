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
| М06 | Advanced RAG | ⬜ |
| М07 | Агенты с LangChain и LangGraph | ⬜ |
| М08 | Model Context Protocol (MCP) | ⬜ |
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
├── m06/          # М06: Advanced RAG
├── m07/          # М07: Агенты с LangChain и LangGraph
├── m08/          # М08: Model Context Protocol (MCP)
├── m09/          # М09: Безопасность агентных систем
├── m10/          # М10: Оценка качества агентов
├── m11/          # М11: Мультиагентные системы
└── README.md
```

## Как запускать

> Раздел будет дополняться по мере выполнения модулей.

### Общие требования

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (рекомендуется) или pip

### М01 — CLI LLM-бот

```bash
cd 01-llm-api
make setup
# создайте .env с OPENROUTER_API_KEY (см. 01-llm-api/README.md)
make run
```

### М02 — Telegram-бот «Ника»

```bash
cd 02-aidd
make install
# создайте .env на основе .env.example (TELEGRAM_BOT_TOKEN, OPENROUTER_API_KEY)
make run
```

### М03 — Мультимодальный бот «Ника»

```bash
cd 03-multimodal
make install
# создайте .env на основе .env.example (TELEGRAM_BOT_TOKEN, OPENROUTER_API_KEY)
make run
```

### М04 — RAG-бот «Ника»

```bash
cd 04-rag-langchain
cp .env.example .env
# TELEGRAM_BOT_TOKEN, OPENROUTER_API_KEY; PDF в data/
make run
```

### М05 — Мониторинг и оценка RAG

```bash
cd 05-monitoring-qa
cp .env.example .env
# TELEGRAM_BOT_TOKEN, OPENROUTER_API_KEY, LANGSMITH_* (см. README модуля)
make run
```

### Быстрый старт

```bash
# Клонировать репозиторий
git clone <url-репозитория>
cd ai-agents

# Перейти в папку нужного модуля
cd 01-llm-api

# Установить зависимости
make setup
```

Инструкции по запуску конкретных заданий — в README внутри папки соответствующего модуля.
