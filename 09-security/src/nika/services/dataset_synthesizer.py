import argparse
import json
import logging
import random
import re
import sys
from pathlib import Path
from typing import Any, TypedDict

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langsmith import Client

from nika.config import Config
from nika.services.indexer import split_documents

logger = logging.getLogger(__name__)

DEFAULT_DATASET_PATH = "datasets/05-rag-qa-dataset.json"
DEFAULT_SAMPLES_PER_FILE = 2
MIN_CHUNK_LENGTH = 100
MEALS_JSON = "meals.json"
JSON_QA_GLOB = "*.json"
DIABETES_JSON_GLOB = "diabetes_*.json"

SYNTHESIS_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """\
Ты эксперт по созданию вопросно-ответных пар для оценки RAG систем.
На основе предоставленного текста создай 1 реалистичный вопрос на русском языке
и краткий точный ответ строго по тексту.

Верни ТОЛЬКО валидный JSON:
{{
  "qa_pairs": [
    {{"question": "...", "answer": "..."}}
  ]
}}""",
        ),
        ("human", "Текст:\n{chunk_text}"),
    ],
)


class QAMetadata(TypedDict, total=False):
    source: str
    page: int | None
    type: str
    title: str
    category: str
    url: str


class QAPair(TypedDict):
    question: str
    ground_truth: str
    contexts: list[str]
    metadata: QAMetadata


def data_dir_from_config(config: Config) -> Path:
    return Path(config.data_pdf).parent


def load_and_sample_pdf_chunks(
    data_dir: Path,
    *,
    samples_per_file: int,
    config: Config,
) -> list[Document]:
    pdf_files = sorted(data_dir.glob("*.pdf"))
    if not pdf_files:
        logger.warning("No PDF files found in %s", data_dir)
        return []

    logger.info("Found %d PDF files", len(pdf_files))
    sampled_chunks: list[Document] = []

    for pdf_file in pdf_files:
        pages = PyPDFLoader(str(pdf_file)).load()
        chunks = split_documents(
            pages,
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=config.chunk_separators,
        )
        if not chunks:
            logger.warning("No chunks created from %s", pdf_file.name)
            continue

        num_samples = min(samples_per_file, len(chunks))
        step = max(len(chunks) // num_samples, 1)
        selected = [chunks[index * step] for index in range(num_samples)]
        sampled_chunks.extend(selected)
        logger.info("Sampled %d chunks from %s", len(selected), pdf_file.name)

    return sampled_chunks


def load_and_sample_json_chunks(
    data_dir: Path,
    *,
    samples_per_file: int,
) -> list[Document]:
    json_files = sorted(data_dir.glob(DIABETES_JSON_GLOB))
    if not json_files:
        logger.info("No %s files found in %s", DIABETES_JSON_GLOB, data_dir)
        return []

    chunks: list[Document] = []
    for json_file in json_files:
        raw = json.loads(json_file.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            continue

        entries = [item for item in raw if isinstance(item, dict)]
        if not entries:
            continue

        num_samples = min(samples_per_file, len(entries))
        selected = random.sample(entries, num_samples)
        for index, item in enumerate(selected):
            full_text = item.get("full_text")
            if not isinstance(full_text, str):
                continue
            if len(full_text.strip()) < MIN_CHUNK_LENGTH:
                continue
            title = item.get("title", "")
            chunks.append(
                Document(
                    page_content=full_text.strip(),
                    metadata={
                        "source": str(json_file),
                        "page": None,
                        "title": title if isinstance(title, str) else "",
                        "entry_index": index,
                    },
                ),
            )
        logger.info("Sampled %d entries from %s", len(selected), json_file.name)

    return chunks


def load_json_qa_pairs(
    data_dir: Path,
    *,
    samples_per_file: int,
) -> list[QAPair]:
    json_files = sorted(
        path for path in data_dir.glob(JSON_QA_GLOB) if path.name != MEALS_JSON
    )
    if not json_files:
        logger.warning("No JSON files found in %s", data_dir)
        return []

    qa_pairs: list[QAPair] = []
    for json_file in json_files:
        raw = json.loads(json_file.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            continue

        ready_items = [
            item
            for item in raw
            if isinstance(item, dict)
            and isinstance(item.get("question"), str)
            and isinstance(item.get("answer"), str)
            and item["question"].strip()
            and item["answer"].strip()
        ]
        if not ready_items:
            continue

        num_samples = min(samples_per_file, len(ready_items))
        selected = random.sample(ready_items, num_samples)
        for item in selected:
            qa_pairs.append(
                {
                    "question": item["question"].strip(),
                    "ground_truth": item["answer"].strip(),
                    "contexts": [
                        str(item.get("full_text", item["answer"])).strip(),
                    ],
                    "metadata": {
                        "source": json_file.name,
                        "page": None,
                        "type": "from_json",
                        "category": str(item.get("category", "unknown")),
                        "url": str(item.get("url", "")),
                    },
                },
            )
        logger.info("Loaded %d ready Q&A pairs from %s", len(selected), json_file.name)

    return qa_pairs


def _parse_llm_json(content: str) -> dict[str, Any]:
    text = content.strip()
    if "```json" in text:
        text = text.split("```json", maxsplit=1)[1].split("```", maxsplit=1)[0].strip()
    elif "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1].strip()
            if text.startswith("json"):
                text = text[4:].strip()

    if not text.startswith("{"):
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            text = match.group(0)

    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        msg = "LLM JSON root must be an object"
        raise TypeError(msg)
    return parsed


def synthesize_qa_pairs(
    chunks: list[Document],
    *,
    config: Config,
) -> list[QAPair]:
    if not chunks:
        return []

    llm = ChatOpenAI(
        model=config.model_rag,
        api_key=config.openai_api_key,
        base_url=config.openai_base_url,
        temperature=0.7,
    )

    qa_pairs: list[QAPair] = []
    for index, chunk in enumerate(chunks):
        if len(chunk.page_content.strip()) < MIN_CHUNK_LENGTH:
            logger.warning("Chunk %d too short, skipping", index)
            continue

        try:
            response = llm.invoke(
                SYNTHESIS_PROMPT.format_messages(
                    chunk_text=chunk.page_content[:2000],
                ),
            )
            content = response.content
            if not isinstance(content, str):
                msg = "LLM synthesis returned non-string content"
                raise TypeError(msg)

            data = _parse_llm_json(content)
            for qa in data.get("qa_pairs", []):
                if not isinstance(qa, dict):
                    continue
                question = qa.get("question")
                answer = qa.get("answer")
                if not isinstance(question, str) or not isinstance(answer, str):
                    continue
                if not question.strip() or not answer.strip():
                    continue
                qa_pairs.append(
                    {
                        "question": question.strip(),
                        "ground_truth": answer.strip(),
                        "contexts": [chunk.page_content],
                        "metadata": {
                            "source": str(chunk.metadata.get("source", "unknown")),
                            "page": chunk.metadata.get("page"),
                            "type": "synthesized",
                            "title": str(chunk.metadata.get("title", "")),
                        },
                    },
                )

            if (index + 1) % 5 == 0:
                logger.info(
                    "Processed %d/%d chunks, created %d Q&A pairs",
                    index + 1,
                    len(chunks),
                    len(qa_pairs),
                )
        except (json.JSONDecodeError, TypeError, ValueError):
            logger.exception("Failed to synthesize Q&A for chunk %d", index)
            continue

    logger.info("Synthesized %d Q&A pairs from %d chunks", len(qa_pairs), len(chunks))
    return qa_pairs


def create_dataset(
    config: Config,
    *,
    samples_per_file: int = DEFAULT_SAMPLES_PER_FILE,
) -> list[QAPair]:
    data_dir = data_dir_from_config(config)
    logger.info("Creating dataset from %s", data_dir)

    pdf_chunks = load_and_sample_pdf_chunks(
        data_dir,
        samples_per_file=samples_per_file,
        config=config,
    )
    json_chunks = load_and_sample_json_chunks(
        data_dir,
        samples_per_file=samples_per_file,
    )
    synthesized = synthesize_qa_pairs(pdf_chunks + json_chunks, config=config)

    json_qa_pairs = load_json_qa_pairs(data_dir, samples_per_file=samples_per_file)
    all_pairs = synthesized + json_qa_pairs

    logger.info(
        "Dataset created: synthesized=%d from_json=%d total=%d",
        len(synthesized),
        len(json_qa_pairs),
        len(all_pairs),
    )
    return all_pairs


def save_dataset(qa_pairs: list[QAPair], filepath: str | Path) -> None:
    output_path = Path(filepath)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(qa_pairs, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Dataset saved to %s (%d examples)", output_path, len(qa_pairs))


def upload_to_langsmith(
    dataset_path: str | Path,
    dataset_name: str,
    *,
    api_key: str,
) -> None:
    if not api_key:
        msg = "LANGSMITH_API_KEY not set. Cannot upload dataset."
        raise ValueError(msg)

    path = Path(dataset_path)
    if not path.is_file():
        msg = f"Dataset file not found: {path}"
        raise FileNotFoundError(msg)

    qa_pairs = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(qa_pairs, list):
        msg = "Dataset JSON root must be a list"
        raise ValueError(msg)

    client = Client(api_key=api_key)
    existing = list(client.list_datasets(dataset_name=dataset_name))
    if existing:
        logger.info(
            "Dataset '%s' already exists in LangSmith (id=%s), skipping upload",
            dataset_name,
            existing[0].id,
        )
        return

    dataset = client.create_dataset(
        dataset_name=dataset_name,
        description="RAG evaluation dataset from PDF/JSON synthesis",
    )
    logger.info("Created dataset '%s' (id=%s)", dataset_name, dataset.id)

    inputs = [{"question": qa["question"]} for qa in qa_pairs]
    outputs = [{"answer": qa["ground_truth"]} for qa in qa_pairs]
    metadata = [qa.get("metadata", {}) for qa in qa_pairs]

    client.create_examples(
        dataset_id=dataset.id,
        inputs=inputs,
        outputs=outputs,
        metadata=metadata,
    )
    logger.info("Uploaded %d examples to LangSmith", len(qa_pairs))


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="RAG evaluation dataset synthesizer")
    parser.add_argument("--create", action="store_true", help="Create dataset locally")
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload dataset to LangSmith",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=DEFAULT_SAMPLES_PER_FILE,
        help="Samples per file",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_DATASET_PATH,
        help="Output JSON path",
    )
    args = parser.parse_args(argv)

    if not args.create and not args.upload:
        parser.print_help()
        logger.error("Specify at least one action: --create or --upload")
        return 1

    config = Config.from_env()
    output_path = args.output

    if args.create:
        qa_pairs = create_dataset(config, samples_per_file=args.samples)
        save_dataset(qa_pairs, output_path)

    if args.upload:
        upload_to_langsmith(
            output_path,
            config.langsmith_dataset,
            api_key=config.langsmith_api_key,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
