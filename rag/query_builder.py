"""
Query Builder for RAG System - OFFLINE & ISOLATED VERSION
Builds structured queries and safely formats RAG responses without an LLM.
Uses process isolation to prevent native C++/Rust crashes in Qt worker threads.
"""

from typing import Dict, Any, List, Optional
import logging
import subprocess
import json
import sys
import os

logger = logging.getLogger(__name__)


def build_query(user_input: Dict[str, Any], detector_output: Dict[str, Any]) -> str:
    """
    Build natural language query for better semantic retrieval.
    
    Creates a concise, natural language query that embedding models understand better
    than pipe-separated attribute lists.
    
    Args:
        user_input: User profile data (Age, HealthCondition, FitnessLevel, ActivityType, DurationMins, etc.)
        detector_output: Risk detector output (label, reasons, warnings)
    
    Returns:
        Natural language query string for vector search
    """
    if not user_input:
        user_input = {}
    if not detector_output:
        detector_output = {}
    
    query_parts = []
    
    # Extract key information
    health = user_input.get('HealthCondition', '')
    fitness = user_input.get('FitnessLevel', '')
    activity = user_input.get('ActivityType', '')
    goals = user_input.get('Goals', '')
    
    # Build natural language phrases
    
    # Health condition is most important for safety
    if health and health != 'unknown':
        query_parts.append(f"exercises for someone with {health}")
    
    # Activity type
    if activity and activity != 'unknown':
        query_parts.append(f"during {activity}")
    
    # Fitness level
    if fitness and fitness != 'unknown':
        query_parts.append(f"for {fitness} fitness level")
    
    # Goals
    if goals and goals != 'unknown':
        query_parts.append(f"to achieve {goals}")
    
    # Add risk warnings if any
    warnings = detector_output.get('warnings', [])
    if warnings and isinstance(warnings, list) and len(warnings) > 0:
        # Take first warning and make it natural
        warning_text = warnings[0].lower()
        if "consult" in warning_text or "doctor" in warning_text:
            query_parts.append("with medical precautions")
        else:
            query_parts.append(f"considering {warning_text}")
    
    # Add risk label if significant
    risk_label = detector_output.get('label', '')
    if risk_label and risk_label.lower() in ['high', 'medium']:
        query_parts.append("safe exercise recommendations")
    
    # If no specific parts, use generic query
    if not query_parts:
        return "safe exercise recommendations for general fitness"
    
    # Join in natural language
    query = " ".join(query_parts)
    
    # Limit length (embedding models work best with shorter queries)
    if len(query) > 200:
        query = query[:200]
    
    return query


def get_rag_context(
    user_input: Dict[str, Any],
    detector_output: Dict[str, Any],
    user_query: str = ""
) -> Dict[str, Any]:
    """
    Get comprehensive RAG context by combining structured profile data
    with natural language user query.
    
    Uses subprocess process isolation to shield the PySide6 main process
    from native Rust/C++ threading panics (0xC0000005).
    
    Args:
        user_input: User profile data
        detector_output: Risk detector output
        user_query: Free-text user question
    
    Returns:
        Dict with documents, raw_results, intent, and error fields
    """
    # Build natural language search query
    search_query = build_query(user_input, detector_output)
    
    # Append user's natural language question
    if user_query and user_query.strip():
        # If we already have a good query, combine naturally
        if search_query and len(search_query) > 20:
            search_query = f"{search_query} {user_query.strip()}"
        else:
            # User query is the primary query
            search_query = user_query.strip()
    
    # If query is empty, return empty context
    if not search_query.strip():
        logger.warning("Empty search query generated")
        return {
            'documents': [[]],
            'raw_results': {},
            'intent': 'unknown',
            'error': 'Empty query'
        }
    
    logger.info(f"Retrieving context for query: {search_query[:200]}...")
    
    # Execute retrieval inside isolated subprocess wrapper
    try:
        script_path = os.path.join(os.path.dirname(__file__), "isolated_runner.py")
        result = subprocess.run(
            [sys.executable, script_path, search_query],
            capture_output=True,
            text=True,
            timeout=40
        )
        
        if result.returncode == 0 and result.stdout.strip():
            context = json.loads(result.stdout.strip())
            context['search_query'] = search_query
            context['has_user_query'] = bool(user_query and user_query.strip())
            return context
        else:
            logger.warning(f"Subprocess non-zero exit or empty response: {result.stderr}")

    except Exception as e:
        logger.error(f"Failed to get RAG context via isolated subprocess: {e}", exc_info=True)
    
    # Fallback response dict
    return {
        'documents': [[]],
        'raw_results': {},
        'intent': 'unknown',
        'error': 'Execution fallback'
    }


def _extract_documents(context: Dict[str, Any]) -> List[str]:
    """Safely extract document list from context dict"""
    try:
        documents = context.get('documents', [])
        if not documents:
            return []
        
        # Handle nested list structure: [['doc1', 'doc2', ...]]
        if isinstance(documents, list) and len(documents) > 0:
            first = documents[0]
            if isinstance(first, list):
                return [doc for doc in first if doc and isinstance(doc, str)]
            elif isinstance(first, str):
                return [doc for doc in documents if doc and isinstance(doc, str)]
        
        return []
    except (IndexError, TypeError, AttributeError):
        return []


def format_context_for_prompt(
    context: Dict[str, Any],
    max_docs: int = 5
) -> str:

    if not context:
        return ""

    documents = context.get("documents", [])

    # Handle:
    # {"documents": [["doc1", "doc2"]]}
    if (
        isinstance(documents, list)
        and len(documents) > 0
        and isinstance(documents[0], list)
    ):
        documents = documents[0]

    if not documents:
        return ""

    intent = context.get("intent", "unknown")

    lines = [
        "",
        "=== RETRIEVED KNOWLEDGE BASE ===",
        f"Category: {intent.upper()}",
        "",
    ]

    for i, document in enumerate(documents[:max_docs], start=1):

        if not isinstance(document, str):
            continue

        document = document.strip()

        if not document:
            continue

        lines.append(f"[Reference {i}]")
        lines.append(document)
        lines.append("")

    lines.append("==============================")
    
    return "\n".join(lines)


def generate_rag_response(context: Dict[str, Any], user_query: str = "") -> str:
    """
    Generate a response using RAG context.
    This is the OFFLINE version — no LLM, just formats retrieved documents.
    
    Args:
        context: RAG context dict from get_rag_context() or retrieve_context()
        user_query: The user's original question (for context-aware formatting)
    
    Returns:
        Formatted response string with relevant information
    """
    # Check for errors
    if context.get('error'):
        return (
            f"⚠️ Unable to retrieve specific information at this time.\n\n"
            f"Please consult a healthcare professional for personalized advice."
        )
    
    # Extract documents
    documents = _extract_documents(context)
    
    if not documents:
        # No documents found — give helpful fallback
        intent = context.get('intent', 'unknown')
        
        if intent == 'medical':
            return (
                "No specific medical guidelines found for your query.\n\n"
                "⚠️ Please consult a healthcare professional before starting any exercise program, "
                "especially if you have pre-existing health conditions."
            )
        elif intent == 'nutrition':
            return (
                "No specific nutrition information found for your query.\n\n"
                "💡 Consider consulting a registered dietitian for personalized meal planning."
            )
        else:
            return (
                "No specific exercise recommendations found for your query.\n\n"
                "💡 General tip: Start with low-intensity activities and gradually increase "
                "duration and intensity.\n\n"
                "⚠️ Consult a healthcare professional before starting any exercise program."
            )
    
    # Build response from retrieved documents
    intent = context.get('intent', 'unknown')
    intent_labels = {
        'medical': '📋 Medical Guidelines',
        'nutrition': '🍎 Nutrition Information',
        'exercises': '🏃 Exercise Recommendations'
    }
    section_title = intent_labels.get(intent, '📚 Relevant Information')
    
    response_parts = [f"Based on available {section_title.lower()}:\n"]
    
    # Add up to 5 documents, truncating long ones
    max_docs = min(5, len(documents))
    for i, doc in enumerate(documents[:max_docs], 1):
        # Clean up whitespace
        doc = doc.strip()
        
        # Truncate very long documents for readability
        if len(doc) > 400:
            truncated = doc[:400]
            last_period = truncated.rfind('.')
            last_newline = truncated.rfind('\n')
            break_point = max(last_period, last_newline)
            
            if break_point > 200:
                doc = truncated[:break_point + 1] + "..."
            else:
                doc = truncated + "..."
        
        response_parts.append(f"• {doc}\n")
    
    # Add disclaimer
    response_parts.append(
        "\n⚠️ **Disclaimer:** This information is for educational purposes only. "
        "Consult a healthcare professional before starting any exercise program."
    )
    
    # Add document count for transparency
    if len(documents) > max_docs:
        response_parts.append(
            f"\n📊 *Showing {max_docs} of {len(documents)} relevant results.*"
        )
    
    return "\n".join(response_parts)


def generate_context_summary(context: Dict[str, Any]) -> str:
    """
    Generate a brief summary of what was retrieved.
    Useful for logging or showing context metadata to users.
    
    Args:
        context: RAG context dict
    
    Returns:
        Summary string
    """
    documents = _extract_documents(context)
    intent = context.get('intent', 'unknown')
    error = context.get('error')
    
    parts = []
    parts.append(f"Intent: {intent}")
    parts.append(f"Documents found: {len(documents)}")
    
    if error:
        parts.append(f"Error: {error}")
    
    collections = list(context.get('raw_results', {}).keys())
    if collections:
        parts.append(f"Collections searched: {', '.join(collections)}")
    
    return " | ".join(parts)


def has_valid_context(context: Dict[str, Any]) -> bool:
    """
    Check if the context contains actual usable documents.
    
    Args:
        context: RAG context dict
    
    Returns:
        True if context has documents, False otherwise
    """
    documents = _extract_documents(context)
    return len(documents) > 0