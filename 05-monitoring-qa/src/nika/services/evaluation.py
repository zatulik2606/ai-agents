import logging
import math
import sys
import types
from typing import Any, TypedDict

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langsmith import Client

from nika.config import Config
from nika.services.rag_service import RagService

logger = logging.getLogger(__name__)

METRIC_DESCRIPTIONS: dict[str, str] = {
    "faithfulness": "Обоснованность (нет галлюцинаций)",
    "answer_relevancy": "Релевантность ответа",
    "answer_correctness": "Правильность ответа",
    "answer_similarity": "Похожесть на эталон",
    "context_recall": "Полнота контекста",
    "context_precision": "Точность поиска",
}


class EvaluationResult(TypedDict):
    dataset_name: str
    num_examples: int
    metrics: dict[str, float]


_ragas_metrics: list[Any] | None = None
_ragas_run_config: Any = None


def _ensure_ragas_importable() -> None:
    module_name = "langchain_community.chat_models.vertexai"
    if module_name in sys.modules:
        return
    module = types.ModuleType(module_name)
    module.ChatVertexAI = type("ChatVertexAI", (), {})
    sys.modules[module_name] = module


def _import_ragas() -> tuple[Any, ...]:
    _ensure_ragas_importable()
    from ragas import evaluate
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import (
        AnswerCorrectness,
        AnswerRelevancy,
        AnswerSimilarity,
        ContextPrecision,
        ContextRecall,
        Faithfulness,
    )
    from ragas.metrics.base import MetricWithEmbeddings, MetricWithLLM
    from ragas.run_config import RunConfig

    from datasets import Dataset

    return (
        Dataset,
        evaluate,
        LangchainEmbeddingsWrapper,
        LangchainLLMWrapper,
        Faithfulness,
        AnswerRelevancy,
        AnswerCorrectness,
        AnswerSimilarity,
        ContextRecall,
        ContextPrecision,
        MetricWithLLM,
        MetricWithEmbeddings,
        RunConfig,
    )


def init_ragas_metrics(config: Config) -> tuple[list[Any], Any]:
    global _ragas_metrics, _ragas_run_config

    if _ragas_metrics is not None and _ragas_run_config is not None:
        return _ragas_metrics, _ragas_run_config

    (
        _dataset,
        _evaluate,
        LangchainEmbeddingsWrapper,
        LangchainLLMWrapper,
        Faithfulness,
        AnswerRelevancy,
        AnswerCorrectness,
        AnswerSimilarity,
        ContextRecall,
        ContextPrecision,
        MetricWithLLM,
        MetricWithEmbeddings,
        RunConfig,
    ) = _import_ragas()

    logger.info("Initializing RAGAS metrics...")

    langchain_llm = ChatOpenAI(
        model=config.ragas_llm_model,
        api_key=config.openai_api_key,
        base_url=config.openai_base_url,
        temperature=0,
    )
    langchain_embeddings = OpenAIEmbeddings(
        model=config.ragas_embedding_model,
        api_key=config.openai_api_key,
        base_url=config.openai_base_url,
    )

    metrics = [
        Faithfulness(),
        AnswerRelevancy(strictness=1),
        AnswerCorrectness(),
        AnswerSimilarity(),
        ContextRecall(),
        ContextPrecision(),
    ]

    ragas_llm = LangchainLLMWrapper(langchain_llm)
    ragas_embeddings = LangchainEmbeddingsWrapper(langchain_embeddings)

    for metric in metrics:
        if isinstance(metric, MetricWithLLM):
            metric.llm = ragas_llm
        if isinstance(metric, MetricWithEmbeddings):
            metric.embeddings = ragas_embeddings
        metric.init(RunConfig())

    run_config = RunConfig(max_workers=4, max_wait=180, max_retries=3)
    _ragas_metrics = metrics
    _ragas_run_config = run_config

    logger.info(
        "RAGAS metrics initialized: %s",
        ", ".join(metric.name for metric in metrics),
    )
    return _ragas_metrics, _ragas_run_config


def check_dataset_exists(dataset_name: str, *, api_key: str) -> bool:
    if not api_key:
        return False
    client = Client(api_key=api_key)
    datasets = list(client.list_datasets(dataset_name=dataset_name))
    return len(datasets) > 0


def _extract_contexts(documents: object) -> list[str]:
    if not isinstance(documents, list):
        return []

    contexts: list[str] = []
    for document in documents:
        page_content = getattr(document, "page_content", None)
        if isinstance(page_content, str):
            contexts.append(page_content)
            continue
        if isinstance(document, dict):
            content = document.get("page_content")
            if isinstance(content, str):
                contexts.append(content)
                continue
        contexts.append(str(document))
    return contexts


def _safe_score(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class EvaluationService:
    def __init__(self, config: Config, rag: RagService) -> None:
        self._config = config
        self._rag = rag

    def evaluate_dataset(
        self,
        dataset_name: str | None = None,
    ) -> EvaluationResult:
        if not self._config.langsmith_api_key:
            msg = "LANGSMITH_API_KEY not set. Cannot run evaluation."
            raise ValueError(msg)

        resolved_name = dataset_name or self._config.langsmith_dataset
        logger.info("Starting evaluation for dataset: %s", resolved_name)

        if not check_dataset_exists(
            resolved_name,
            api_key=self._config.langsmith_api_key,
        ):
            msg = f"Dataset '{resolved_name}' not found in LangSmith"
            raise ValueError(msg)

        ragas_metrics, ragas_run_config = init_ragas_metrics(self._config)
        client = Client(api_key=self._config.langsmith_api_key)

        logger.info("[1/3] Running experiment and collecting data...")

        def target(inputs: dict[str, object]) -> dict[str, object]:
            question = str(inputs.get("question", ""))
            result = self._rag.answer(question, [])
            return {
                "answer": result.answer,
                "documents": result.documents,
            }

        questions: list[str] = []
        answers: list[str] = []
        contexts_list: list[list[str]] = []
        ground_truths: list[str] = []
        run_ids: list[str] = []

        for result in client.evaluate(
            target,
            data=resolved_name,
            evaluators=[],
            experiment_prefix="rag-evaluation",
            metadata={
                "approach": "RAGAS batch evaluation + LangSmith feedback",
                "model": self._config.model_rag,
                "embedding_model": self._config.model_embedding,
            },
            blocking=False,
        ):
            run = result["run"]
            example = result["example"]

            question = str(run.inputs.get("question", ""))
            answer = str(run.outputs.get("answer", ""))
            documents = run.outputs.get("documents", [])
            contexts = _extract_contexts(documents)
            ground_truth = ""
            if example is not None and example.outputs is not None:
                ground_truth = str(example.outputs.get("answer", ""))

            questions.append(question)
            answers.append(answer)
            contexts_list.append(contexts)
            ground_truths.append(ground_truth)
            run_ids.append(str(run.id))

        logger.info("Experiment completed, collected %d examples", len(questions))

        logger.info("[2/3] Running RAGAS evaluation...")
        Dataset, evaluate, *_rest = _import_ragas()

        ragas_dataset = Dataset.from_dict(
            {
                "question": questions,
                "answer": answers,
                "contexts": contexts_list,
                "ground_truth": ground_truths,
            },
        )
        ragas_result = evaluate(
            ragas_dataset,
            metrics=ragas_metrics,
            run_config=ragas_run_config,
        )
        ragas_df = ragas_result.to_pandas()

        metrics_summary: dict[str, float] = {}
        for metric in ragas_metrics:
            if metric.name not in ragas_df.columns:
                continue
            avg_score = ragas_df[metric.name].mean()
            safe_avg = _safe_score(avg_score)
            if safe_avg is None:
                continue
            metrics_summary[metric.name] = safe_avg
            logger.info("  %s: %.3f", metric.name, safe_avg)

        logger.info("[3/3] Uploading feedback to LangSmith...")
        for index, run_id in enumerate(run_ids):
            row = ragas_df.iloc[index]
            for metric in ragas_metrics:
                if metric.name not in row:
                    continue
                score = _safe_score(row[metric.name])
                if score is None:
                    continue
                client.create_feedback(
                    run_id=run_id,
                    key=metric.name,
                    score=score,
                    comment=f"RAGAS metric: {metric.name}",
                )

        logger.info("Feedback uploaded (%d runs)", len(run_ids))
        return {
            "dataset_name": resolved_name,
            "num_examples": len(questions),
            "metrics": metrics_summary,
        }

    @staticmethod
    def format_report(result: EvaluationResult) -> str:
        lines = [
            "✅ Evaluation завершён!",
            "",
            f"📊 Датасет: {result['dataset_name']}",
            f"📝 Примеров обработано: {result['num_examples']}",
            "",
            "🎯 RAGAS метрики:",
        ]

        for metric_name, score in result["metrics"].items():
            description = METRIC_DESCRIPTIONS.get(metric_name, metric_name)
            if score >= 0.8:
                emoji = "🟢"
            elif score >= 0.6:
                emoji = "🟡"
            else:
                emoji = "🔴"
            lines.append(f"{emoji} {description}: {score:.3f}")

        lines.append("")
        lines.append("💡 Результаты загружены в LangSmith как feedback")
        return "\n".join(lines)
