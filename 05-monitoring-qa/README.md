# Ника — Telegram-ассистент по диабету + RAG

Telegram-бот: учёт питания и инсулина, фото/голос, отчёты и справочные ответы
по PDF-руководству через LangChain RAG.

## Требования

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Telegram Bot Token
- OpenRouter API key (для RAG, vision, audio)
- PDF в `data/` (см. `DATA_PDF` в `.env`)

## Быстрый старт

```bash
cp .env.example .env
# заполнить TELEGRAM_BOT_TOKEN, OPENROUTER_API_KEY (или IMAGE_/AUDIO_ ключи)
# положить PDF в data/

make run
```

При старте бот переиндексирует PDF. В логах:

```
Vector index ready: chunk_count=225
RAG config: pdf=... model=google/gemini-2.5-flash ...
```

## Переменные RAG

| Переменная | Назначение |
|------------|------------|
| `OPENAI_BASE_URL` | OpenRouter для LangChain (маппится в Config) |
| `MODEL_EMBEDDING` | Модель эмбеддингов |
| `MODEL_RAG` | LLM для RAG (в гибриде дефолт — `MODEL_IMAGE`) |
| `RETRIEVER_K` | Top-K чанков |
| `DATA_PDF` | Путь к PDF |

## Гибрид Ollama + OpenRouter

```env
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434/v1
MODEL_TEXT=deepseek-r1:latest

OPENAI_BASE_URL=https://openrouter.ai/api/v1
IMAGE_OPENROUTER_API_KEY=sk-or-...
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
| `/index` | Переиндексация PDF |
| `/index_status` | Число чанков |
| `/report_day`, `/report_week` | Отчёты |
| `/reset` | Сброс истории |
| `/reset_log` | Сброс учёта |

Справочный вопрос → RAG; запись о еде → учёт.

## Документация

- [docs/idea.md](docs/idea.md) — идея
- [docs/vision.md](docs/vision.md) — архитектура
- [docs/tasklist.md](docs/tasklist.md) — план итераций
