# Отчёт: Ника — Telegram-ассистент по диабету + RAG

## О проекте

**Ника** — Telegram-бот, дружелюбная ассистентка для человека с сахарным диабетом 1 типа. Помогает вести учёт питания и инсулина, оценивать ХЕ, рассчитывать доколку, обрабатывать текст/фото/голос и отвечать на **справочные вопросы** по PDF-руководству через LangChain RAG.

**Источник знаний:** `data/rukovodstvo_dlya_detei_i_ih_roditelei_saharnii_diabet_1_tipa_chto_neobhodimo_znat_178.pdf` (105 стр.) + JSON-инструкции в `data/diabetes_*.json`.

---

## Вариант задания: **AIDD**

| | **Лайт** | **AIDD** (выбран) |
|---|----------|-------------------|
| Бот | RAG поверх готового/минимального шаблона | Свой бот, развитый итерациями (AI-driven) |
| Эмбеддинги | Только OpenRouter, смена `MODEL_EMBEDDING` в `.env` | OpenRouter **+** локальный Ollama (`langchain-ollama`, `EMBEDDING_PROVIDER=ollama`) |
| Разработка | Точечные правки под ДЗ | `docs/tasklist.md`, `docs/vision.md`, 29 итераций |

**Почему AIDD, а не Лайт:**

1. **Проект** — не отдельный RAG-бот, а «Ника» из М02 (`02-aidd`) и М03 (`03-multimodal`): учёт, фото, голос, отчёты + RAG в М04.
2. **Эмбеддинги** — сравнены **3 модели**: две через OpenRouter (`text-embedding-3-small`, `text-embedding-3-large`) **и** локальная Ollama (`aroxima/multilingual-e5-large-instruct`) с `create_embeddings()` и `langchain-ollama` — это расширенный (AIDD) вариант ДЗ.
3. **Методология** — итерационный цикл согласование → реализация → проверка → tasklist → коммит.

Если нужен только **Лайт** по эмбеддингам — достаточно двух OpenRouter-моделей без Ollama; в отчёте зафиксирован полный AIDD-путь.

---

## Реализованные возможности

### Учёт и расчёты (Спринт 1)

- [x] Telegram-бот на aiogram 3.x (polling)
- [x] Конфигурация из `.env` (`Config`)
- [x] LLM-диалог с системным промптом и историей
- [x] Structured output → учёт приёмов пищи в `data/meals.json`
- [x] Расчёт инсулина (ХЕ, БЖЕ, доколка) с дисклеймером
- [x] Фото блюд (VLM) → учёт
- [x] Голосовые сообщения (Whisper) → учёт / RAG
- [x] Отчёты `/report_day`, `/report_week`
- [x] Команды `/start`, `/reset`, `/help`, `/reset_log`, `/coeffs`
- [x] Docker + Makefile

### RAG (Спринты 2–3)

- [x] Загрузка PDF (`PyPDFLoader`) + чанкинг (`RecursiveCharacterTextSplitter`)
- [x] Загрузка JSON-инструкций (`full_text` без чанкинга)
- [x] `reindex_all()` — PDF-чанки + JSON-документы → `InMemoryVectorStore`
- [x] Эмбеддинги через OpenRouter или Ollama (`EMBEDDING_PROVIDER`)
- [x] Query transformation с учётом истории диалога
- [x] RAG-цепочка: retrieve → generate (только по контексту)
- [x] Маршрутизация: справочный вопрос → RAG, запись о еде → учёт
- [x] UX: статус «Ищу в руководстве…»
- [x] Команды `/index`, `/index_status`
- [x] Автопереиндексация при старте бота
- [x] Гибрид Ollama (текст) + OpenRouter (RAG, vision, audio)

---

## Стек и модели

### Стек

| Компонент | Технология |
|-----------|------------|
| Язык | Python 3.12 |
| Зависимости | uv, `pyproject.toml` |
| Telegram | aiogram 3.x |
| LLM SDK | openai (OpenRouter-compatible) |
| RAG | LangChain, langchain-openai, langchain-community, langchain-ollama |
| Vector store | `InMemoryVectorStore` |
| PDF | PyPDFLoader, RecursiveCharacterTextSplitter |
| Качество кода | ruff, mypy (strict) |

### Модели (текущая конфигурация)

| Роль | Провайдер | Модель |
|------|-----------|--------|
| Текст / диалог | Ollama (локально) | `deepseek-r1:latest` |
| RAG-генерация | OpenRouter | `google/gemini-2.5-flash` |
| Vision (фото) | OpenRouter | `google/gemini-2.5-flash` |
| Транскрипция | OpenRouter | `openai/whisper-1` |
| **Эмбеддинги** | OpenRouter | `openai/text-embedding-3-small` |

Переменные: `MODEL_TEXT`, `MODEL_IMAGE`, `MODEL_AUDIO`, `MODEL_RAG`, `MODEL_EMBEDDING`, `EMBEDDING_PROVIDER`, `RETRIEVER_K=4`.

---

## Эксперименты с чанкингом

**Скрипт:** `scripts/chunk_experiment.py`  
**PDF:** 105 страниц  
**Тестовые вопросы:** «Сколько инъекций инсулина необходимо в день?», «Что такое гипогликемия?»

| Профиль | chunk_size | chunk_overlap | separators | Чанков |
|---------|------------|---------------|------------|--------|
| baseline | 1000 | 200 | default | 225 |
| large | 1500 | 150 | default | 157 |
| pdf_separators | 800 | 100 | PDF (`\n\n\n`, `\n\n`, …) | ~280 |

### Выводы

1. **baseline (1000/200)** — стандартный профиль; на вопрос «Сколько инъекций…» retrieval иногда возвращал менее точные фрагменты (ответ размазан по нескольким чанкам).
2. **large (1500/150)** — **рекомендуемый профиль**: меньше чанков (157), выше шанс, что цельный абзац про режим инсулинотерапии попадёт в один чанк; лучше для вопросов про инъекции и схемы лечения.
3. **pdf_separators (800/100)** — больше мелких чанков; полезен, если в PDF много коротких абзацев, но для нашего руководства уступает `large`.

**В продакшене:** `CHUNK_SIZE=1000`, `CHUNK_OVERLAP=200` (дефолт). Для улучшения retrieval рекомендуется `1500/150` (`CHUNK_SIZE=1500`, `CHUNK_OVERLAP=150`).

---

## JSON: загрузка инструкций

### Файлы (5 шт., 7 записей)

| Файл | Тема |
|------|------|
| `diabetes_hypoglycemia.json` | Гипогликемия: определение и действия |
| `diabetes_insulin_storage.json` | Хранение инсулина |
| `diabetes_insulin_injections.json` | Число инъекций, правила до/после еды |
| `diabetes_glucose_monitoring.json` | Когда измерять сахар |
| `diabetes_injection_sites.json` | Места и правила уколов |

Формат записи:

```json
[
  {
    "title": "Что такое гипогликемия",
    "full_text": "ГИПОГЛИКЕМИЯ — состояние, при котором..."
  }
]
```

### Реализация загрузки

Модуль: `src/nika/services/json_document_loader.py`  
Интеграция: `Indexer.reindex_all()` в `src/nika/services/indexer.py`.

**Эквивалент JSONLoader из задания:**

```python
from langchain_community.document_loaders import JSONLoader

loader = JSONLoader(
    file_path=str(json_path),
    jq_schema=".[].full_text",
    text_content=False,
)
documents = loader.load()
```

В проекте используется **тот же контракт** (`[].full_text`), но через стандартный `json` + `Document` — без зависимости `jq`. Каждая запись с `full_text` становится отдельным документом **без чанкинга** и объединяется с PDF-чанками:

```
reindex_all() → PDF chunks (225) + JSON docs (7) = 232 документа в vector store
```

Glob-паттерн: `data/diabetes_*.json`.

---

## Сравнение эмбеддингов

**Скрипт:** `scripts/embedding_experiment.py`  
**Подробный отчёт:** `docs/embedding_comparison_report.md`  
**Ориентир:** [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard)

### Сравниваемые модели

| # | Провайдер | Модель | Размерность |
|---|-----------|--------|-------------|
| 1 | OpenRouter | `openai/text-embedding-3-small` | 1536 |
| 2 | OpenRouter | `openai/text-embedding-3-large` | 3072 |
| 3 | Ollama (локально) | `aroxima/multilingual-e5-large-instruct:latest` | 1024 |

> `intfloat/multilingual-e5-large` через OpenRouter не прошёл полную индексацию (232 док.) — ошибка `No embedding data received`; на одиночных запросах работает.

### Тестовые вопросы (одинаковые для всех прогонов)

1. «Что такое гипогликемия?»
2. «Как хранить инсулин?»
3. «Сколько инъекций инсулина необходимо в день?»

После каждой смены модели — переиндексация и те же вопросы.

### Результаты retrieval@1

| Модель | Итого |
|--------|-------|
| `text-embedding-3-small` | **11/11 (100%)** |
| `text-embedding-3-large` | **11/11 (100%)** |
| Ollama `multilingual-e5-large-instruct` | **10/11 (90.9%)** |

Единственное расхождение: Ollama e5 на «гипогликемия» вернул PDF-чанк вместо JSON-определения в top-1, но RAG-ответ остался корректным (нужный контекст был в top-4).

### Выводы для русского языка

| Критерий | Рекомендация |
|----------|--------------|
| Качество retrieval | `text-embedding-3-small` ≈ `text-embedding-3-large` (100%) |
| Цена / скорость | **`text-embedding-3-small`** — ~5 с индекс, дешевле |
| Офлайн / приватность | Ollama e5 — ~17 с индекс, 90.9%; можно улучшить префиксами `query:` / `passage:` |

**Итоговая рекомендация:** `EMBEDDING_PROVIDER=openrouter`, `MODEL_EMBEDDING=openai/text-embedding-3-small`.

---

## Запуск и воспроизведение экспериментов

```bash
# Бот
make run

# Эксперименты
PYTHONPATH=src uv run python scripts/chunk_experiment.py
PYTHONPATH=src uv run python scripts/embedding_experiment.py
```

## Документация

- [README.md](README.md) — быстрый старт
- [docs/vision.md](docs/vision.md) — архитектура
- [docs/tasklist.md](docs/tasklist.md) — план итераций
- [docs/embedding_comparison_report.md](docs/embedding_comparison_report.md) — детали по эмбеддингам
