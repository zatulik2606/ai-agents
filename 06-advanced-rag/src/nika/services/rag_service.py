import asyncio
import logging
from dataclasses import dataclass
from typing import cast

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable, RunnableLambda, RunnablePassthrough
from langchain_openai import ChatOpenAI

from nika.config import Config
from nika.services.hybrid_retriever import HybridRetriever
from nika.services.indexer import Indexer
from nika.services.meal_log import DISCLAIMER
from nika.services.reranker import Reranker

logger = logging.getLogger(__name__)

QUERY_TRANSFORM_PROMPT = """\
Тебе передана история диалога в сообщениях выше. Последний вопрос пользователя \
может ссылаться на контекст («это», «она», «а что насчёт этого?»).
Сформулируй один короткий самодостаточный поисковый запрос на русском \
для семантического поиска по базе знаний.
Верни ТОЛЬКО текст запроса, без пояснений и без ответа на вопрос."""

RAG_ANSWER_PROMPT = """\
Ты — Ника, ассистентка по диабету. Отвечаешь на справочный вопрос по руководству.

Правила:
- Не здоровайся и не представляйся — сразу отвечай по существу.
- Опирайся ТОЛЬКО на контекст ниже; если ответа нет — скажи честно.
- Не выдумывай факты. Женский род, русский язык.
- В конце добавь дисклеймер: {disclaimer}

Контекст из руководства:
{context}"""


@dataclass(frozen=True)
class RagAnswer:
    answer: str
    documents: list[Document]


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
        self._retrieval_chain = self._build_retrieval_chain()
        self._answer_chain = self._build_answer_chain()

    def rag_query_transform_chain(
        self,
        question: str,
        chat_history: list[BaseMessage],
    ) -> RagAnswer:
        return self.answer(question, chat_history)

    def answer(self, question: str, chat_history: list[BaseMessage]) -> RagAnswer:
        enriched = self._retrieval_chain.invoke(
            {
                "input": question,
                "chat_history": chat_history,
                "disclaimer": DISCLAIMER,
            },
        )
        documents = cast(list[Document], enriched["documents"])
        answer = self._answer_chain.invoke(enriched)
        if not isinstance(answer, str):
            msg = "RAG answer returned non-string result"
            raise TypeError(msg)
        logger.info(
            "RAG answer: mode=%s question=%r chunks=%d answer_len=%d",
            self._config.rag_retrieval_mode,
            question,
            len(documents),
            len(answer),
        )
        return RagAnswer(answer=answer, documents=documents)

    async def aanswer(
        self,
        question: str,
        chat_history: list[BaseMessage],
    ) -> RagAnswer:
        return await asyncio.to_thread(self.answer, question, chat_history)

    def transform_query(
        self,
        question: str,
        chat_history: list[BaseMessage],
    ) -> str:
        transformed = self._query_transform_chain().invoke(
            {"input": question, "chat_history": chat_history},
        )
        if not isinstance(transformed, str):
            msg = "Query transform returned non-string result"
            raise TypeError(msg)
        logger.info(
            "Query transformed: original=%r transformed=%r",
            question,
            transformed,
        )
        return transformed

    async def atransform_query(
        self,
        question: str,
        chat_history: list[BaseMessage],
    ) -> str:
        return await asyncio.to_thread(
            self.transform_query,
            question,
            chat_history,
        )

    def _retrieve_documents(self, search_query: str) -> list[Document]:
        mode = self._config.rag_retrieval_mode
        if mode == "semantic":
            docs = cast(
                list[Document],
                self._indexer.as_semantic_retriever().invoke(search_query),
            )
        elif mode == "hybrid":
            docs = self._hybrid_retriever(self._config.hybrid_retriever_k).invoke(
                search_query,
            )
        elif mode == "hybrid_rerank":
            if self._reranker is None:
                msg = "Reranker is not initialized"
                raise RuntimeError(msg)
            candidates = self._hybrid_retriever(
                self._config.reranker_fetch_k,
            ).invoke(search_query)
            docs = self._reranker.rerank(search_query, candidates)
        else:
            msg = f"Unknown RAG_RETRIEVAL_MODE: {mode}"
            raise ValueError(msg)

        logger.info(
            "RAG retrieved: mode=%s query=%r docs=%d",
            mode,
            search_query,
            len(docs),
        )
        return docs

    def _hybrid_retriever(self, top_k: int) -> HybridRetriever:
        return HybridRetriever(
            self._indexer.as_semantic_retriever(),
            self._indexer.as_bm25_retriever(),
            top_k=top_k,
        )

    def _build_retrieval_chain(
        self,
    ) -> Runnable[dict[str, object], dict[str, object]]:
        return (
            RunnablePassthrough.assign(
                search_query=self._query_transform_chain(),
            )
            | RunnableLambda(self._attach_retrieved_context)
        )

    def _attach_retrieved_context(self, inputs: dict[str, object]) -> dict[str, object]:
        search_query = inputs["search_query"]
        if not isinstance(search_query, str):
            msg = "search_query must be a string"
            raise TypeError(msg)
        documents = self._retrieve_documents(search_query)
        return {
            **inputs,
            "documents": documents,
            "context": self._format_context(documents),
        }

    @staticmethod
    def _format_context(docs: list[Document]) -> str:
        if not docs:
            return "Контекст не найден."
        return "\n\n---\n\n".join(doc.page_content for doc in docs)

    def _query_transform_chain(self) -> Runnable[dict[str, object], str]:
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", QUERY_TRANSFORM_PROMPT),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ],
        )
        return prompt | self._chat_llm() | StrOutputParser()

    def _build_answer_chain(self) -> Runnable[dict[str, object], str]:
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", RAG_ANSWER_PROMPT),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ],
        )
        return prompt | self._chat_llm() | StrOutputParser()

    def _chat_llm(self) -> ChatOpenAI:
        return ChatOpenAI(
            model=self._config.model_rag,
            api_key=self._config.openai_api_key,
            base_url=self._config.openai_base_url,
            temperature=0,
        )
