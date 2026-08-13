"""
Quick ingestion of text documents into ChromaDB with proper collection routing
Run: python ingest_now.py
"""

import sys
import os
import json
import hashlib
import re
from pathlib import Path

# Setup path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from rag.rag_system import rag_orchestrator
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================
DOCS_DIR = "D:/ED/data/documents/"

# ============================================================================
# SIMPLE LOADING FUNCTIONS
# ============================================================================

def simple_chunk_text(text, chunk_size=1000, overlap=200):
    """
    Simple chunking by size with overlap.
    Good for general text documents.
    """
    words = text.split()
    chunks = []
    
    i = 0
    while i < len(words):
        # Get chunk of words
        chunk_words = words[i:i+chunk_size]
        chunk = " ".join(chunk_words)
        chunks.append(chunk)
        i += chunk_size - overlap
    
    return chunks


def chunk_by_paragraphs(text, min_chars=100, max_chars=2000):
    """
    Chunk by paragraphs (double newlines).
    Merges small paragraphs and splits large ones.
    """
    # Split by double newlines
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        # If adding this paragraph exceeds max, save current chunk
        if len(current_chunk) + len(para) > max_chars and current_chunk:
            if len(current_chunk) >= min_chars:
                chunks.append(current_chunk)
            current_chunk = para
        else:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
    
    # Add last chunk
    if current_chunk and len(current_chunk) >= min_chars:
        chunks.append(current_chunk)
    
    return chunks


def chunk_by_sections(text):
    """
    Chunk by numbered sections (1., 2., 3., etc.)
    """
    # Normalize line endings
    text = text.replace('\r\n', '\n')
    
    # Find section boundaries
    section_pattern = re.compile(r'^\d+\.\s+.+$', re.MULTILINE)
    matches = list(section_pattern.finditer(text))
    
    if len(matches) < 2:
        # Not enough sections, fall back to paragraphs
        return chunk_by_paragraphs(text)
    
    chunks = []
    
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        
        section_text = text[start:end].strip()
        
        if len(section_text) > 50:  # Skip very short sections
            # If section is too long, split further
            if len(section_text) > 2000:
                sub_chunks = chunk_by_paragraphs(section_text)
                chunks.extend(sub_chunks)
            else:
                chunks.append(section_text)
    
    return chunks


# ============================================================================
# COLLECTION ROUTING
# ============================================================================

def determine_collection(fname: str, text: str, metadata: dict) -> str:
    """
    Determine which collection a document belongs to based on:
    1. Filename keywords
    2. Content keywords
    3. Manual metadata override
    
    Returns: "medical", "exercises", or "nutrition"
    """
    fname_lower = fname.lower()
    text_lower = text.lower()[:5000]  # Check first 5000 chars
    
    # Check if metadata explicitly specifies collection
    if "collection" in metadata:
        return metadata["collection"]
    
    # Nutrition indicators
    nutrition_keywords = [
        "nutrition", "diet", "food", "eat", "meal", "protein", "calorie",
        "sugar", "diabetes", "blood sugar", "insulin", "glycemic",
        "vitamin", "mineral", "nutrient", "breakfast", "lunch", "dinner",
        "snack", "carbohydrate", "carbs", "fat", "keto", "vegan"
    ]
    
    # Medical indicators (specific conditions/health issues)
    medical_keywords = [
        "asthma", "respiratory", "bronchoconstriction", "inhaler",
        "heart disease", "cardiovascular", "hypertension", "blood pressure",
        "medical", "guideline", "condition", "symptom", "treatment",
        "disease", "copd", "airway", "wheezing", "medication"
    ]
    
    # Exercise indicators
    exercise_keywords = [
        "exercise", "workout", "training", "cardio", "aerobic",
        "strength", "fitness", "vo2max", "endurance", "stamina",
        "posture", "muscle", "flexibility", "stretching", "yoga",
        "running", "walking", "cycling", "swimming", "hiit",
        "warm-up", "cool-down", "repetition", "sets", "intensity"
    ]
    
    # Count keyword matches
    nutrition_score = sum(1 for kw in nutrition_keywords if kw in fname_lower or kw in text_lower)
    medical_score = sum(1 for kw in medical_keywords if kw in fname_lower or kw in text_lower)
    exercise_score = sum(1 for kw in exercise_keywords if kw in fname_lower or kw in text_lower)
    
    # Filename-based rules (highest priority)
    if "asthma" in fname_lower:
        return "medical"
    if "back_issues" in fname_lower or "knee_issues" in fname_lower:
        return "medical"
    if "sugar" in fname_lower or "diabetes" in fname_lower:
        return "medical"  # Sugar problems often relates to diabetes (medical)
    if "posture" in fname_lower:
        return "exercises"
    if "cardio" in fname_lower or "exercise" in fname_lower:
        return "exercises"
    
    # Content-based decision
    scores = {
        "medical": medical_score,
        "exercises": exercise_score,
        "nutrition": nutrition_score
    }
    
    best_collection = max(scores, key=scores.get)
    
    # If scores are all zero, default to medical
    if scores[best_collection] == 0:
        return "medical"
    
    return best_collection


# ============================================================================
# FILE METADATA (Updated with collection routing)
# ============================================================================

FILE_METADATA = {
    "asthma_guide.txt": {
        "title": "Asthma & Exercise Guide",
        "source": "Medical Research Compilation",
        "category": "Respiratory Health",
        "chunk_method": "paragraphs",
        "collection": "medical",  # Explicitly medical
    },
    "Exercise_1.txt": {
        "title": "Exercise & Health Medical Guide",
        "source": "Compilation of research",
        "category": "General Exercise Science",
        "chunk_method": "sections",
        "collection": "exercises",  # Primarily exercise content
    },
    "Posture_Correction.txt": {
        "title": "Posture Correction: Evidence-Based Practices",
        "source": "Posture Correction Guide",
        "category": "Musculoskeletal Health",
        "chunk_method": "sections",
        "collection": "exercises",  # Exercise/posture related
    },
    "cardio_guides.txt": {
        "title": "Cardio Exercise Guides",
        "source": "Compilation of cardio guidelines",
        "category": "Cardiovascular Health",
        "chunk_method": "paragraphs",
        "collection": "exercises",  # Cardio = exercise
    },
    "High_cardio.txt": {
        "title": "High Intensity Cardio Guide",
        "source": "Cardio Training Compilation",
        "category": "Cardiovascular Health",
        "chunk_method": "paragraphs",
        "collection": "exercises",  # Cardio = exercise
    },
    "back_issues.txt": {
        "title": "Back Issues and Exercise",
        "source": "Medical Compilation",
        "category": "Musculoskeletal Health",
        "chunk_method": "paragraphs",
        "collection": "medical",  # Back problems are medical
    },
    "Knee_issues.txt": {
        "title": "Knee Issues and Exercise",
        "source": "Medical Compilation",
        "category": "Orthopedic Health",
        "chunk_method": "paragraphs",
        "collection": "medical",  # Knee problems are medical
    },
    "sugar_problems.txt": {
        "title": "Blood Sugar Problems and Exercise",
        "source": "Medical Compilation",
        "category": "Metabolic Health",
        "chunk_method": "paragraphs",
        "collection": "medical",  # Blood sugar = diabetes = medical
    },
}


# ============================================================================
# INGESTION
# ============================================================================

def reset_collections():
    """Clear all collections before ingesting"""
    print("\n[RESET] Clearing existing collections...")
    
    vs = rag_orchestrator.vector_store
    
    for name in ["exercises", "nutrition", "medical"]:
        try:
            vs.client.delete_collection(name)
            print(f"  Deleted: {name}")
        except:
            pass
        
        # Recreate empty collection
        vs.collections[name] = vs.client.create_collection(name)
        print(f"  Recreated: {name}")
    
    print("  ✅ Reset complete\n")


def ingest_all_documents():
    """Ingest all text files from documents folder with proper routing"""
    
    print("=" * 80)
    print("INGESTING TEXT DOCUMENTS INTO CHROMADB")
    print("=" * 80)
    
    if not os.path.exists(DOCS_DIR):
        print(f"❌ Documents folder not found: {DOCS_DIR}")
        return 0
    
    # Reset collections first
    reset_collections()
    
    txt_files = [f for f in os.listdir(DOCS_DIR) if f.endswith('.txt')]
    print(f"Found {len(txt_files)} text files\n")
    
    total_chunks = 0
    collection_stats = {"medical": 0, "exercises": 0, "nutrition": 0}
    
    for fname in sorted(txt_files):
        filepath = os.path.join(DOCS_DIR, fname)
        
        print(f"📄 Processing: {fname}")
        print(f"   Size: {os.path.getsize(filepath):,} bytes")
        
        try:
            # Read file
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
            
            # Get metadata
            meta = FILE_METADATA.get(fname, {})
            title = meta.get("title", fname.replace(".txt", "").replace("_", " ").title())
            source = meta.get("source", f"Auto-ingested: {fname}")
            category = meta.get("category", "General")
            chunk_method = meta.get("chunk_method", "paragraphs")
            
            # Determine collection
            collection = determine_collection(fname, text, meta)
            print(f"   Collection: {collection}")
            
            # Chunk the text
            if chunk_method == "sections":
                chunks = chunk_by_sections(text)
            elif chunk_method == "paragraphs":
                chunks = chunk_by_paragraphs(text)
            else:
                chunks = simple_chunk_text(text)
            
            print(f"   Chunks: {len(chunks)}")
            
            # Prepare for ingestion
            docs = []
            metas = []
            ids = []
            
            basename = fname.replace(".txt", "")
            
            for i, chunk in enumerate(chunks):
                if len(chunk.strip()) < 50:
                    continue
                
                docs.append(chunk)
                metas.append({
                    "title": title,
                    "source": source,
                    "category": category,
                    "filename": fname,
                    "chunk_id": i,
                })
                ids.append(f"{basename}_{i}")
            
            # Add to correct collection
            if docs:
                rag_orchestrator.vector_store.add_documents(collection, docs, metas, ids)
                print(f"   ✅ Ingested {len(docs)} chunks into '{collection}'")
                total_chunks += len(docs)
                collection_stats[collection] = collection_stats.get(collection, 0) + len(docs)
            else:
                print(f"   ⚠️ No valid chunks extracted")
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("INGESTION COMPLETE")
    print("=" * 80)
    print(f"Total chunks: {total_chunks}")
    for collection, count in collection_stats.items():
        print(f"  {collection}: {count} chunks")
    
    return total_chunks


def verify_ingestion():
    """Verify documents are in ChromaDB"""
    print("\n[VERIFICATION]")
    
    vs = rag_orchestrator.vector_store
    
    for name, collection in vs.collections.items():
        try:
            count = collection.count()
            print(f"  {name}: {count} documents")
            
            if count > 0:
                # Show sample
                sample = collection.peek(limit=1)
                if sample and sample.get('documents'):
                    print(f"    Sample: {sample['documents'][0][:100]}...")
        except Exception as e:
            print(f"  {name}: Error - {e}")


def test_retrieval():
    """Test retrieval with sample queries"""
    print("\n[TESTING RETRIEVAL]")
    
    try:
        from rag.retriever import retrieve_context
        
        test_queries = [
            "What should someone with asthma know about exercise?",
            "Best cardio exercises",
            "How does air quality affect exercise?",
            "Posture correction tips",
            "Exercises for back pain",
            "Exercises for knee problems",
            "Blood sugar and exercise"
        ]
        
        for query in test_queries:
            print(f"\nQuery: {query}")
            context = retrieve_context(query)
            
            if isinstance(context, dict):
                docs = context.get('documents', [[]])
                if docs and docs[0]:
                    print(f"  ✅ Retrieved {len(docs[0])} documents")
                    print(f"  Intent: {context.get('intent')}")
                    print(f"  Top: {docs[0][0][:100]}...")
                else:
                    print(f"  ❌ No documents")
                    print(f"  Error: {context.get('error')}")
    
    except Exception as e:
        print(f"  ❌ Test failed: {e}")


if __name__ == "__main__":
    chunks = ingest_all_documents()
    
    if chunks > 0:
        verify_ingestion()
        test_retrieval()
    else:
        print("\n❌ No documents were ingested!")
        print("Check if files exist and are readable")