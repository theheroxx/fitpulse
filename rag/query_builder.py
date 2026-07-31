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
    Build comprehensive query string for RAG retrieval.
    Combines user profile, health data, and risk assessment into a searchable string.
    
    Args:
        user_input: User profile data (Age, HealthCondition, FitnessLevel, ActivityType, DurationMins, etc.)
        detector_output: Risk detector output (label, reasons, warnings)
    
    Returns:
        Pipe-separated query string for vector search
    """
    if not user_input:
        user_input = {}
    if not detector_output:
        detector_output = {}
    
    query_parts = []
    
    # 1. User profile fields
    age = user_input.get('Age', 'unknown')
    if age and age != 'unknown':
        query_parts.append(f"Age {age}")
    
    gender = user_input.get('Gender', 'unknown')
    if gender and gender != 'unknown':
        query_parts.append(f"Gender {gender}")

    health = user_input.get('HealthCondition', 'unknown')
    if health and health != 'unknown':
        query_parts.append(f"Health condition: {health}")
    
    fitness = user_input.get('FitnessLevel', 'unknown')
    if fitness and fitness != 'unknown':
        query_parts.append(f"Fitness level: {fitness}")
    
    activity = user_input.get('ActivityType', 'unknown')
    if activity and activity != 'unknown':
        query_parts.append(f"Activity: {activity}")
    
    duration = user_input.get('DurationMins', None)
    if duration is not None and duration != 'unknown':
        query_parts.append(f"Duration: {duration} minutes")
    
    weather = user_input.get('Weather', 'unknown')
    if weather and weather != 'unknown':
        query_parts.append(f"Environment: {weather}")

    goals = user_input.get('Goals', 'unknown')
    if goals and goals != 'unknown':
        query_parts.append(f"Goals: {goals}")

    # 2. Risk assessment & detector output
    risk_label = detector_output.get('label', None)
    if risk_label:
        query_parts.append(f"Risk level: {risk_label}")
    
    reasons = detector_output.get('reasons', [])
    if reasons:
        reasons_str = ', '.join(reasons[:3]) if isinstance(reasons, list) else str(reasons)
        query_parts.append(f"Risk factors: {reasons_str}")

    warnings = detector_output.get('warnings', [])
    if warnings:
        warnings_str = ', '.join(warnings[:2]) if isinstance(warnings, list) else str(warnings)
        query_parts.append(f"Safety warnings: {warnings_str}")

    # If no meaningful parts, return a generic fitness query
    if not query_parts:
        return "fitness exercise safety recommendations"
    
    return " | ".join(query_parts)


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
    # Build structured search query
    search_query = build_query(user_input, detector_output)
    
    # Append user's natural language question
    if user_query and user_query.strip():
        search_query += f" | Question: {user_query.strip()}"
    
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
            timeout=12
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


def format_context_for_prompt(context: Dict[str, Any], max_docs: int = 4) -> str:
    """Format retrieved context into a structured block for LLM integration (if enabled)."""
    docs = _extract_documents(context)
    if not docs:
        return ""
    
    intent = context.get('intent', 'exercises')
    formatted = f"\n=== RETRIEVED KNOWLEDGE BASE (Category: {intent.upper()}) ===\n"
    
    for i, doc in enumerate(docs[:max_docs], 1):
        clean_doc = doc.strip().replace("\n\n", "\n")
        formatted += f"\n[Reference {i}]:\n{clean_doc}\n"
        
    formatted += "===============================================================\n"
    return formatted


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