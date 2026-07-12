import asyncio
import logging
from pathlib import Path
from typing import cast

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from nika.config import Config
from nika.services.json_document_loader import load_all_json_documents

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
PDF_SEPARATORS = ["\n\n\n", "\n\n", "\n", ". ", " ", ""]


def create_embeddings(config: Config) -> Embeddings:
    if config.embedding_provider == "ollama":
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(
            model=config.model_embedding,
            base_url=config.ollama_embedding_base_url,
        )
    return OpenAIEmbeddings(
        model=config.model_embedding,
        api_key=config.openai_api_key,
        base_url=config.openai_base_url,
    )


def split_documents(
    pages: list[Document],
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    separators: list[str] | None = None,
) -> list[Document]:
    kwargs: dict[str, object] = {
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
    }
    if separators is not None:
        kwargs["separators"] = separators
        kwargs["keep_separator"] = True
    text_splitter = RecursiveCharacterTextSplitter(**kwargs)
    chunks = text_splitter.split_documents(pages)
    logger.info(
        "Split into %d chunks (size=%d overlap=%d separators=%s)",
        len(chunks),
        chunk_size,
        chunk_overlap,
        "custom" if separators else "default",
    )
    return cast(list[Document], chunks)


class Indexer:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._vector_store: InMemoryVectorStore | None = None
        self._chunk_count = 0

    @property
    def chunk_count(self) -> int:
        return self._chunk_count

    def load_pdf_chunks(self) -> tuple[int, list[Document]]:
        pdf_path = Path(self._config.data_pdf)
        if not pdf_path.is_file():
            msg = f"PDF not found: {pdf_path}"
            raise FileNotFoundError(msg)

        pages = PyPDFLoader(str(pdf_path)).load()
        chunks = split_documents(
            pages,
            chunk_size=self._config.chunk_size,
            chunk_overlap=self._config.chunk_overlap,
            separators=self._config.chunk_separators,
        )
        logger.info(
            "PDF loaded: path=%s pages=%d chunks=%d",
            pdf_path,
            len(pages),
            len(chunks),
        )
        return len(pages), chunks

    def load_chunks(self) -> tuple[int, list[Document]]:
        return self.load_pdf_chunks()

    def reindex_all(self) -> int:
        _, pdf_chunks = self.load_pdf_chunks()
        data_dir = str(Path(self._config.data_pdf).parent)
        json_documents = load_all_json_documents(data_dir)
        all_documents = pdf_chunks + json_documents
        if not all_documents:
            self._vector_store = None
            self._chunk_count = 0
            logger.warning("No PDF chunks or JSON documents, vector index not built")
            return 0

        logger.info(
            "Total documents: %d (PDF chunks: %d, JSON: %d)",
            len(all_documents),
            len(pdf_chunks),
            len(json_documents),
        )

        embeddings = create_embeddings(self._config)
        self._vector_store = InMemoryVectorStore.from_documents(
            all_documents,
            embeddings,
        )
        self._chunk_count = len(all_documents)
        logger.info(
            "Vector index built: documents=%d provider=%s model=%s",
            self._chunk_count,
            self._config.embedding_provider,
            self._config.model_embedding,
        )
        return self._chunk_count

    def index(self) -> int:
        return self.reindex_all()

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
