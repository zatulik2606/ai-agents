import logging

from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class Reranker:
    def __init__(self, model_name: str, *, top_k: int) -> None:
        from sentence_transformers import CrossEncoder

        self._model = CrossEncoder(model_name)
        self._top_k = top_k
        self._model_name = model_name

    def rerank(self, query: str, documents: list[Document]) -> list[Document]:
        if not documents:
            return []

        pairs = [[query, document.page_content] for document in documents]
        scores = self._model.predict(pairs)
        ranked = sorted(
            zip(scores, documents, strict=True),
            key=lambda item: float(item[0]),
            reverse=True,
        )
        result = [document for _, document in ranked[: self._top_k]]
        logger.info(
            "Reranker: model=%s fetch=%d top_k=%d",
            self._model_name,
            len(documents),
            len(result),
        )
        return result
