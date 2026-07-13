"""Проверка hybrid retrieval: индексация, BM25, RRF, query transform."""

from __future__ import annotations

import asyncio
import logging
import sys

from langchain_core.messages import AIMessage, HumanMessage

from nika.config import Config
from nika.services.hybrid_retriever import HybridRetriever
from nika.services.indexer import Indexer
from nika.services.rag_service import RagService

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("verify_hybrid_rag")

KEYWORD_QUESTION = "Сколько инъекций инсулина необходимо в день?"
FOLLOWUP_QUESTION = "А что насчёт этого?"
HISTORY_TOPIC = "гипогликемия"


def _marker_hit(text: str, markers: list[str]) -> list[str]:
    lowered = text.lower()
    return [m for m in markers if m.lower() in lowered]


def _preview(doc_text: str, width: int = 100) -> str:
    return " ".join(doc_text.split())[:width]


async def main() -> int:
    config = Config.from_env()
    print("=== Config ===")
    print(f"  RAG_RETRIEVAL_MODE={config.rag_retrieval_mode}")
    print(f"  EMBEDDING_PROVIDER={config.embedding_provider}")
    print(f"  MODEL_EMBEDDING={config.model_embedding}")
    print(f"  semantic_k={config.semantic_retriever_k} bm25_k={config.bm25_retriever_k}")
    print(f"  hybrid_k={config.hybrid_retriever_k}")
    print(f"  MODEL_RAG={config.model_rag}")

    indexer = Indexer(config)
    print("\n=== Indexing ===")
    count = await indexer.aindex()
    print(f"  chunks={count}")
    if count == 0:
        print("FAIL: index empty")
        return 1

    semantic = indexer.as_semantic_retriever()
    bm25 = indexer.as_bm25_retriever()
    hybrid = HybridRetriever(semantic, bm25, top_k=config.hybrid_retriever_k)

    print("\n=== Retrieval: инъекции ===")
    query = "инъекции инсулина"
    sem_docs = semantic.invoke(query)
    bm25_docs = bm25.invoke(query)
    hyb_docs = hybrid.invoke(query)

    injection_markers = ["инъекц", "укол", "введен"]
    for label, docs in [("semantic", sem_docs), ("bm25", bm25_docs), ("hybrid", hyb_docs)]:
        hits = [_marker_hit(d.page_content, injection_markers) for d in docs]
        matched = sum(1 for h in hits if h)
        print(f"  {label}: docs={len(docs)} with_injection_markers={matched}")
        if docs:
            print(f"    top: {_preview(docs[0].page_content)}")

    bm25_has = any(_marker_hit(d.page_content, injection_markers) for d in bm25_docs)
    hybrid_has = any(_marker_hit(d.page_content, injection_markers) for d in hyb_docs)
    if not bm25_has:
        print("WARN: BM25 did not return injection-related chunk")
    if not hybrid_has:
        print("FAIL: hybrid did not return injection-related chunk")
        return 1

    print("\n=== Query transform (follow-up) ===")
    rag = RagService(config, indexer)
    history = [
        HumanMessage(content="Что такое гипогликемия?"),
        AIMessage(content="Гипогликемия — снижение сахара в крови ниже нормы."),
    ]
    transformed = await rag.atransform_query(FOLLOWUP_QUESTION, history)
    print(f"  original={FOLLOWUP_QUESTION!r}")
    print(f"  transformed={transformed!r}")
    if HISTORY_TOPIC not in transformed.lower():
        print(f"WARN: transformed query may miss topic {HISTORY_TOPIC!r}")

    print("\n=== Full RAG answer (keyword question) ===")
    result = await rag.aanswer(KEYWORD_QUESTION, [])
    print(f"  answer_len={len(result.answer)} docs={len(result.documents)}")
    print(f"  answer_preview: {_preview(result.answer, 200)}")
    ctx_hits = _marker_hit("\n".join(d.page_content for d in result.documents), injection_markers)
    print(f"  context_markers={ctx_hits or 'none'}")

    print("\n=== PASS ===")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
