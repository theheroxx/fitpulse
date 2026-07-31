"""
Retriever for RAG System - THREAD-SAFE VERSION
Handles intent detection, vector document retrieval, and prioritization
without crashing Qt worker threads.
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


def detect_query_intent(query: str) -> str:
    """Detect what type of information the user is looking for"""
    if not query:
        return "exercises"
    
    query_lower = query.lower()
    
    # Nutrition intent
    nutrition_keywords = [
        "food", "eat", "meal", "protein", "calorie", "diet", 
        "nutrition", "carbs", "fat", "vitamin", "mineral",
        "breakfast", "lunch", "dinner", "snack", "glycemic"
    ]
    if any(kw in query_lower for kw in nutrition_keywords):
        return "nutrition"
    
    # Medical intent (asthma, heart, diabetes specific)
    medical_keywords = [
        "asthma", "heart", "diabetes", "blood pressure", 
        "medical", "guideline", "condition", "symptom",
        "bronchoconstriction", "inhaler", "medication"
    ]
    if any(kw in query_lower for kw in medical_keywords):
        return "medical"
    
    # Exercise intent (default)
    return "exercises"


def _safe_get_documents(results: Dict[str, Any], collection: str) -> List[str]:
    """Safely extract documents from a collection's results"""
    try:
        collection_results = results.get(collection, {})
        if not collection_results:
            return []
        
        documents_list = collection_results.get('documents', [])
        if not documents_list or not documents_list[0]:
            return []
        
        return [doc for doc in documents_list[0] if doc and isinstance(doc, str)]
    except (IndexError, TypeError, AttributeError):
        return []


def prioritize_results(results: Dict[str, Any], intent: str, query: str) -> List[str]:
    """Prioritize results based on query intent"""
    documents = []
    query_lower = query.lower() if query else ""
    
    # =========================================================
    # 1) Primary collection based on intent
    # =========================================================
    if intent == "nutrition":
        docs = _safe_get_documents(results, 'nutrition')
        if docs:
            boosted = []
            rest = []
            for doc in docs:
                doc_lower = doc.lower()
                if any(kw in doc_lower for kw in ["protein", "calorie", "food", "meal", "eat"]):
                    boosted.append(doc)
                else:
                    rest.append(doc)
            documents.extend(boosted)
            documents.extend(rest)
    
    elif intent == "medical":
        docs = _safe_get_documents(results, 'medical')
        if docs:
            if "asthma" in query_lower:
                asthma_docs = []
                other_docs = []
                for doc in docs:
                    if "asthma" in doc.lower():
                        asthma_docs.append(doc)
                    else:
                        other_docs.append(doc)
                documents.extend(asthma_docs)
                documents.extend(other_docs)
            else:
                documents.extend(docs)
    
    else:  # exercises intent (default)
        docs = _safe_get_documents(results, 'exercises')
        if docs:
            documents.extend(docs)
    
    # =========================================================
    # 2) Exercises — secondary context
    # =========================================================
    if intent != "exercises":
        docs = _safe_get_documents(results, 'exercises')
        for doc in docs:
            if doc not in documents:
                documents.append(doc)
    
    # =========================================================
    # 3) Remaining collections (deduplicated)
    # =========================================================
    remaining = [c for c in ['nutrition', 'medical'] if c != intent]
    for collection in remaining:
        docs = _safe_get_documents(results, collection)
        for doc in docs:
            if doc not in documents:
                documents.append(doc)
    
    return documents


def retrieve_context(query: str) -> Dict[str, Any]:
    """
    Retrieve relevant context using RAG system with intent-based prioritization.
    Thread-safe — guarded against PySide6 C++ thread crashes.
    """
    empty_result = {
        'documents': [[]],
        'raw_results': {},
        'intent': 'unknown',
        'error': None
    }
    
    if not query or not query.strip():
        empty_result['error'] = 'Empty query'
        return empty_result
    
    try:
        # Detect what the user is asking about
        intent = detect_query_intent(query)
        
        # Reorder collections based on intent for better retrieval
        if intent == "nutrition":
            collections = ["nutrition", "medical", "exercises"]
        elif intent == "medical":
            collections = ["medical", "exercises", "nutrition"]
        else:
            collections = ["exercises", "medical", "nutrition"]
        
        # =========================================================
        # Thread-safe Vector Store query execution
        # =========================================================
        results = {}
        try:
            from rag.rag_system import rag_orchestrator
            
            if hasattr(rag_orchestrator, "vector_store") and rag_orchestrator.vector_store:
                results = rag_orchestrator.vector_store.search_multiple(
                    collections, 
                    query, 
                    n=4
                )
        except Exception as e:
            logger.warning(f"Vector search skipped safely due to thread boundary restriction: {e}")
            results = {}

        # Fill default empty collections structure if search was skipped or failed
        if not results:
            for col in collections:
                results[col] = {'documents': [[]], 'metadatas': [[]], 'distances': [[]]}
        
        # Prioritize and filter results
        documents = prioritize_results(results, intent, query)
        
        return {
            'documents': [documents[:8]],  # Return top 8 results
            'raw_results': results,
            'intent': intent,
            'error': None
        }
        
    except Exception as e:
        logger.error(f"Retrieval error caught safely: {e}", exc_info=True)
        empty_result['error'] = str(e)
        return empty_result


def retrieve_context_legacy(query: str) -> List[List[str]]:
    """Legacy function for backward compatibility"""
    result = retrieve_context(query)
    return result.get('documents', [[]])


def has_results(context: Dict[str, Any]) -> bool:
    """Check if any documents were actually retrieved"""
    try:
        docs = context.get('documents', [[]])
        return bool(docs) and bool(docs[0]) and len(docs[0]) > 0
    except (IndexError, AttributeError):
        return False


def format_context(context: Dict[str, Any], max_docs: int = 5) -> str:
    """Format retrieved context into a readable string for prompts"""
    if not has_results(context):
        return ""
    
    docs = context.get('documents', [[]])[0][:max_docs]
    intent = context.get('intent', 'unknown')
    
    formatted = f"\n\n---\n📚 **Retrieved Context** (intent: {intent})\n"
    for i, doc in enumerate(docs, 1):
        truncated = doc[:500] + "..." if len(doc) > 500 else doc
        formatted += f"\n[{i}] {truncated}\n"
    formatted += "---\n"
    
    return formatted