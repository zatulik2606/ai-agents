import asyncio
import logging
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from nika.config import Config

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


class Indexer:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._vector_store: InMemoryVectorStore | None = None
        self._chunk_count = 0

    @property
    def chunk_count(self) -> int:
        return self._chunk_count

    def load_chunks(self) -> tuple[int, list[Document]]:
        pdf_path = Path(self._config.data_pdf)
        if not pdf_path.is_file():
            msg = f"PDF not found: {pdf_path}"
            raise FileNotFoundError(msg)

        pages = PyPDFLoader(str(pdf_path)).load()
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )
        chunks = splitter.split_documents(pages)
        logger.info(
            "PDF loaded: path=%s pages=%d chunks=%d",
            pdf_path,
            len(pages),
            len(chunks),
        )
        return len(pages), chunks

    def index(self) -> int:
        _, chunks = self.load_chunks()
        if not chunks:
            self._vector_store = None
            self._chunk_count = 0
            logger.warning("PDF produced 0 chunks, vector index not built")
            return 0

        embeddings = OpenAIEmbeddings(
            model=self._config.model_embedding,
            api_key=self._config.openai_api_key,
            base_url=self._config.openai_base_url,
        )
        self._vector_store = InMemoryVectorStore.from_documents(chunks, embeddings)
        self._chunk_count = len(chunks)
        logger.info(
            "Vector index built: chunks=%d model=%s",
            self._chunk_count,
            self._config.model_embedding,
        )
        return self._chunk_count

    def as_retriever(self) -> BaseRetriever:
        if self._vector_store is None:
            msg = "Vector index is empty. Call index() first."
            raise RuntimeError(msg)
        return self._vector_store.as_retriever(
            search_kwargs={"k": self._config.retriever_k},
        )

    async def aload_chunks(self) -> tuple[int, list[Document]]:
        return await asyncio.to_thread(self.load_chunks)

    async def aindex(self) -> int:
        return await asyncio.to_thread(self.index)
