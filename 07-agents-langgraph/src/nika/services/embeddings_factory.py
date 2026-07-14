import logging

from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from nika.config import Config

logger = logging.getLogger(__name__)


def create_embeddings(
    config: Config,
    *,
    provider: str | None = None,
    model: str | None = None,
) -> Embeddings:
    resolved_provider = provider or config.embedding_provider
    resolved_model = model or config.model_embedding

    if resolved_provider == "huggingface":
        from langchain_community.embeddings import HuggingFaceEmbeddings

        logger.info(
            "Embeddings: provider=huggingface model=%s device=%s",
            resolved_model,
            config.huggingface_device,
        )
        return HuggingFaceEmbeddings(
            model_name=resolved_model,
            model_kwargs={"device": config.huggingface_device},
        )

    logger.info("Embeddings: provider=openai model=%s", resolved_model)
    return OpenAIEmbeddings(
        model=resolved_model,
        api_key=config.openai_api_key,
        base_url=config.openai_base_url,
    )


def create_ragas_embeddings(config: Config) -> Embeddings:
    return create_embeddings(
        config,
        provider=config.ragas_embedding_provider,
        model=config.ragas_embedding_model,
    )
