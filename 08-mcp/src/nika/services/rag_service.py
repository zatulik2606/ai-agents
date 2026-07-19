import asyncio
import logging
from typing import cast

from langchain_core.documents import Document

from nika.config import Config
from nika.services.hybrid_retriever import HybridRetriever
from nika.services.indexer import Indexer
from nika.services.reranker import Reranker

logger = logging.getLogger(__name__)


def format_sources(documents: list[Document]) -> str | None:
    if not documents:
        return None

    sources_by_file: dict[str, list[str]] = {}
    for doc in documents:
        source = doc.metadata.get("source", "Unknown")
        source_path = source if source.startswith("@") else f"@{source}"
        page = doc.metadata.get("page")
        if source_path not in sources_by_file:
            sources_by_file[source_path] = []
        if page is not None and page != "N/A":
            sources_by_file[source_path].append(str(page))

    parts: list[str] = []
    for source_path, pages in sources_by_file.items():
        if pages:
            pages_str = ", ".join(
                sorted(
                    set(pages),
                    key=lambda value: int(value) if value.isdigit() else 0,
                ),
            )
            parts.append(f"{source_path} (стр. {pages_str})")
        else:
            parts.append(source_path)

    return "📚 Источники: " + ", ".join(parts)


class RagService:
    def __init__(self, config: Config, indexer: Indexer) -> None:
        self._config = config
        self._indexer = indexer
        self._reranker: Reranker | None = None
        if config.rag_retrieval_mode == "hybrid_rerank":
            self._reranker = Reranker(
                config.model_crossencoder,
                top_k=config.reranker_k,
            )

    def retrieve(self, query: str) -> list[Document]:
        mode = self._config.rag_retrieval_mode
        if mode == "semantic":
            docs = cast(
                list[Document],
                self._indexer.as_semantic_retriever().invoke(query),
            )
        elif mode == "hybrid":
            docs = self._hybrid_retriever(self._config.hybrid_retriever_k).invoke(
                query,
            )
        elif mode == "hybrid_rerank":
            if self._reranker is None:
                msg = "Reranker is not initialized"
                raise RuntimeError(msg)
            candidates = self._hybrid_retriever(
                self._config.reranker_fetch_k,
            ).invoke(query)
            docs = self._reranker.rerank(query, candidates)
        else:
            msg = f"Unknown RAG_RETRIEVAL_MODE: {mode}"
            raise ValueError(msg)

        logger.info(
            "RAG retrieved: mode=%s query=%r docs=%d",
            mode,
            query,
            len(docs),
        )
        return docs

    async def aretrieve(self, query: str) -> list[Document]:
        return await asyncio.to_thread(self.retrieve, query)

    def _hybrid_retriever(self, top_k: int) -> HybridRetriever:
        return HybridRetriever(
            self._indexer.as_semantic_retriever(),
            self._indexer.as_bm25_retriever(),
            top_k=top_k,
        )
