# Отчёт по ДЗ-10: Оценка качества агентов

**Проект:** Ника (Telegram ReAct-агент + MCP `mcp-nika-agent`)  
**Стек оценки:** `agentevals`, `pytest`, `pytest-asyncio`  
**Запуск:** `make test-deterministic` / `make test-llm-judge` / `make test-all`  
**Judge-модель:** `AGENTEVALS_LLM_MODEL=openai:gpt-4o`

---

## Разработанные тесты

### Детерминированные тесты

Файл: `tests/test_agent_deterministic.py`  
Evaluator: `create_trajectory_match_evaluator`  
Запуск: `make test-deterministic` → **6 passed** (~42s)

| Тест | Режим | Сценарий | Проверка |
|------|-------|----------|----------|
| `test_extract_trajectory_returns_messages` | smoke | «Спасибо» | helper возвращает HumanMessage + AIMessage |
| `test_rag_search_superset` | superset + ignore args | «Что такое гипогликемия?» | минимум `rag_search` |
| `test_glucose_unit_converter_superset` | superset + ignore args | «Переведи 180 мг/дл в ммоль/л» | минимум `glucose_unit_converter` |
| `test_insulin_storage_rag_superset` | superset + ignore args | «Как хранить инсулин?» | минимум `rag_search` |
| `test_glucose_converter_exact_args` | superset + **exact** args | «Переведи 5.5 ммоль/л в мг/дл» | tool + точные `value` / `from_unit` / `to_unit` |
| `test_search_products_subset` | **subset** + ignore args | «Какие полоски к Contour Plus?» | только `search_products`, без лишних tools (нужен MCP) |

### Тесты с LLM-as-a-Judge

Файл: `tests/test_agent_llm_judge.py`  
Evaluator: `create_async_trajectory_llm_as_judge` + `TRAJECTORY_ACCURACY_PROMPT_WITH_REFERENCE`  
Критерий: `score > 0.7` (bool `True` тоже проходит)  
Запуск: `make test-llm-judge` → **2 passed** (~37s)

| Тест | Сценарий | Эталон | Результат judge |
|------|----------|--------|-----------------|
| `test_search_products_llm_judge` | полоски Contour Plus | траектория с `search_products` | score=`True`, комментарий: tool и ответ семантически совпадают с reference |
| `test_glucose_converter_llm_judge` | 180 мг/дл → ммоль/л | траектория с `glucose_unit_converter` → ~10 ммоль/л | score=`True` |

---

## Результаты тестирования

### Стабильность выполнения тестов

- **Match-тесты** стабильны при `tool_args_match_mode="ignore"`: LLM переформулирует query (`гипогликемия` → `гипогликемия определение симптомы`), но факт вызова tool совпадает.
- **Exact args** для конвертера прошёл: модель стабильно передаёт `mmol_l` / `mg_dl` и число `5.5` / `180`.
- **LLM-as-a-Judge** согласовался с ожиданиями на обоих сценариях; дороже и медленнее match (~30–40s вместе с индексацией).
- Повторные прогоны `make test-deterministic` / `make test-llm-judge` — зелёные без флапов в рамках сессии.
- Session-fixture: индекс + агент один раз на прогон; изоляция через уникальный `thread_id`.

### Выявленные проблемы

- **`AGENT_RUN_LIMIT=3`** в Telegram: при нескольких вопросах подряд агент отвечает `Model call limits exceeded: run limit (3/3)`. Для e2e в `conftest` поднят лимит до **5** (`AGENT_RUN_LIMIT_TEST`).
- **MCP обязателен** для `search_products`-тестов: без `make run-mcp-nika` — skip. Graceful degradation бота при этом корректна, но e2e по расходникам неполный.
- **RAGAS (`/evaluate_dataset`) и agentevals** — разные контуры: первый оценивает ответ/контекст, второй — траекторию tools. Путать их не стоит.
- Доработки по ходу спринта: `AgentService.get_trajectory`, каркас `tests/`, проброс `OPENAI_API_KEY` из OpenRouter-переменных для judge, `AGENTEVALS_LLM_MODEL` в `Config`.

---

## Инсайты

- Начинать с **trajectory match** (`superset` / `subset`) выгоднее: быстро, дёшево, ловит «не тот tool».
- **`exact` args** имеет смысл только там, где контракт жёсткий (конвертер единиц); для `rag_search.query` почти всегда нужен `ignore`.
- **LLM-as-a-Judge** полезен, когда важен смысл ответа, а не только имя tool; нужен judge со structured output (`openai:gpt-4o`).
- Сложность: не банковский эталон курса, а домен Ники + HITL/MCP/лимиты — тесты должны отражать реальную маршрутизацию (`mode=search` / `tools`) и поднятие MCP.
- Интересно: subset на `search_products` хорошо ловит «лишний» `rag_search` на вопросах про расходники — это как раз типичная ошибка tool-policy.
