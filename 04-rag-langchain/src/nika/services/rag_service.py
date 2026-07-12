import asyncio
import logging
from typing import cast

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from nika.config import Config
from nika.services.indexer import Indexer
from nika.services.meal_log import DISCLAIMER

logger = logging.getLogger(__name__)

QUERY_TRANSFORM_PROMPT = """\
Тебе передана история диалога в сообщениях выше. Последний вопрос пользователя \
может ссылаться на контекст («это», «она», «а что насчёт этого?»).
Сформулируй один короткий самодостаточный поисковый запрос на русском \
для семантического поиска по базе знаний.
Верни ТОЛЬКО текст запроса, без пояснений и без ответа на вопрос."""

RAG_ANSWER_PROMPT = """\
{system_prompt}

Ответь на вопрос пользователя, опираясь ТОЛЬКО на контекст из руководства ниже.
Если в контексте нет ответа — честно скажи, что в руководстве этого нет.
Не выдумывай факты. Пиши от первого лица, женский род, на русском языке.
В конце добавь дисклеймер: {disclaimer}

Контекст из руководства:
{context}"""


class RagService:
    def __init__(self, config: Config, indexer: Indexer) -> None:
        self._config = config
        self._indexer = indexer
        self._query_transform_chain = self._build_query_transform_chain()
        self._answer_chain = self._build_answer_chain()

    def rag_query_transform_chain(
        self,
        question: str,
        chat_history: list[BaseMessage],
    ) -> str:
        return self.answer(question, chat_history)

    def answer(self, question: str, chat_history: list[BaseMessage]) -> str:
        search_query = self.transform_query(question, chat_history)
        docs = self._retrieve(search_query)
        context = self._format_context(docs)
        answer = self._answer_chain.invoke(
            {
                "input": question,
                "chat_history": chat_history,
                "context": context,
                "system_prompt": self._config.system_prompt,
                "disclaimer": DISCLAIMER,
            },
        )
        if not isinstance(answer, str):
            msg = "RAG answer returned non-string result"
            raise TypeError(msg)
        logger.info(
            "RAG answer: question=%r chunks=%d answer_len=%d",
            question,
            len(docs),
            len(answer),
        )
        return answer

    async def aanswer(self, question: str, chat_history: list[BaseMessage]) -> str:
        return await asyncio.to_thread(self.answer, question, chat_history)

    def transform_query(
        self,
        question: str,
        chat_history: list[BaseMessage],
    ) -> str:
        transformed = self._query_transform_chain.invoke(
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

    def _retrieve(self, search_query: str) -> list[Document]:
        docs = cast(
            list[Document],
            self._indexer.as_retriever().invoke(search_query),
        )
        logger.info("RAG retrieved: query=%r docs=%d", search_query, len(docs))
        return docs

    @staticmethod
    def _format_context(docs: list[Document]) -> str:
        if not docs:
            return "Контекст не найден."
        return "\n\n---\n\n".join(doc.page_content for doc in docs)

    def _build_query_transform_chain(
        self,
    ) -> Runnable[dict[str, object], str]:
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", QUERY_TRANSFORM_PROMPT),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ],
        )
        llm = self._chat_llm()
        return prompt | llm | StrOutputParser()

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
            model=self._config.model_text,
            api_key=self._config.openrouter_api_key,
            base_url=self._config.llm_base_url,
            temperature=0,
        )
