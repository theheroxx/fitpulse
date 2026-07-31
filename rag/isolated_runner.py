# rag/isolated_runner.py
"""
Isolated RAG Execution Bridge
Runs vector searches and embedding calculations in a separate process space
to completely insulate the PySide6 GUI process from C++/Rust native thread panics.
"""

import sys
import os
import json

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Critical thread and memory flags for isolated execution
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

def execute_search(query_text: str):
    """Executes vector search safely in process isolation."""
    try:
        from rag.retriever import retrieve_context
        result = retrieve_context(query_text)
        # Print JSON payload to stdout for caller capture
        print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        error_payload = {
            "documents": [[]],
            "raw_results": {},
            "intent": "unknown",
            "error": str(e)
        }
        print(json.dumps(error_payload))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query_arg = sys.argv[1]
        execute_search(query_arg)
    else:
        print(json.dumps({"documents": [[]], "error": "No query provided"}))