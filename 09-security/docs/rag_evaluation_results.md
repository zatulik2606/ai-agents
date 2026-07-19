# RAGAS evaluation — сравнение режимов retrieval

> Baseline для сравнения `semantic` / `hybrid` / `hybrid_rerank`.
> Команда: `/evaluate_dataset` · датасет: `LANGSMITH_DATASET` · feedback в LangSmith.

---

## semantic (baseline)

**Дата:** 2026-07-13  
**Команда:** `/evaluate_dataset`  
**Датасет:** `06-rag-qa-dataset` · **9 примеров**

| Метрика | Score | Статус |
|---------|------:|--------|
| faithfulness (обоснованность) | 0.570 | 🔴 |
| answer_relevancy (релевантность ответа) | 0.707 | 🟡 |
| answer_correctness (правильность) | 0.492 | 🔴 |
| answer_similarity (похожесть на эталон) | 0.774 | 🟡 |
| context_recall (полнота контекста) | 0.875 | 🟢 |
| context_precision (точность поиска) | 0.715 | 🟡 |

**Конфиг (ключевое):**
- `RAG_RETRIEVAL_MODE=semantic`
- `EMBEDDING_PROVIDER=huggingface`
- `HUGGINGFACE_EMBEDDING_MODEL=intfloat/multilingual-e5-base`
- `MODEL_RAG=google/gemini-2.5-flash` (OpenRouter)

**Вывод:** retrieval находит контекст хорошо (recall 0.875), но faithfulness и correctness слабые — есть пространство для hybrid/rerank.

---

## hybrid

**Дата:** 2026-07-13  
**Команда:** `/evaluate_dataset`  
**Датасет:** `06-rag-qa-dataset` · **9 примеров**

| Метрика | Score | Статус |
|---------|------:|--------|
| faithfulness (обоснованность) | 0.496 | 🔴 |
| answer_relevancy (релевантность ответа) | 0.830 | 🟢 |
| answer_correctness (правильность) | 0.687 | 🟡 |
| answer_similarity (похожесть на эталон) | 0.819 | 🟢 |
| context_recall (полнота контекста) | 1.000 | 🟢 |
| context_precision (точность поиска) | 0.800 | 🟡 |

**Конфиг (`.env` строки 66–71):**
```env
RAG_RETRIEVAL_MODE=hybrid
SEMANTIC_RETRIEVER_K=10
BM25_RETRIEVER_K=10
ENSEMBLE_SEMANTIC_WEIGHT=0.5   # не используется — fusion через RRF
ENSEMBLE_BM25_WEIGHT=0.5       # не используется — fusion через RRF
```
- `HYBRID_RETRIEVER_K` — не задан, дефолт **4** (после fusion в контекст)
- `EMBEDDING_PROVIDER=huggingface`, `intfloat/multilingual-e5-base`
- `MODEL_RAG=google/gemini-2.5-flash`

**Сравнение с semantic:**

| Метрика | semantic | hybrid | Δ |
|---------|--------:|-------:|---|
| faithfulness | 0.570 | 0.496 | −0.074 |
| answer_relevancy | 0.707 | 0.830 | +0.123 |
| answer_correctness | 0.492 | 0.687 | +0.195 |
| answer_similarity | 0.774 | 0.819 | +0.045 |
| context_recall | 0.875 | 1.000 | +0.125 |
| context_precision | 0.715 | 0.800 | +0.085 |

**Вывод:** hybrid улучшил recall, relevancy, correctness и precision; faithfulness чуть ниже semantic.

---

## hybrid_rerank

**Дата:** 2026-07-13  
**Команда:** `/evaluate_dataset`  
**Датасет:** `06-rag-qa-dataset` · **9 примеров**

| Метрика | Score | Статус |
|---------|------:|--------|
| faithfulness (обоснованность) | 0.569 | 🔴 |
| answer_relevancy (релевантность ответа) | 0.728 | 🟡 |
| answer_correctness (правильность) | 0.672 | 🟡 |
| answer_similarity (похожесть на эталон) | 0.802 | 🟢 |
| context_recall (полнота контекста) | 1.000 | 🟢 |
| context_precision (точность поиска) | 0.889 | 🟢 |

**Конфиг (`.env` строки 74–76):**
```env
RETRIEVAL_MODE=hybrid_reranker
CROSS_ENCODER_MODEL=cross-encoder/mmarco-mMiniLMv2-L12-H384-v1
RERANKER_TOP_K=3
```
- `SEMANTIC_RETRIEVER_K` / `BM25_RETRIEVER_K` — не заданы, дефолт **4**
- `RERANKER_FETCH_K` — не задан, дефолт **10**
- `EMBEDDING_PROVIDER=huggingface`, `intfloat/multilingual-e5-base`
- `MODEL_RAG=google/gemini-2.5-flash`

**Сравнение с semantic и hybrid:**

| Метрика | semantic | hybrid | hybrid_rerank | Δ vs semantic | Δ vs hybrid |
|---------|--------:|-------:|--------------:|--------------:|------------:|
| faithfulness | 0.570 | 0.496 | 0.569 | −0.001 | +0.073 |
| answer_relevancy | 0.707 | 0.830 | 0.728 | +0.021 | −0.102 |
| answer_correctness | 0.492 | 0.687 | 0.672 | +0.180 | −0.015 |
| answer_similarity | 0.774 | 0.819 | 0.802 | +0.028 | −0.017 |
| context_recall | 0.875 | 1.000 | 1.000 | +0.125 | 0.000 |
| context_precision | 0.715 | 0.800 | 0.889 | +0.174 | +0.089 |

**Вывод:** reranker дал лучший context_precision (0.889) и faithfulness на уровне semantic; hybrid без rerank всё ещё лидирует по relevancy и correctness на этом датасете.

