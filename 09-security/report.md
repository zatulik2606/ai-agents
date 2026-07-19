# Отчёт: сравнение режимов retrieval в RAG-боте «Ника»

**Задача:** ответы на вопросы родителей детей с сахарным диабетом 1 типа по PDF-руководству.  
**Оценка:** RAGAS через `/evaluate_dataset` · датасет `06-rag-qa-dataset` · **9 примеров** · 2026-07-13.

**Общие настройки (одинаковые для всех экспериментов):**
- `EMBEDDING_PROVIDER=huggingface`, `HUGGINGFACE_EMBEDDING_MODEL=intfloat/multilingual-e5-base`, `HUGGINGFACE_DEVICE=cpu`
- `MODEL_RAG=google/gemini-2.5-flash` (OpenRouter)
- `DATA_PDF` — руководство по СД 1 типа для детей и родителей
- Fusion в hybrid-режимах: **RRF** (Reciprocal Rank Fusion), без весов ensemble

---

## Конфигурация экспериментов

### 1. semantic (baseline)

Только векторный поиск по эмбеддингам.

```env
RAG_RETRIEVAL_MODE=semantic
SEMANTIC_RETRIEVER_K=4          # дефолт (RETRIEVER_K)
```

### 2. hybrid

Параллельный semantic + BM25, объединение через RRF.

```env
RAG_RETRIEVAL_MODE=hybrid
SEMANTIC_RETRIEVER_K=10
BM25_RETRIEVER_K=10
HYBRID_RETRIEVER_K=4            # дефолт — сколько чанков в контекст после fusion
```

### 3. hybrid_rerank

Hybrid retrieval → cross-encoder rerank → top-K в контекст.

```env
RETRIEVAL_MODE=hybrid_reranker
CROSS_ENCODER_MODEL=cross-encoder/mmarco-mMiniLMv2-L12-H384-v1
RERANKER_TOP_K=3
SEMANTIC_RETRIEVER_K=4          # дефолт
BM25_RETRIEVER_K=4              # дефолт
RERANKER_FETCH_K=10             # дефолт — кандидаты до rerank
```

> **Замечание:** у hybrid и hybrid_rerank различаются параметры K (10/10 vs 4/4). Это влияет на сравнение; reranker компенсирует шум за счёт переранжирования.

---

## Эксперименты

| Режим | Faithfulness | Answer Relevancy | Answer Correctness | Answer Similarity | Context Recall | Context Precision |
|-------|-------------:|-----------------:|-------------------:|------------------:|---------------:|------------------:|
| semantic | 0.570 | 0.707 | 0.492 | 0.774 | 0.875 | 0.715 |
| hybrid | 0.496 | **0.830** | **0.687** | **0.819** | **1.000** | 0.800 |
| hybrid_rerank | **0.569** | 0.728 | 0.672 | 0.802 | **1.000** | **0.889** |

---

## Вывод

**Лучшую конфигурацию для задачи показал режим `hybrid_rerank`.**

**Почему:**

1. **Медицинский контекст** — критична обоснованность ответов (faithfulness). У `hybrid` она самая низкая (0.496), у `hybrid_rerank` — на уровне semantic (0.569), то есть меньше риск галлюцинаций при сохранении гибридного поиска.

2. **Точность retrieval** — `hybrid_rerank` дал лучший **context_precision** (0.889): cross-encoder отфильтровывает слабо релевантные чанки после RRF. Это важно при узком top-K (`RERANKER_TOP_K=3`).

3. **Полнота контекста** — **context_recall = 1.000** (как у hybrid): нужные фрагменты из PDF находятся стабильно.

4. **Качество ответов** — `hybrid` чуть выше по answer_correctness (0.687 vs 0.672) и relevancy (0.830 vs 0.728), но разрыв небольшой, а просадка faithfulness у чистого hybrid для медицинского бота неприемлема.

**Рекомендация для продакшена:** `hybrid_rerank` с текущим cross-encoder. Для дальнейшего улучшения — выровнять `SEMANTIC_RETRIEVER_K` / `BM25_RETRIEVER_K` с экспериментом hybrid (10/10) и повторить оценку; ожидается рост correctness без потери precision.

**semantic** остаётся простым baseline: хуже по recall, correctness и precision — имеет смысл только как эталон для сравнения.
