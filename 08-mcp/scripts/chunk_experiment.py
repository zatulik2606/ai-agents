"""Сравнение профилей чанкинга PDF: число чанков, retrieval, RAG-ответы."""

from __future__ import annotations

import asyncio
import textwrap
from dataclasses import dataclass
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader

from nika.config import Config
from nika.services.indexer import PDF_SEPARATORS, split_documents
from nika.services.rag_service import RagService


@dataclass(frozen=True)
class ChunkProfile:
    name: str
    chunk_size: int
    chunk_overlap: int
    separators: list[str] | None


PROFILES = [
    ChunkProfile("baseline", 1000, 200, None),
    ChunkProfile("large", 1500, 150, None),
    ChunkProfile("pdf_separators", 800, 100, PDF_SEPARATORS),
]

QUESTIONS = [
    "Сколько инъекций инсулина необходимо в день?",
    "Что такое гипогликемия?",
]


def load_pages(pdf_path: Path) -> list:
    return PyPDFLoader(str(pdf_path)).load()


def preview(text: str, width: int = 120) -> str:
    cleaned = " ".join(text.split())
    return textwrap.shorten(cleaned, width=width, placeholder="…")


async def run_profile(
    config: Config,
    profile: ChunkProfile,
    pages: list,
) -> None:
    print(f"\n{'=' * 60}")
    print(f"Профиль: {profile.name}")
    print(
        f"  chunk_size={profile.chunk_size} "
        f"overlap={profile.chunk_overlap} "
        f"separators={'pdf' if profile.separators else 'default'}",
    )

    chunks = split_documents(
        pages,
        chunk_size=profile.chunk_size,
        chunk_overlap=profile.chunk_overlap,
        separators=profile.separators,
    )
    avg_len = sum(len(c.page_content) for c in chunks) // max(len(chunks), 1)
    print(f"  chunks={len(chunks)} avg_len={avg_len} chars")

    # Индекс строим через подкласс Indexer с заранее нарезанными chunks.

    from nika.services.indexer import Indexer

    class _ProfileIndexer(Indexer):
        def load_chunks(self):  # type: ignore[override]
            return len(pages), chunks

    indexer = _ProfileIndexer(config)
    await indexer.aindex()
    rag = RagService(config, indexer)

    for question in QUESTIONS:
        docs = indexer.as_retriever().invoke(question)
        print(f"\n  Q: {question}")
        print(f"  retrieved {len(docs)} docs:")
        for i, doc in enumerate(docs, 1):
            print(f"    [{i}] {preview(doc.page_content)}")

        result = await rag.aretrieve(question)
        print(f"  retrieved: {len(result)} docs, top: {preview(result[0].page_content, 200) if result else 'none'}")


async def main() -> None:
    config = Config.from_env()
    pdf_path = Path(config.data_pdf)
    if not pdf_path.is_file():
        msg = f"PDF not found: {pdf_path}"
        raise FileNotFoundError(msg)

    pages = load_pages(pdf_path)
    print(f"PDF: {pdf_path} pages={len(pages)}")

    for profile in PROFILES:
        await run_profile(config, profile, pages)


if __name__ == "__main__":
    asyncio.run(main())
