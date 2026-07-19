from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "care_products.json"


def load_products() -> list[dict[str, Any]]:
    with _DATA_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        msg = f"Expected list in {_DATA_PATH}"
        raise TypeError(msg)
    return data


def search_products(query: str, *, limit: int = 8) -> list[dict[str, Any]]:
    """Простой текстовый поиск по полям каталога расходников."""
    q = query.strip().lower()
    if not q:
        return []

    tokens = [t for t in q.replace(",", " ").split() if t]
    products = load_products()
    scored: list[tuple[int, dict[str, Any]]] = []

    for product in products:
        blob = " ".join(
            [
                str(product.get("type", "")),
                str(product.get("name", "")),
                str(product.get("brand", "")),
                str(product.get("description", "")),
                str(product.get("conditions", "")),
                str(product.get("promo", "") or ""),
                " ".join(product.get("compatibility") or []),
            ]
        ).lower()
        score = sum(1 for token in tokens if token in blob)
        if score > 0:
            scored.append((score, product))

    scored.sort(key=lambda item: (-item[0], str(item[1].get("name", ""))))
    return [item for _, item in scored[:limit]]
