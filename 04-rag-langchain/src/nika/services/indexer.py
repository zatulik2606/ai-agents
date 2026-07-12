import asyncio
import logging
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from nika.config import Config

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


class Indexer:
    def __init__(self, config: Config) -> None:
        self._config = config

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

    async def aload_chunks(self) -> tuple[int, list[Document]]:
        return await asyncio.to_thread(self.load_chunks)
