# Сравнение моделей эмбеддингов для RAG (русский язык)

**Дата:** 2026-07-12  
**Корпус:** PDF-руководство (225 чанков) + 7 JSON-инструкций = 232 документа  
**Retriever:** top-4, `RETRIEVER_K=4`  
**RAG-генерация:** `google/gemini-2.5-flash` (OpenRouter) — одинакова для всех прогонов

## Модели (MTEB / практика)

| # | Провайдер | Модель | MTEB (ориентир) | Размерность |
|---|-----------|--------|-----------------|-------------|
| 1 | OpenRouter | `openai/text-embedding-3-small` | сильная универсальная baseline | 1536 |
| 2 | OpenRouter | `openai/text-embedding-3-large` | выше small на retrieval-задачах | 3072 |
| 3 | Ollama (локально) | `aroxima/multilingual-e5-large-instruct:latest` | top multilingual (E5 family) | 1024 |

> `intfloat/multilingual-e5-large` через OpenRouter на полном индексе (232 док.) дал `No embedding data received` — в сравнение не включена. На одиночных запросах работает.

## Тестовые вопросы

Одинаковые для всех конфигураций (после переиндексации):

1. «Что такое гипогликемия?»
2. «Как хранить инсулин?»
3. «Сколько инъекций инсулина необходимо в день?»

## Результаты retrieval@1

Оценка: сколько ключевых маркеров из эталона найдено в **первом** retrieved-документе.

| Модель | Гипогликемия | Хранение | Инъекции | Итого |
|--------|:------------:|:--------:|:--------:|:-----:|
| OpenRouter `text-embedding-3-small` | 3/3 | 4/4 | 4/4 | **11/11 (100%)** |
| OpenRouter `text-embedding-3-large` | 3/3 | 4/4 | 4/4 | **11/11 (100%)** |
| Ollama `multilingual-e5-large-instruct` | 2/3 | 4/4 | 4/4 | **10/11 (90.9%)** |

### Детали по «гипогликемия» (единственное расхождение)

| Модель | Top-1 документ |
|--------|----------------|
| OpenRouter small/large | JSON `diabetes_hypoglycemia.json` — определение «ниже 3,9 ммоль/л» |
| Ollama e5 | PDF-чанк про контринсулярные гормоны (контекст гипогликемии, но не определение) |

RAG-ответ при Ollama e5 всё равно **корректный** — в top-4 попал нужный JSON, Gemini собрал ответ из контекста.

## Качество RAG-ответов

На всех трёх конфигурациях ответы по существу совпали:

- **Гипогликемия:** определение, порог 3,9 ммоль/л, целевой минимум 4–5 ммоль/л
- **Хранение:** +2…+8 °C в холодильнике, комнатная t° для ручки, не замораживать
- **Инъекции:** базис-болюс, 3 bolus + базальный, итого 4–6 уколов/сутки

## Вывод: что лучше для русского

| Критерий | Лучший выбор |
|----------|--------------|
| **Retrieval на русском (наш корпус)** | `openai/text-embedding-3-small` или `text-embedding-3-large` — паритет 100% |
| **Стоимость / скорость** | `text-embedding-3-small` — дешевле, индекс ~5 с |
| **Офлайн / приватность** | Ollama `multilingual-e5-large-instruct` — ~17 с индекс, 90.9% retrieval |
| **Размерность / память** | small (1536) компактнее large (3072) |

**Рекомендация для бота:** оставить **`EMBEDDING_PROVIDER=openrouter`** + **`MODEL_EMBEDDING=openai/text-embedding-3-small`** — лучший баланс цены, скорости и качества на русском для данного корпуса.

Ollama e5 имеет смысл, если нужен локальный пайплайн без отправки текста в облако; для улучшения retrieval стоит добавить префиксы E5-instruct (`query: …` / `passage: …`).

## Настройка `.env`

### OpenRouter (рекомендуется)

```env
EMBEDDING_PROVIDER=openrouter
MODEL_EMBEDDING=openai/text-embedding-3-small
OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

### OpenRouter, модель покрупнее

```env
EMBEDDING_PROVIDER=openrouter
MODEL_EMBEDDING=openai/text-embedding-3-large
```

### Ollama (локально)

```bash
ollama pull aroxima/multilingual-e5-large-instruct:latest
```

```env
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=aroxima/multilingual-e5-large-instruct:latest
OLLAMA_EMBEDDING_BASE_URL=http://localhost:11434
```

После смены модели: перезапуск бота → `/index` или автоматическая переиндексация при старте.

## Как воспроизвести

```bash
PYTHONPATH=src uv run python scripts/embedding_experiment.py
```
