import logging
from typing import cast

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

logger = logging.getLogger(__name__)

RRF_K = 60


def _doc_key(document: Document) -> str:
    source = document.metadata.get("source", "")
    page = document.metadata.get("page", "")
    return f"{source}|{page}|{document.page_content}"


def reciprocal_rank_fusion(
    ranked_lists: list[list[Document]],
    *,
    top_k: int,
    rrf_k: int = RRF_K,
) -> list[Document]:
    scores: dict[str, float] = {}
    documents_by_key: dict[str, Document] = {}

    for ranked in ranked_lists:
        for rank, document in enumerate(ranked, start=1):
            key = _doc_key(document)
            documents_by_key[key] = document
            scores[key] = scores.get(key, 0.0) + 1.0 / (rrf_k + rank)

    sorted_keys = sorted(scores, key=scores.get, reverse=True)
    return [documents_by_key[key] for key in sorted_keys[:top_k]]


class HybridRetriever:
    def __init__(
        self,
        semantic_retriever: BaseRetriever,
        bm25_retriever: BaseRetriever,
        *,
        top_k: int,
    ) -> None:
        self._semantic_retriever = semantic_retriever
        self._bm25_retriever = bm25_retriever
        self._top_k = top_k

    def invoke(self, query: str) -> list[Document]:
        semantic_docs = cast(
            list[Document],
            self._semantic_retriever.invoke(query),
        )
        bm25_docs = cast(
            list[Document],
            self._bm25_retriever.invoke(query),
        )
        fused = reciprocal_rank_fusion(
            [semantic_docs, bm25_docs],
            top_k=self._top_k,
        )
        logger.info(
            "Hybrid retrieval: query=%r semantic=%d bm25=%d fused=%d",
            query,
            len(semantic_docs),
            len(bm25_docs),
            len(fused),
        )
        return fused
