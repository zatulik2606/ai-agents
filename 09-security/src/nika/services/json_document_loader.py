import json
import logging
from pathlib import Path

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

JSON_GLOB = "diabetes_*.json"


def load_json_documents(json_file_path: str) -> list[Document]:
    json_path = Path(json_file_path)
    if not json_path.exists():
        logger.warning("JSON file %s does not exist", json_file_path)
        return []

    raw = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        msg = f"JSON root must be a list: {json_path}"
        raise ValueError(msg)

    documents: list[Document] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        full_text = item.get("full_text")
        if not isinstance(full_text, str) or not full_text.strip():
            continue
        title = item.get("title", "")
        documents.append(
            Document(
                page_content=full_text.strip(),
                metadata={
                    "source": str(json_path),
                    "title": title if isinstance(title, str) else "",
                    "entry_index": index,
                },
            ),
        )

    logger.info("Loaded %d entries from JSON: %s", len(documents), json_path.name)
    return documents


def load_all_json_documents(data_dir: str) -> list[Document]:
    directory = Path(data_dir)
    if not directory.is_dir():
        logger.warning("Data directory does not exist: %s", data_dir)
        return []

    documents: list[Document] = []
    for json_path in sorted(directory.glob(JSON_GLOB)):
        documents.extend(load_json_documents(str(json_path)))
    logger.info(
        "Loaded %d JSON documents from %s (%s)",
        len(documents),
        directory,
        JSON_GLOB,
    )
    return documents
