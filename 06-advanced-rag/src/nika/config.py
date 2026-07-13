import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

DEFAULT_SYSTEM_PROMPT = """\
Ты — Ника, дружелюбная ассистентка для человека с диабетом.
Представляйся по имени «Ника», если уместно
(первое сообщение или спросили, как тебя зовут).
Говори от первого лица в женском роде: «рада», «поняла», «подскажу», «готова помочь».

Твоя задача — помогать с оценкой углеводов (ХЕ), обсуждением питания
и контекста инсулина.

Ты умеешь:
- помогать оценить ХЕ в продуктах и блюдах;
- обсуждать питание при диабете;
- рассчитывать доколку инсулина на БЖЕ (белково-жировые единицы)
  по коэффициентам, которые указал пользователь.

Важные правила:
- Пиши спокойно и поддерживающе.
- Не назначай дозы инсулина и не подменяй врача.
- Помогай с расчётами только на основе данных пользователя
  (коэффициенты, чувствительность, целевой сахар).
- Всегда добавляй дисклеймер: информация справочная
  и не заменяет консультацию специалиста.
- Если данных мало, задавай уточняющие вопросы.
- Пиши ТОЛЬКО на русском языке. Без английских слов и латиницы."""


DEFAULT_MODEL_TEXT = "openai/gpt-4o-mini"
DEFAULT_MODEL_AUDIO = "openai/whisper-1"
DEFAULT_MODEL_EMBEDDING = "openai/text-embedding-3-small"
DEFAULT_EMBEDDING_PROVIDER = "openai"
DEFAULT_OLLAMA_EMBEDDING_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL_RAG = "google/gemini-2.5-flash"
DEFAULT_DATA_PDF = (
    "data/rukovodstvo_dlya_detei_i_ih_roditelei_saharnii_diabet_1_tipa_"
    "chto_neobhodimo_znat_178.pdf"
)
DEFAULT_RAG_RETRIEVAL_MODE = "semantic"
DEFAULT_SEMANTIC_RETRIEVER_K = 4
DEFAULT_BM25_RETRIEVER_K = 4
DEFAULT_HYBRID_RETRIEVER_K = 4
DEFAULT_RERANKER_FETCH_K = 10
DEFAULT_RERANKER_K = 4
DEFAULT_MODEL_CROSSENCODER = "cross-encoder/ms-marco-MiniLM-L-6-v2"
DEFAULT_RETRIEVER_K = DEFAULT_SEMANTIC_RETRIEVER_K
DEFAULT_RAGAS_LLM_MODEL = "openai/gpt-oss-20b:free"
DEFAULT_RAGAS_EMBEDDING_MODEL = "openai/text-embedding-3-large"
DEFAULT_RAGAS_EMBEDDING_PROVIDER = "openai"
DEFAULT_HUGGINGFACE_DEVICE = "cpu"
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OLLAMA_BASE_URL = "http://localhost:11434/v1"


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    openrouter_api_key: str
    llm_provider: str
    llm_base_url: str
    model_text: str
    model_image: str
    model_audio: str
    image_base_url: str
    image_api_key: str
    audio_base_url: str
    audio_api_key: str
    system_prompt: str
    data_file: str
    carb_ratio: float
    insulin_sensitivity: float
    target_glucose_min: float
    target_glucose_max: float
    fpu_ratio: float
    openai_base_url: str
    openai_api_key: str
    model_embedding: str
    embedding_provider: str
    huggingface_device: str
    ollama_embedding_base_url: str
    model_rag: str
    rag_retrieval_mode: str
    semantic_retriever_k: int
    bm25_retriever_k: int
    hybrid_retriever_k: int
    reranker_fetch_k: int
    reranker_k: int
    model_crossencoder: str
    retriever_k: int
    data_pdf: str
    chunk_size: int
    chunk_overlap: int
    chunk_separators: list[str] | None
    show_sources: bool
    langsmith_api_key: str
    langsmith_tracing_v2: bool
    langsmith_project: str
    langsmith_dataset: str
    ragas_llm_model: str
    ragas_embedding_model: str
    ragas_embedding_provider: str

    @classmethod
    def from_env(cls) -> "Config":
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set")

        provider = os.getenv("LLM_PROVIDER", "openrouter")
        if provider not in {"openrouter", "ollama"}:
            raise ValueError(f"Unknown LLM_PROVIDER: {provider}")

        model_text = (
            os.getenv("MODEL_TEXT")
            or os.getenv("LLM_MODEL")
            or DEFAULT_MODEL_TEXT
        )

        return cls(
            telegram_bot_token=token,
            openrouter_api_key=_api_key(provider),
            llm_provider=provider,
            llm_base_url=_base_url(provider),
            model_text=model_text,
            model_image=os.getenv("MODEL_IMAGE", model_text),
            model_audio=os.getenv("MODEL_AUDIO", DEFAULT_MODEL_AUDIO),
            image_base_url=os.getenv("IMAGE_LLM_BASE_URL") or _base_url(provider),
            image_api_key=_image_api_key(provider),
            audio_base_url=os.getenv("AUDIO_LLM_BASE_URL") or _base_url(provider),
            audio_api_key=_audio_api_key(provider),
            system_prompt=os.getenv("SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT),
            data_file=os.getenv("DATA_FILE", "data/meals.json"),
            carb_ratio=_float_env("CARB_RATIO", 12.0),
            insulin_sensitivity=_float_env("INSULIN_SENSITIVITY", 2.0),
            target_glucose_min=_float_env("TARGET_GLUCOSE_MIN", 5.0),
            target_glucose_max=_float_env("TARGET_GLUCOSE_MAX", 10.0),
            fpu_ratio=_float_env("FPU_RATIO", 10.0),
            openai_base_url=_openai_base_url(provider),
            openai_api_key=_openai_api_key(provider),
            model_embedding=_model_embedding(),
            embedding_provider=_embedding_provider(),
            huggingface_device=os.getenv(
                "HUGGINGFACE_DEVICE",
                DEFAULT_HUGGINGFACE_DEVICE,
            ),
            ollama_embedding_base_url=_ollama_embedding_base_url(),
            model_rag=_model_rag(provider, model_text),
            rag_retrieval_mode=_rag_retrieval_mode(),
            semantic_retriever_k=_semantic_retriever_k(),
            bm25_retriever_k=_int_env("BM25_RETRIEVER_K", DEFAULT_BM25_RETRIEVER_K),
            hybrid_retriever_k=_int_env(
                "HYBRID_RETRIEVER_K",
                DEFAULT_HYBRID_RETRIEVER_K,
            ),
            reranker_fetch_k=_int_env("RERANKER_FETCH_K", DEFAULT_RERANKER_FETCH_K),
            reranker_k=_reranker_k(),
            model_crossencoder=_model_crossencoder(),
            retriever_k=_semantic_retriever_k(),
            data_pdf=os.getenv("DATA_PDF", DEFAULT_DATA_PDF),
            chunk_size=_int_env("CHUNK_SIZE", DEFAULT_CHUNK_SIZE),
            chunk_overlap=_int_env("CHUNK_OVERLAP", DEFAULT_CHUNK_OVERLAP),
            chunk_separators=_chunk_separators(),
            show_sources=_bool_env("SHOW_SOURCES", False),
            langsmith_api_key=os.getenv("LANGSMITH_API_KEY", ""),
            langsmith_tracing_v2=_bool_env("LANGSMITH_TRACING_V2", False),
            langsmith_project=os.getenv("LANGSMITH_PROJECT", "06-rag-assistant"),
            langsmith_dataset=os.getenv("LANGSMITH_DATASET", "05-rag-qa-dataset"),
            ragas_llm_model=os.getenv("RAGAS_LLM_MODEL", DEFAULT_RAGAS_LLM_MODEL),
            ragas_embedding_model=os.getenv(
                "RAGAS_EMBEDDING_MODEL",
                DEFAULT_RAGAS_EMBEDDING_MODEL,
            ),
            ragas_embedding_provider=_ragas_embedding_provider(),
        )


def _base_url(provider: str) -> str:
    explicit = os.getenv("LLM_BASE_URL")
    if explicit:
        return explicit
    if provider == "ollama":
        return OLLAMA_BASE_URL
    return OPENROUTER_BASE_URL


def _openai_base_url(provider: str) -> str:
    explicit = os.getenv("OPENAI_BASE_URL")
    if explicit:
        return explicit
    return _base_url(provider)


def _openai_api_key(provider: str) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if api_key:
        return api_key
    image_key = os.getenv("IMAGE_OPENROUTER_API_KEY", "")
    if image_key:
        return image_key
    audio_key = os.getenv("AUDIO_OPENROUTER_API_KEY", "")
    if audio_key:
        return audio_key
    return _api_key(provider)


def _model_rag(provider: str, model_text: str) -> str:
    explicit = os.getenv("MODEL_RAG")
    if explicit:
        return explicit
    if _is_rag_hybrid(provider):
        return os.getenv("MODEL_IMAGE", DEFAULT_MODEL_RAG)
    return model_text


def _is_rag_hybrid(provider: str) -> bool:
    openai_url = _openai_base_url(provider)
    llm_url = _base_url(provider)
    return openai_url.rstrip("/") != llm_url.rstrip("/")


def _api_key(provider: str) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if provider == "ollama" and not api_key:
        return "ollama"
    return api_key


def _image_api_key(provider: str) -> str:
    image_key = os.getenv("IMAGE_OPENROUTER_API_KEY", "")
    if image_key:
        return image_key
    return _api_key(provider)


def _audio_api_key(provider: str) -> str:
    audio_key = os.getenv("AUDIO_OPENROUTER_API_KEY", "")
    if audio_key:
        return audio_key
    return _api_key(provider)


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    return float(raw)


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    return int(raw)


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def _model_embedding() -> str:
    provider = os.getenv("EMBEDDING_PROVIDER", DEFAULT_EMBEDDING_PROVIDER).lower()
    if provider in {"huggingface", "hf"}:
        hf_model = os.getenv("HUGGINGFACE_EMBEDDING_MODEL")
        if hf_model:
            return hf_model
    return (
        os.getenv("MODEL_EMBEDDING")
        or os.getenv("EMBEDDING_MODEL")
        or DEFAULT_MODEL_EMBEDDING
    )


def _embedding_provider() -> str:
    raw = os.getenv("EMBEDDING_PROVIDER", DEFAULT_EMBEDDING_PROVIDER).lower()
    aliases = {"openrouter": "openai"}
    provider = aliases.get(raw, raw)
    if provider not in {"openai", "huggingface"}:
        msg = f"Unknown EMBEDDING_PROVIDER: {raw}"
        raise ValueError(msg)
    return provider


def _ragas_embedding_provider() -> str:
    raw = os.getenv("RAGAS_EMBEDDING_PROVIDER", DEFAULT_RAGAS_EMBEDDING_PROVIDER)
    raw = raw.lower()
    aliases = {"openrouter": "openai"}
    provider = aliases.get(raw, raw)
    if provider not in {"openai", "huggingface"}:
        msg = f"Unknown RAGAS_EMBEDDING_PROVIDER: {raw}"
        raise ValueError(msg)
    return provider


def _rag_retrieval_mode() -> str:
    raw = os.getenv("RAG_RETRIEVAL_MODE") or os.getenv(
        "RETRIEVAL_MODE",
        DEFAULT_RAG_RETRIEVAL_MODE,
    )
    mode = raw.lower()
    aliases = {"hybrid_reranker": "hybrid_rerank"}
    mode = aliases.get(mode, mode)
    if mode not in {"semantic", "hybrid", "hybrid_rerank"}:
        msg = f"Unknown RAG_RETRIEVAL_MODE: {raw}"
        raise ValueError(msg)
    return mode


def _model_crossencoder() -> str:
    return (
        os.getenv("MODEL_CROSSENCODER")
        or os.getenv("CROSS_ENCODER_MODEL")
        or DEFAULT_MODEL_CROSSENCODER
    )


def _reranker_k() -> int:
    if os.getenv("RERANKER_K") is not None:
        return _int_env("RERANKER_K", DEFAULT_RERANKER_K)
    if os.getenv("RERANKER_TOP_K") is not None:
        return _int_env("RERANKER_TOP_K", DEFAULT_RERANKER_K)
    return DEFAULT_RERANKER_K


def _semantic_retriever_k() -> int:
    if os.getenv("SEMANTIC_RETRIEVER_K") is not None:
        return _int_env("SEMANTIC_RETRIEVER_K", DEFAULT_SEMANTIC_RETRIEVER_K)
    return _int_env("RETRIEVER_K", DEFAULT_RETRIEVER_K)


def _ollama_embedding_base_url() -> str:
    explicit = os.getenv("OLLAMA_EMBEDDING_BASE_URL")
    if explicit:
        return explicit.rstrip("/")
    llm_url = os.getenv("LLM_BASE_URL", OLLAMA_BASE_URL)
    if llm_url.endswith("/v1"):
        return llm_url[:-3].rstrip("/")
    return DEFAULT_OLLAMA_EMBEDDING_BASE_URL


def _chunk_separators() -> list[str] | None:
    profile = os.getenv("CHUNK_SEPARATORS", "default").lower()
    if profile in {"default", ""}:
        return None
    if profile == "pdf":
        return ["\n\n\n", "\n\n", "\n", ". ", " ", ""]
    msg = f"Unknown CHUNK_SEPARATORS profile: {profile}"
    raise ValueError(msg)
