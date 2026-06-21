# tests/test_rag_llm.py
"""
Simple test of RAG retrieval + Ollama LLM without any Qt/UI.
Run from the project root: python tests/test_rag_llm.py
"""

import sys
import os

# Add project root to path (go up from tests/ to project root)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Verify path
print(f"Project root: {sys.path[0]}")

# Disable telemetry
os.environ['CHROMA_TELEMETRY'] = 'False'
os.environ['ANONYMIZED_TELEMETRY'] = 'False'

print("=" * 60)
print("🔧 RAG + LLM TEST (No UI)")
print("=" * 60)

# =========================================================
# Step 1: Initialize RAG
# =========================================================
print("\n[1] Initializing RAG system...")
try:
    from rag.rag_system import rag_orchestrator
    vs = rag_orchestrator.vector_store
    print(f"    ChromaDB initialized: {vs._initialized}")
except Exception as e:
    print(f"    ❌ ChromaDB failed: {e}")
    import traceback
    traceback.print_exc()

# =========================================================
# Step 2: Load embedding model
# =========================================================
print("\n[2] Loading embedding model...")
try:
    from rag.rag_system import EmbeddingManager
    emb = EmbeddingManager()
    test_emb = emb.encode(["test"])
    print(f"    ✅ Model loaded. Embedding dim: {len(test_emb[0])}")
except Exception as e:
    print(f"    ❌ Model load failed: {e}")

# =========================================================
# Step 3: Test RAG retrieval
# =========================================================
print("\n[3] Testing RAG retrieval...")

test_queries = [
    "Is running safe with asthma?",
    "What should I eat before exercise?",
    "Best cardio workout for beginners"
]

for query in test_queries:
    print(f"\n    Query: '{query}'")
    try:
        from rag.retriever import retrieve_context
        result = retrieve_context(query)
        
        docs = result.get('documents', [[]])[0]
        intent = result.get('intent', 'unknown')
        
        print(f"    Intent: {intent}")
        print(f"    Documents found: {len(docs)}")
        
        if docs:
            print(f"    First doc preview: {docs[0][:100]}...")
        else:
            print("    ⚠️ No documents found")
            
    except Exception as e:
        print(f"    ❌ Retrieval error: {e}")

# =========================================================
# Step 4: Test Ollama connection
# =========================================================
print("\n[4] Testing Ollama connection...")
try:
    import ollama
    client = ollama.Client(host='http://127.0.0.1:11434')
    
    # List available models
    models = client.list()
    print(f"    Available models: {[m['name'] for m in models.get('models', [])]}")
    
    # Test generate
    test_response = client.generate(
        model='gemma3:4b',
        prompt='Say hello in one word.',
        options={'max_tokens': 10}
    )
    print(f"    Test response: {test_response['response'].strip()}")
    print("    ✅ Ollama working")
    
except Exception as e:
    print(f"    ❌ Ollama error: {e}")

# =========================================================
# Step 5: Full RAG + LLM pipeline
# =========================================================
print("\n[5] Testing FULL RAG + LLM pipeline...")

# Simulate a user profile
user_context = """
User Profile: 35 years old, asthma, intermediate fitness
Activity: running
Environmental Risk: 45/100 (moderate)
"""

question = "Is it safe for me to run outside today?"

print(f"    User: {question}")

# Get RAG context
try:
    from rag.retriever import retrieve_context
    search_query = f"{question} asthma running fitness safety"
    result = retrieve_context(search_query)
    
    docs = result.get('documents', [[]])[0]
    
    if docs:
        rag_context = "\n\n---\n📚 Medical Context:\n" + "\n".join(docs[:3]) + "\n---\n"
        print(f"    RAG: Found {len(docs)} documents")
    else:
        rag_context = ""
        print("    RAG: No documents found")
    
    # Build prompt
    prompt = f"""You are an AI fitness coach using EVIDENCE-BASED MEDICAL CONTEXT.

{user_context}

{rag_context}

User question: {question}

Provide a DETAILED, SCIENTIFIC answer based on the retrieved medical context above."""

    # Send to Ollama
    import ollama
    client = ollama.Client(host='http://127.0.0.1:11434')
    
    print("    Sending to Ollama...")
    response = client.generate(
        model='gemma3:4b',
        prompt=prompt,
        options={'temperature': 0.7, 'max_tokens': 300}
    )
    
    print(f"\n    🤖 AI Response:\n    {response['response'].strip()}")
    
except Exception as e:
    print(f"    ❌ Pipeline error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("✅ TEST COMPLETE")
print("=" * 60)