# mcp-nika-agent

MCP-сервер для Telegram-бота Ника: каталог расходников и онлайн-КБЖУ.

## Tools

- `search_products` — поиск по `data/care_products.json`
- `food_nutrition` — Open Food Facts API (+ fallback для типовых продуктов)
- `calculate_meal_bolus` — оценка ХЕ и болюса (аналог учебного deposit calculator)

## Запуск

Из корня головного проекта:

```bash
make run-mcp-nika
```

Сервер: streamable-http на `http://127.0.0.1:8000/mcp`.
