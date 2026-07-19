import json
import logging
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.tools import StructuredTool

from nika.services.rag_service import RagService

logger = logging.getLogger(__name__)

RAG_SEARCH_DESCRIPTION = """\
Поиск по медицинскому руководству для детей с сахарным диабетом 1 типа.

Вызывай, когда пользователь задаёт СПРАВОЧНЫЙ вопрос о диабете, инсулине, питании,
осложнениях, гипо/гипергликемии и т.п. — и ответ нужно опирать на руководство.

Не вызывай для учёта еды, расчёта доз, приветствий («Привет!»),
благодарностей («Спасибо за помощь»), small talk («Как дела?»)
и любого разговора без фактов из базы.

Args:
    query: Короткая самодостаточная поисковая фраза на русском.
           Для follow-up перефразируй с учётом истории
           («гипогликемия симптомы лечение»)."""


def document_to_source(doc: Document) -> dict[str, object]:
    raw_source = str(doc.metadata.get("source", "Unknown"))
    source_name = Path(raw_source).name
    item: dict[str, object] = {
        "source": source_name,
        "page_content": doc.page_content,
    }
    page = doc.metadata.get("page")
    if page is not None and page != "N/A":
        item["page"] = page
    return item


def sources_to_documents(sources: list[dict[str, object]]) -> list[Document]:
    documents: list[Document] = []
    for source in sources:
        page_content = source.get("page_content")
        if not isinstance(page_content, str):
            continue
        metadata: dict[str, object] = {
            "source": source.get("source", "Unknown"),
        }
        page = source.get("page")
        if page is not None:
            metadata["page"] = page
        documents.append(Document(page_content=page_content, metadata=metadata))
    return documents


def create_rag_search_tool(rag: RagService) -> StructuredTool:
    def rag_search(query: str) -> str:
        """Поиск фрагментов руководства по справочному вопросу."""
        documents = rag.retrieve(query)
        payload = {
            "sources": [document_to_source(doc) for doc in documents],
        }
        logger.info("rag_search: query=%r sources=%d", query, len(documents))
        return json.dumps(payload, ensure_ascii=False)

    return StructuredTool.from_function(
        func=rag_search,
        name="rag_search",
        description=RAG_SEARCH_DESCRIPTION,
    )
