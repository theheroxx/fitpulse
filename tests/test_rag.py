# tests/test_rag.py
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.retriever import retrieve_context
from rag.rag_system import rag_orchestrator


def test_rag_queries():
    """Test RAG retrieval with various queries"""
    
    print("=" * 70)
    print("🔍 RAG SYSTEM TEST - Database Content")
    print("=" * 70)
    
    # First, show what's in the database collections
    print("\n📊 RAG Collection Statistics:")
    print("-" * 40)
    
    for collection_name in ["exercises", "nutrition", "medical"]:
        try:
            collection = rag_orchestrator.vector_store.collections.get(collection_name)
            if collection:
                count = collection.count()
                print(f"   {collection_name}: {count} documents")
        except:
            print(f"   {collection_name}: Not available")
    
    # Test queries
    test_queries = [
        # Exercise-related queries (should hit exercises collection)
        ("🏋️ Exercise Query", "What exercises are good for beginners?"),
        ("🏋️ Exercise Query", "low intensity cardio for heart patients"),
        ("🏋️ Exercise Query", "high intensity workouts for asthma"),
        ("🏋️ Exercise Query", "benefits of swimming"),
        
        # Food/nutrition queries (should hit nutrition collection)
        ("🍽️ Nutrition Query", "high protein foods for muscle recovery"),
        ("🍽️ Nutrition Query", "low glycemic index foods for diabetes"),
        ("🍽️ Nutrition Query", "heart healthy foods"),
        
        # Medical queries (should hit medical collection)
        ("🩺 Medical Query", "asthma exercise guidelines"),
        ("🩺 Medical Query", "HIIT safety for asthma patients"),
        ("🩺 Medical Query", "exercise for heart disease patients"),
        ("🩺 Medical Query", "air quality and outdoor exercise"),
    ]
    
    for category, query in test_queries:
        print(f"\n{'='*60}")
        print(f"{category}: {query}")
        print('='*60)
        
        result = retrieve_context(query)
        
        # Check each collection for results
        collections_found = []
        for collection in ['exercises', 'nutrition', 'medical']:
            if result.get('raw_results', {}).get(collection, {}).get('documents', [[]])[0]:
                collections_found.append(collection)
        
        print(f"📚 Found in collections: {collections_found if collections_found else 'None'}")
        
        # Display top result
        all_docs = result.get('documents', [])
        if all_docs:
            print(f"\n📄 Top Result ({len(all_docs)} total):")
            print("-" * 40)
            print(all_docs[0][:400] + "..." if len(all_docs[0]) > 400 else all_docs[0])
        else:
            print("\n⚠️ No documents found")


def test_medical_specific():
    """Test specifically medical collection (asthma guide)"""
    
    print("\n" + "=" * 70)
    print("🩺 MEDICAL COLLECTION SPECIFIC TESTS")
    print("=" * 70)
    
    medical_queries = [
        "asthma and high intensity exercise",
        "swimming benefits for asthma",
        "exercise-induced bronchoconstriction treatment",
        "asthma attack during workout what to do",
        "cold weather exercise asthma",
    ]
    
    for query in medical_queries:
        print(f"\n📝 Query: {query}")
        print("-" * 50)
        
        # Search only medical collection
        results = rag_orchestrator.vector_store.search("medical", query, n_results=2)
        
        docs = results.get('documents', [[]])[0]
        if docs:
            print(f"✅ Found {len(docs)} results")
            print(f"   {docs[0][:200]}...")
        else:
            print("⚠️ No results found")


def test_exercise_specific():
    """Test specifically exercise collection from database"""
    
    print("\n" + "=" * 70)
    print("🏋️ EXERCISE COLLECTION SPECIFIC TESTS")
    print("=" * 70)
    
    # First, list what exercises are in the database
    print("\n📋 Exercises in database:")
    print("-" * 40)
    
    try:
        from database.exercise import get_all_exercises
        exercises = get_all_exercises()
        for ex in exercises[:10]:  # Show first 10
            print(f"   • {ex.get('name')} ({ex.get('intensity', 'N/A')} intensity)")
        print(f"\n   Total: {len(exercises)} exercises")
    except Exception as e:
        print(f"   Error loading exercises: {e}")
    
    # Test specific exercise queries
    exercise_queries = [
        "walking",
        "running",
        "yoga",
        "strength training",
    ]
    
    for query in exercise_queries:
        print(f"\n📝 Query: {query}")
        print("-" * 50)
        
        results = rag_orchestrator.vector_store.search("exercises", query, n_results=2)
        
        docs = results.get('documents', [[]])[0]
        if docs:
            print(f"✅ Found:")
            for doc in docs:
                # Extract exercise name from the document
                lines = doc.split('\n')
                for line in lines:
                    if line.startswith('Exercise:'):
                        print(f"   {line}")
                        break
        else:
            print("⚠️ No results found")


# Test nutrition
result = retrieve_context("high protein foods")
print(f"Intent: {result['intent']}")  # Should be "nutrition"

# Test medical
result = retrieve_context("asthma exercise guidelines")
print(f"Intent: {result['intent']}")  # Should be "medical"

# Test exercise
result = retrieve_context("walking")
print(f"Intent: {result['intent']}")  # Should be "exercises"

if __name__ == "__main__":
    # Run all tests
    test_rag_queries()
    test_medical_specific()
    test_exercise_specific()
    
    print("\n" + "=" * 70)
    print("✅ RAG Testing Complete")
    print("=" * 70)