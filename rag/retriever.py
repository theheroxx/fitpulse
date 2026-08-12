"""
Retriever for FitStat RAG System
--------------------------------
Pipeline:

Query
  -> Intent Detection
  -> ChromaDB Candidate Retrieval
  -> Reranking
  -> Deduplication
  -> Top-K Documents

Designed for:
- PySide6
- Offline execution
- ChromaDB
- Existing rag.reranker module
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


# ============================================================
# Intent Detection
# ============================================================

def detect_query_intent(query: str) -> str:
    """
    Detect the main information category requested by the user.

    Returns:
        nutrition | medical | exercises
    """

    if not query:
        return "exercises"

    query_lower = query.lower()

    # --------------------------------------------------------
    # Nutrition
    # --------------------------------------------------------
    nutrition_keywords = [
        "food", "eat", "meal", "protein", "calorie",
        "diet", "nutrition", "carbs", "fat",
        "vitamin", "mineral", "breakfast",
        "lunch", "dinner", "snack",
        "glycemic", "nutrition"
    ]

    if any(keyword in query_lower for keyword in nutrition_keywords):
        return "nutrition"

    # --------------------------------------------------------
    # Medical / Health
    # --------------------------------------------------------
    medical_keywords = [
        "asthma", "heart", "diabetes",
        "blood pressure", "medical",
        "guideline", "condition", "symptom",
        "bronchoconstriction", "inhaler",
        "medication", "disease",
        "cardiovascular", "respiratory",
        "health"
    ]

    if any(keyword in query_lower for keyword in medical_keywords):
        return "medical"

    # --------------------------------------------------------
    # Exercise
    # --------------------------------------------------------
    exercise_keywords = [
        "exercise", "workout", "training",
        "running", "walking", "cycling",
        "cardio", "aerobic", "strength",
        "fitness", "vo2max", "vo2 max",
        "endurance", "stamina",
        "performance", "activity",
        "intensity", "duration",
        "recovery", "muscle"
    ]

    if any(keyword in query_lower for keyword in exercise_keywords):
        return "exercises"

    # Default
    return "exercises"


# ============================================================
# Collection Ordering
# ============================================================

def get_collection_order(intent: str) -> List[str]:
    """
    Decide which Chroma collections should be queried first.

    NOTE:
    This does NOT determine final ranking.
    Final ranking is handled by reranker.py.
    """

    if intent == "nutrition":
        return [
            "nutrition",
            "exercises",
            "medical"
        ]

    if intent == "medical":
        return [
            "medical",
            "exercises",
            "nutrition"
        ]

    return [
        "exercises",
        "medical",
        "nutrition"
    ]


# ============================================================
# Safe Chroma Result Extraction
# ============================================================

def _safe_collection_result(
    results: Dict[str, Any],
    collection: str
) -> Dict[str, Any]:
    """Return a safe Chroma result structure."""

    default = {
        "documents": [[]],
        "metadatas": [[]],
        "distances": [[]],
    }

    try:
        value = results.get(collection)

        if not isinstance(value, dict):
            return default

        return {
            "documents": value.get("documents", [[]]),
            "metadatas": value.get("metadatas", [[]]),
            "distances": value.get("distances", [[]]),
        }

    except Exception:
        return default


# ============================================================
# Candidate Statistics
# ============================================================

def _count_candidates(results: Dict[str, Any]) -> int:
    """Count all candidate documents returned by ChromaDB."""

    count = 0

    for collection_result in results.values():

        if not isinstance(collection_result, dict):
            continue

        documents = collection_result.get("documents", [[]])

        if (
            isinstance(documents, list)
            and documents
            and isinstance(documents[0], list)
        ):
            count += len(documents[0])

    return count


# ============================================================
# Main Retrieval
# ============================================================

def retrieve_context(
    query: str,
    candidate_k: int = 6,
    top_k: int = 5
) -> Dict[str, Any]:
    """
    Retrieve and rerank context for the user's query.

    Pipeline:

        Query
          ↓
        Intent Detection
          ↓
        ChromaDB
          ↓
        Candidate Documents
          ↓
        Reranker
          ↓
        Top-K
    """

    empty_result = {
        "documents": [[]],
        "raw_results": {},
        "reranked_results": [],
        "intent": "unknown",
        "candidate_count": 0,
        "final_count": 0,
        "reranking_enabled": False,
        "error": None,
    }

    # --------------------------------------------------------
    # Validate query
    # --------------------------------------------------------

    if not query or not query.strip():

        empty_result["error"] = "Empty query"

        return empty_result

    query = query.strip()

    try:

        # ----------------------------------------------------
        # 1. Intent
        # ----------------------------------------------------

        intent = detect_query_intent(query)

        collections = get_collection_order(intent)

        logger.info(
            "RAG intent=%s | collections=%s",
            intent,
            collections
        )

        # ----------------------------------------------------
        # 2. Vector Retrieval
        # ----------------------------------------------------

        results = {}

        try:

            from rag.rag_system import rag_orchestrator

            vector_store = getattr(
                rag_orchestrator,
                "vector_store",
                None
            )

            if vector_store is None:

                raise RuntimeError(
                    "Vector store is not initialized"
                )

            results = vector_store.search_multiple(
                collections,
                query,
                n=candidate_k
            )

        except Exception as e:

            logger.error(
                "ChromaDB retrieval failed: %s",
                e,
                exc_info=True
            )

            # Return safely instead of crashing GUI
            empty_result["intent"] = intent
            empty_result["error"] = (
                f"Vector retrieval failed: {str(e)}"
            )

            return empty_result

        # ----------------------------------------------------
        # 3. Candidate Count
        # ----------------------------------------------------

        candidate_count = _count_candidates(results)

        logger.info(
            "RAG retrieved %d candidate documents",
            candidate_count
        )

        if candidate_count == 0:

            empty_result["intent"] = intent
            empty_result["raw_results"] = results
            empty_result["error"] = "No documents retrieved"

            return empty_result

        # ----------------------------------------------------
        # 4. Reranking
        # ----------------------------------------------------

        try:

            from rag.reranker import rerank_results

            ranked_results = rerank_results(
                results=results,
                query=query,
                intent=intent,
                top_k=top_k
            )

        except Exception as e:

            logger.error(
                "Reranker failed: %s",
                e,
                exc_info=True
            )

            # IMPORTANT:
            # Do not silently return badly ranked documents.
            # Return an explicit error instead.
            empty_result["intent"] = intent
            empty_result["raw_results"] = results
            empty_result["candidate_count"] = candidate_count
            empty_result["error"] = (
                f"Reranking failed: {str(e)}"
            )

            return empty_result

        # ----------------------------------------------------
        # 5. Extract ranked documents
        # ----------------------------------------------------

        documents = []

        for item in ranked_results:

            if not isinstance(item, dict):
                continue

            document = item.get("document")

            if (
                isinstance(document, str)
                and document.strip()
            ):
                documents.append(document.strip())

        # ----------------------------------------------------
        # 6. Final safety deduplication
        # ----------------------------------------------------

        unique_documents = []

        seen = set()

        for document in documents:

            normalized = " ".join(
                document.lower().split()
            )

            if normalized in seen:
                continue

            seen.add(normalized)
            unique_documents.append(document)

        unique_documents = unique_documents[:top_k]

        # ----------------------------------------------------
        # 7. Final Result
        # ----------------------------------------------------

        logger.info(
            "RAG final ranking: %d/%d documents",
            len(unique_documents),
            candidate_count
        )

        return {
            "documents": [unique_documents],

            "raw_results": results,

            "reranked_results": ranked_results,

            "intent": intent,

            "candidate_count": candidate_count,

            "final_count": len(unique_documents),

            "reranking_enabled": True,

            "error": None,
        }

    except Exception as e:

        logger.error(
            "Unexpected RAG retrieval error: %s",
            e,
            exc_info=True
        )

        empty_result["error"] = str(e)

        return empty_result


# ============================================================
# Legacy Compatibility
# ============================================================

def retrieve_context_legacy(
    query: str
) -> List[List[str]]:
    """
    Backward-compatible API.
    """

    result = retrieve_context(query)

    return result.get(
        "documents",
        [[]]
    )


# ============================================================
# Result Helpers
# ============================================================

def has_results(
    context: Dict[str, Any]
) -> bool:
    """Check whether usable documents were retrieved."""

    try:

        documents = context.get(
            "documents",
            [[]]
        )

        return (
            isinstance(documents, list)
            and len(documents) > 0
            and isinstance(documents[0], list)
            and len(documents[0]) > 0
        )

    except Exception:

        return False


def get_ranked_documents(
    context: Dict[str, Any]
) -> List[str]:
    """Safely extract final ranked documents."""

    if not context:
        return []

    documents = context.get(
        "documents",
        [[]]
    )

    if (
        isinstance(documents, list)
        and documents
        and isinstance(documents[0], list)
    ):
        return [
            doc
            for doc in documents[0]
            if isinstance(doc, str)
            and doc.strip()
        ]

    return []


# ============================================================
# Formatting
# ============================================================

def format_context(
    context: Dict[str, Any],
    max_docs: int = 5
) -> str:
    """
    Format final reranked documents for the LLM.
    """

    if not has_results(context):
        return ""

    documents = get_ranked_documents(context)

    documents = documents[:max_docs]

    intent = context.get(
        "intent",
        "unknown"
    )

    formatted = (
        "\n\n---\n"
        f"Retrieved Knowledge "
        f"(intent: {intent})\n"
    )

    for index, document in enumerate(
        documents,
        1
    ):

        # Avoid huge context
        if len(document) > 700:
            document = (
                document[:700]
                + "..."
            )

        formatted += (
            f"\n[Reference {index}]\n"
            f"{document}\n"
        )

    formatted += "\n---\n"

    return formatted


# ============================================================
# Ranking Debugging
# ============================================================

def get_ranking_explanation(
    context: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Return ranking details for debugging/evaluation.
    """

    ranked = context.get(
        "reranked_results",
        []
    )

    if not isinstance(ranked, list):
        return []

    explanation = []

    for rank, item in enumerate(
        ranked,
        start=1
    ):

        if not isinstance(item, dict):
            continue

        scores = item.get(
            "scores",
            {}
        )

        explanation.append({

            "rank": rank,

            "collection": item.get(
                "collection"
            ),

            "score": item.get(
                "score"
            ),

            "distance": item.get(
                "distance"
            ),

            "semantic": scores.get(
                "semantic",
                0.0
            ),

            "keyword": scores.get(
                "keyword",
                0.0
            ),

            "intent": scores.get(
                "intent",
                0.0
            ),

            "metadata": scores.get(
                "metadata",
                0.0
            ),

            "risk": scores.get(
                "risk",
                0.0
            ),

            "document": item.get(
                "document",
                ""
            ),
        })

    return explanation