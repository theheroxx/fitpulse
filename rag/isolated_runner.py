"""
Isolated RAG Execution Bridge
Runs RAG retrieval in a separate process to isolate
PySide6 from native ML / vector-search dependencies.
"""

import sys
import os
import json
import time
import traceback


# ============================================================
# Project root
# ============================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ============================================================
# Thread / native library isolation
# ============================================================

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"


def log(message):
    """Send debug logs to stderr, NOT stdout."""
    print(message, file=sys.stderr, flush=True)


def execute_search(query_text: str):

    start_time = time.perf_counter()

    try:
        log("[RAG Runner] Process started")
        log(f"[RAG Runner] Query: {query_text}")

        # ----------------------------------------------------
        # Import retriever
        # ----------------------------------------------------

        t0 = time.perf_counter()

        log("[RAG Runner] Importing retriever...")

        from rag.retriever import retrieve_context

        log(
            f"[RAG Runner] Retriever imported in "
            f"{time.perf_counter() - t0:.2f}s"
        )

        # ----------------------------------------------------
        # Retrieval
        # ----------------------------------------------------

        t1 = time.perf_counter()

        log("[RAG Runner] Starting retrieval...")

        result = retrieve_context(query_text)

        log(
            f"[RAG Runner] Retrieval completed in "
            f"{time.perf_counter() - t1:.2f}s"
        )

        # ----------------------------------------------------
        # Return JSON
        # ----------------------------------------------------

        payload = json.dumps(
            result,
            ensure_ascii=False
        )

        print(payload, flush=True)

        log(
            f"[RAG Runner] Total execution time: "
            f"{time.perf_counter() - start_time:.2f}s"
        )

    except Exception as e:

        log("[RAG Runner] ERROR")
        log(str(e))
        log(traceback.format_exc())

        error_payload = {
            "documents": [[]],
            "raw_results": {},
            "intent": "unknown",
            "error": str(e)
        }

        print(
            json.dumps(
                error_payload,
                ensure_ascii=False
            ),
            flush=True
        )


if __name__ == "__main__":

    if len(sys.argv) > 1:

        query_arg = sys.argv[1]

        execute_search(query_arg)

    else:

        print(
            json.dumps(
                {
                    "documents": [[]],
                    "error": "No query provided"
                },
                ensure_ascii=False
            ),
            flush=True
        )