import sys
import os

# Change to project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)  # ← This fixes the relative path issue
sys.path.insert(0, PROJECT_ROOT)

"""
FitStat RAG Retriever + Reranker Test

Tests the real retrieval pipeline:

    Query
      ↓
    Intent Detection
      ↓
    ChromaDB Retrieval
      ↓
    Reranker
      ↓
    Final Ranked Documents

Run:
    python test_retriever.py

Or:
    python test_retriever.py "How to maximize my VO2max?"
"""

import json
import traceback
from typing import Any, Dict


# ============================================================
# Configuration
# ============================================================

DEFAULT_QUERY = "What should someone with asthma know about exercise?"

TOP_K = 8


# ============================================================
# Pretty Printing
# ============================================================

def separator(char="=", length=80):
    print(char * length)


def print_document(index: int, item: Dict[str, Any]):
    """Print one reranked document with all scoring details."""

    document = item.get("document", "")
    collection = item.get("collection", "unknown")
    score = item.get("score", 0.0)
    distance = item.get("distance")

    scores = item.get("scores", {})

    print(f"\n{'-' * 80}")
    print(f"RANK #{index}")
    print(f"Collection : {collection}")
    print(f"Final Score: {score}")
    print(f"Distance   : {distance}")

    print("\nScore Breakdown:")
    print(f"  Semantic : {scores.get('semantic', 0.0):.6f}")
    print(f"  Keyword  : {scores.get('keyword', 0.0):.6f}")
    print(f"  Intent   : {scores.get('intent', 0.0):.6f}")
    print(f"  Metadata : {scores.get('metadata', 0.0):.6f}")
    print(f"  Risk     : {scores.get('risk', 0.0):.6f}")

    metadata = item.get("metadata", {})

    if metadata:
        print("\nMetadata:")
        print(json.dumps(metadata, indent=2, ensure_ascii=False))

    print("\nDocument:")
    print(document)


# ============================================================
# Main Test
# ============================================================

def main():

    query = (
        " ".join(sys.argv[1:])
        if len(sys.argv) > 1
        else DEFAULT_QUERY
    )

    separator()

    print("FITSTAT RAG RETRIEVER TEST")

    separator()

    print(f"\nQuery:")
    print(query)

    print(f"\nTop K: {TOP_K}")

    # --------------------------------------------------------
    # Import retriever
    # --------------------------------------------------------

    print("\n[1] Importing retriever...")

    try:
        from rag.retriever import (
            retrieve_context,
            detect_query_intent,
        )

        print("✅ Retriever imported successfully")

    except Exception as e:

        print("❌ Failed to import retriever")

        traceback.print_exc()

        return

    # --------------------------------------------------------
    # Intent
    # --------------------------------------------------------

    print("\n[2] Detecting intent...")

    try:

        intent = detect_query_intent(query)

        print(f"✅ Intent: {intent}")

    except Exception:

        print("❌ Intent detection failed")

        traceback.print_exc()

        return

    # --------------------------------------------------------
    # Retrieval
    # --------------------------------------------------------

    print("\n[3] Running retrieve_context()...")

    try:

        context = retrieve_context(query)

    except Exception:

        print("❌ Retriever crashed")

        traceback.print_exc()

        return

    # --------------------------------------------------------
    # Basic context information
    # --------------------------------------------------------

    print("\n[4] Retrieval result")

    separator("-")

    print(
        "Context type:",
        type(context)
    )

    print(
        "Context keys:",
        list(context.keys())
    )

    print(
        "Intent:",
        context.get("intent")
    )

    print(
        "Error:",
        context.get("error")
    )

    # --------------------------------------------------------
    # Check documents
    # --------------------------------------------------------

    documents = context.get(
        "documents",
        [[]]
    )

    if (
        not documents
        or not isinstance(documents, list)
        or not documents[0]
    ):

        print("\n❌ NO DOCUMENTS RETRIEVED")

        print("\nRaw result:")

        print(
            json.dumps(
                context,
                indent=2,
                ensure_ascii=False,
                default=str
            )
        )

        return

    print(
        f"\n✅ Documents retrieved: {len(documents[0])}"
    )

    # --------------------------------------------------------
    # Raw Chroma results
    # --------------------------------------------------------

    raw_results = context.get(
        "raw_results",
        {}
    )

    print("\n[5] Raw ChromaDB results")

    separator("-")

    if not raw_results:

        print("❌ raw_results is EMPTY")

    else:

        print(
            f"Collections returned: "
            f"{list(raw_results.keys())}"
        )

        for collection_name, collection_data in raw_results.items():

            print(
                f"\nCollection: {collection_name}"
            )

            if not isinstance(
                collection_data,
                dict
            ):
                print("  Invalid collection structure")
                continue

            docs = collection_data.get(
                "documents",
                [[]]
            )

            distances = collection_data.get(
                "distances",
                [[]]
            )

            metadatas = collection_data.get(
                "metadatas",
                [[]]
            )

            doc_count = (
                len(docs[0])
                if docs
                and isinstance(docs, list)
                and docs[0]
                else 0
            )

            distance_count = (
                len(distances[0])
                if distances
                and isinstance(distances, list)
                and distances[0]
                else 0
            )

            metadata_count = (
                len(metadatas[0])
                if metadatas
                and isinstance(metadatas, list)
                and metadatas[0]
                else 0
            )

            print(
                f"  Documents : {doc_count}"
            )

            print(
                f"  Distances : {distance_count}"
            )

            print(
                f"  Metadatas : {metadata_count}"
            )

    # --------------------------------------------------------
    # Reranker
    # --------------------------------------------------------

    print("\n[6] Checking reranker...")

    try:

        from rag.reranker import (
            rerank_results,
        )

        print(
            "✅ Reranker imported successfully"
        )

    except Exception:

        print(
            "❌ Failed to import reranker"
        )

        traceback.print_exc()

        return

    # --------------------------------------------------------
    # Explicit reranking
    # --------------------------------------------------------

    print("\n[7] Running rerank_results()...")

    try:

        ranked_results = rerank_results(
            results=raw_results,
            query=query,
            intent=intent,
            top_k=TOP_K,
        )

    except Exception:

        print(
            "❌ Reranker crashed"
        )

        traceback.print_exc()

        return

    if not ranked_results:

        print(
            "\n❌ Reranker returned ZERO results"
        )

        return

    print(
        f"\n✅ Reranker returned "
        f"{len(ranked_results)} documents"
    )

    # --------------------------------------------------------
    # Ranked results
    # --------------------------------------------------------

    print("\n[8] FINAL RANKING")

    separator()

    for index, item in enumerate(
        ranked_results,
        start=1
    ):

        print_document(
            index,
            item
        )

    # --------------------------------------------------------
    # Final documents
    # --------------------------------------------------------

    print("\n[9] Final documents passed to LLM")

    separator()

    for index, item in enumerate(
        ranked_results,
        start=1
    ):

        document = item.get(
            "document",
            ""
        )

        print(
            f"\n[{index}] "
            f"{item.get('collection', 'unknown')}"
        )

        print(document)

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    print("\n[10] Validation")

    separator("-")

    checks = {

        "Retriever returned context":
            bool(context),

        "No retrieval error":
            context.get("error") is None,

        "Raw Chroma results exist":
            bool(raw_results),

        "Documents retrieved":
            bool(documents[0]),

        "Reranker returned results":
            bool(ranked_results),

        "Ranking scores exist":
            all(
                "score" in item
                for item in ranked_results
            ),

        "Documents are strings":
            all(
                isinstance(
                    item.get("document"),
                    str
                )
                for item in ranked_results
            ),

    }

    all_passed = True

    for name, passed in checks.items():

        if passed:
            print(
                f"✅ {name}"
            )

        else:
            print(
                f"❌ {name}"
            )

            all_passed = False

    # --------------------------------------------------------
    # Reranking enabled?
    # --------------------------------------------------------

    print("\n[11] Retriever integration status")

    separator("-")

    reranked_context = context.get(
        "reranked_results"
    )

    if reranked_context:

        print(
            "✅ Retriever itself contains "
            "`reranked_results`."
        )

        print(
            f"   Count: {len(reranked_context)}"
        )

    else:

        print(
            "⚠️ Retriever context does NOT "
            "contain `reranked_results`."
        )

        print(
            "   Explicit reranking test succeeded, "
            "but integration may need checking."
        )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    separator()

    if all_passed:

        print(
            "✅ RAG RETRIEVER + RERANKER TEST PASSED"
        )

    else:

        print(
            "⚠️ RAG TEST COMPLETED WITH FAILURES"
        )

    separator()

    print("\nRecommended query tests:")

    print(
        '  python test_retriever.py '
        '"How to maximize my VO2max?"'
    )

    print(
        '  python test_retriever.py '
        '"How can I improve my cardiovascular endurance?"'
    )

    print(
        '  python test_retriever.py '
        '"What should I eat after exercise?"'
    )

    print(
        '  python test_retriever.py '
        '"What should someone with asthma know about exercise?"'
    )

    print(
        '  python test_retriever.py '
        '"How does poor air quality affect exercise?"'
    )


if __name__ == "__main__":
    main()