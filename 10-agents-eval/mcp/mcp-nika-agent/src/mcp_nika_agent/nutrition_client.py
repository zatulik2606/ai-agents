from __future__ import annotations

import logging
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_OFF_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"
_USER_AGENT = "mcp-nika-agent/0.1 (diabetes assistant; educational)"

# Типовые продукты для запросов на русском — OFF лучше ищет по EN.
_QUERY_ALIASES: dict[str, str] = {
    "банан": "banana",
    "бананы": "banana",
    "яблоко": "apple",
    "яблоки": "apple",
    "апельсин": "orange",
    "груша": "pear",
    "виноград": "grapes",
    "клубника": "strawberry",
    "овсянка": "oatmeal",
    "овсяная каша": "oatmeal",
    "гречка": "buckwheat",
    "рис": "rice",
    "картофель": "potato",
    "хлеб": "bread",
    "молоко": "milk",
    "йогурт": "yogurt",
    "греческий йогурт": "greek yogurt",
    "творог": "cottage cheese",
    "сыр": "cheese",
    "яйцо": "egg",
    "яйца": "egg",
    "курица": "chicken",
    "рыба": "fish",
    "макароны": "pasta",
    "паста": "pasta",
}

# Ориентиры для сырых продуктов, когда OFF отдаёт брендовый мусор / таймаут.
# Значения типичные (на 100 г), не замена лабораторного анализа.
_COMMON_FOODS: dict[str, dict[str, Any]] = {
    "banana": {
        "name": "Банан (сырой)",
        "brands": "",
        "quantity": "на 100 г",
        "barcode": "",
        "per_100g": {
            "energy_kcal": 89,
            "proteins_g": 1.1,
            "fat_g": 0.3,
            "carbohydrates_g": 22.8,
            "sugars_g": 12.2,
            "fiber_g": 2.6,
        },
        "source": "reference_fallback",
    },
    "apple": {
        "name": "Яблоко (сырое)",
        "brands": "",
        "quantity": "на 100 г",
        "barcode": "",
        "per_100g": {
            "energy_kcal": 52,
            "proteins_g": 0.3,
            "fat_g": 0.2,
            "carbohydrates_g": 14.0,
            "sugars_g": 10.0,
            "fiber_g": 2.4,
        },
        "source": "reference_fallback",
    },
    "oatmeal": {
        "name": "Овсянка (сухая крупа)",
        "brands": "",
        "quantity": "на 100 г",
        "barcode": "",
        "per_100g": {
            "energy_kcal": 379,
            "proteins_g": 13.0,
            "fat_g": 7.0,
            "carbohydrates_g": 67.0,
            "sugars_g": 1.0,
            "fiber_g": 10.0,
        },
        "source": "reference_fallback",
    },
    "greek yogurt": {
        "name": "Греческий йогурт",
        "brands": "",
        "quantity": "на 100 г",
        "barcode": "",
        "per_100g": {
            "energy_kcal": 97,
            "proteins_g": 9.0,
            "fat_g": 5.0,
            "carbohydrates_g": 3.6,
            "sugars_g": 3.6,
            "fiber_g": 0,
        },
        "source": "reference_fallback",
    },
}

_JUNK_NAME_MARKERS = (
    "yogurt",
    "yoghurt",
    "йогурт",
    "bar",
    "бар",
    "juice",
    "сок",
    "candy",
    "шоколад",
    "chocolate",
    "milkshake",
    "smoothie",
    "cookie",
    "печенье",
    "chips",
    "cereal",
)


def _normalize_query(query: str) -> tuple[str, str]:
    """Вернуть (search_query_en_or_original, original)."""
    original = query.strip()
    key = original.lower()
    key = re.sub(r"[!?.…]+$", "", key).strip()
    if key in _QUERY_ALIASES:
        return _QUERY_ALIASES[key], original
    # «Сколько углеводов в банане?» → banana
    for ru, en in sorted(_QUERY_ALIASES.items(), key=lambda item: -len(item[0])):
        if ru in key:
            return en, original
    return original, original


def _has_carbs(item: dict[str, Any]) -> bool:
    carbs = (item.get("per_100g") or {}).get("carbohydrates_g")
    return isinstance(carbs, (int, float))


def _is_junk_for_fresh_food(name: str, search_query: str) -> bool:
    if search_query not in _COMMON_FOODS:
        return False
    name_l = name.lower()
    return any(marker in name_l for marker in _JUNK_NAME_MARKERS)


def _score_item(item: dict[str, Any], search_query: str, original: str) -> int:
    name = str(item.get("name") or "").lower()
    brands = str(item.get("brands") or "").lower()
    blob = f"{name} {brands}"
    score = 0
    for token in {search_query.lower(), original.lower()}:
        if token and token in blob:
            score += 3
        for part in token.split():
            if len(part) >= 3 and part in blob:
                score += 1
    if _has_carbs(item):
        score += 2
    if name and name != "без названия":
        score += 1
    if _is_junk_for_fresh_food(name, search_query):
        score -= 5
    return score


def _fallback_item(search_query: str) -> dict[str, Any] | None:
    item = _COMMON_FOODS.get(search_query.lower())
    if item is None:
        return None
    return dict(item)


def _summary_for(best: dict[str, Any]) -> str:
    carbs = best["per_100g"]["carbohydrates_g"]
    name = best["name"]
    source = best.get("source")
    suffix = " (справочные значения)" if source == "reference_fallback" else ""
    return (
        f"Лучшее совпадение: {name}{suffix}. "
        f"Углеводы: {carbs} г на 100 г "
        f"(белки: {best['per_100g'].get('proteins_g')}, "
        f"жиры: {best['per_100g'].get('fat_g')}, "
        f"ккал: {best['per_100g'].get('energy_kcal')})."
    )


def lookup_food_nutrition(query: str, *, limit: int = 8) -> dict[str, Any]:
    """Поиск КБЖУ через Open Food Facts + fallback для типовых продуктов."""
    search_query, original = _normalize_query(query)
    empty = {
        "query": original,
        "search_query": search_query,
        "count": 0,
        "summary": None,
        "best": None,
        "items": [],
    }
    if not search_query:
        return empty

    # Типовые сырые продукты: сразу справочник (OFF для них шумный и часто таймаутится).
    fallback_first = _fallback_item(search_query)
    if fallback_first is not None:
        return {
            "query": original,
            "search_query": search_query,
            "count": 1,
            "summary": _summary_for(fallback_first),
            "best": fallback_first,
            "items": [fallback_first],
            "note": "reference_fallback for common food",
        }

    params = {
        "search_terms": search_query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": max(limit, 10),
        "fields": "product_name,brands,nutriments,quantity,code",
    }
    headers = {"User-Agent": _USER_AGENT}
    timeout = httpx.Timeout(25.0, connect=8.0)

    payload: dict[str, Any] = {}
    off_failed = False
    for attempt in range(2):
        try:
            with httpx.Client(timeout=timeout, headers=headers) as client:
                response = client.get(_OFF_SEARCH_URL, params=params)
                response.raise_for_status()
                payload = response.json()
            break
        except Exception as exc:
            logger.warning(
                "Open Food Facts attempt %s failed for %r: %s",
                attempt + 1,
                search_query,
                exc,
            )
            off_failed = True
    else:
        fallback = _fallback_item(search_query)
        if fallback is not None:
            return {
                "query": original,
                "search_query": search_query,
                "count": 1,
                "summary": _summary_for(fallback),
                "best": fallback,
                "items": [fallback],
                "note": "Open Food Facts unavailable; used reference fallback",
            }
        raise RuntimeError("Open Food Facts unavailable")

    products = payload.get("products") or []
    results: list[dict[str, Any]] = []
    for product in products:
        nutriments = product.get("nutriments") or {}
        results.append(
            {
                "name": product.get("product_name") or "без названия",
                "brands": product.get("brands") or "",
                "quantity": product.get("quantity") or "",
                "barcode": product.get("code") or "",
                "per_100g": {
                    "energy_kcal": nutriments.get("energy-kcal_100g"),
                    "proteins_g": nutriments.get("proteins_100g"),
                    "fat_g": nutriments.get("fat_100g"),
                    "carbohydrates_g": nutriments.get("carbohydrates_100g"),
                    "sugars_g": nutriments.get("sugars_100g"),
                    "fiber_g": nutriments.get("fiber_100g"),
                },
            }
        )

    ranked = sorted(
        results,
        key=lambda item: _score_item(item, search_query, original),
        reverse=True,
    )
    with_carbs = [
        item
        for item in ranked
        if _has_carbs(item)
        and not _is_junk_for_fresh_food(str(item.get("name")), search_query)
    ]
    off_items = (with_carbs or [i for i in ranked if _has_carbs(i)] or ranked)[:limit]

    # Для типовых сырых продуктов OFF часто отдаёт батончики/йогурты —
    # best берём из справочника, OFF оставляем в items как доп. контекст.
    fallback = _fallback_item(search_query)
    if fallback is not None:
        best = fallback
        items = [fallback, *off_items][:limit]
        note = "reference_fallback preferred for common fresh food"
    else:
        best = off_items[0] if off_items else None
        items = off_items
        note = None

    summary = _summary_for(best) if best is not None else None
    result: dict[str, Any] = {
        "query": original,
        "search_query": search_query,
        "count": len(items),
        "summary": summary,
        "best": best,
        "items": items,
    }
    if note:
        result["note"] = note
    if off_failed:
        result["off_status"] = "unavailable"
    return result
