"""Сравнение моделей эмбеддингов: retrieval и RAG-ответы на русском."""

from __future__ import annotations

import asyncio
import textwrap
from dataclasses import dataclass, replace

from nika.config import Config
from nika.services.indexer import Indexer
from nika.services.rag_service import RagService


@dataclass(frozen=True)
class EmbeddingProfile:
    name: str
    provider: str
    model: str


PROFILES = [
    EmbeddingProfile(
        "openrouter-3-small",
        "openrouter",
        "openai/text-embedding-3-small",
    ),
    EmbeddingProfile(
        "openrouter-3-large",
        "openrouter",
        "openai/text-embedding-3-large",
    ),
    EmbeddingProfile(
        "ollama-multilingual-e5",
        "ollama",
        "aroxima/multilingual-e5-large-instruct:latest",
    ),
]

QUESTIONS: list[tuple[str, list[str]]] = [
    (
        "Что такое гипогликемия?",
        ["гипоглик", "3,9", "ммоль"],
    ),
    (
        "Как хранить инсулин?",
        ["холодильник", "+2", "+8", "замораж"],
    ),
    (
        "Сколько инъекций инсулина необходимо в день?",
        ["инъекц", "4", "6", "базис"],
    ),
]


def preview(text: str, width: int = 120) -> str:
    cleaned = " ".join(text.split())
    return textwrap.shorten(cleaned, width=width, placeholder="…")


def score_retrieval(text: str, markers: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for marker in markers if marker.lower() in lowered)


def apply_profile(config: Config, profile: EmbeddingProfile) -> Config:
    return replace(
        config,
        embedding_provider=profile.provider,
        model_embedding=profile.model,
    )


async def run_profile(config: Config, profile: EmbeddingProfile) -> dict[str, object]:
    profile_config = apply_profile(config, profile)
    print(f"\n{'=' * 60}")
    print(f"Профиль: {profile.name}")
    print(f"  provider={profile.provider} model={profile.model}")

    indexer = Indexer(profile_config)
    doc_count = await indexer.aindex()
    print(f"  indexed documents={doc_count}")

    rag = RagService(profile_config, indexer)
    retriever = indexer.as_retriever()
    total_score = 0
    max_score = 0
    rows: list[dict[str, object]] = []

    for question, markers in QUESTIONS:
        docs = retriever.invoke(question)
        top = docs[0].page_content if docs else ""
        top_score = score_retrieval(top, markers)
        total_score += top_score
        max_score += len(markers)

        answer = await rag.aanswer(question, [])
        answer_score = score_retrieval(answer, markers)

        print(f"\n  Q: {question}")
        print(f"  top-1 score: {top_score}/{len(markers)}")
        print(f"  top-1: {preview(top)}")
        print(f"  answer score: {answer_score}/{len(markers)}")
        print(f"  A: {preview(answer, 220)}")

        rows.append(
            {
                "question": question,
                "top_score": top_score,
                "marker_count": len(markers),
                "answer_score": answer_score,
                "top_preview": preview(top, 160),
                "answer_preview": preview(answer, 220),
            },
        )

    retrieval_pct = round(total_score / max_score * 100, 1) if max_score else 0.0
    print(f"\n  Итого retrieval@1: {total_score}/{max_score} ({retrieval_pct}%)")
    return {
        "profile": profile.name,
        "provider": profile.provider,
        "model": profile.model,
        "retrieval_score": total_score,
        "retrieval_max": max_score,
        "retrieval_pct": retrieval_pct,
        "rows": rows,
    }


async def main() -> None:
    config = Config.from_env()
    results: list[dict[str, object]] = []
    for profile in PROFILES:
        results.append(await run_profile(config, profile))

    print(f"\n{'=' * 60}")
    print("Сводка:")
    for item in sorted(
        results,
        key=lambda row: float(row["retrieval_pct"]),
        reverse=True,
    ):
        print(
            f"  {item['profile']}: "
            f"{item['retrieval_score']}/{item['retrieval_max']} "
            f"({item['retrieval_pct']}%)",
        )


if __name__ == "__main__":
    asyncio.run(main())
