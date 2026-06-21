# rag/rag_server.py
"""Standalone RAG server"""
import os
import sys
import json
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['CHROMA_TELEMETRY'] = 'False'

from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings as ChromaSettings

# Load model
model_path = os.path.join(os.path.dirname(__file__), "msmarco-distilbert-base-v4")
if os.path.exists(model_path):
    model = SentenceTransformer(model_path, device='cpu')
else:
    model = SentenceTransformer("msmarco-distilbert-base-v4", device='cpu')

print(f"[SERVER] Model loaded", file=sys.stderr, flush=True)

# Connect to ChromaDB with FRESH database if corrupted
db_path = "./data/chroma_db"
try:
    client = chromadb.PersistentClient(
        path=db_path,
        settings=ChromaSettings(anonymized_telemetry=False)
    )
except Exception:
    print(f"[SERVER] Database corrupted, recreating...", file=sys.stderr, flush=True)
    shutil.rmtree(db_path, ignore_errors=True)
    client = chromadb.PersistentClient(
        path=db_path,
        settings=ChromaSettings(anonymized_telemetry=False)
    )

collections = {}
for name in ["medical", "exercises", "nutrition"]:
    try:
        collections[name] = client.get_collection(name)
        count = collections[name].count()
        print(f"[SERVER] {name}: {count} docs", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"[SERVER] {name}: creating new collection", file=sys.stderr, flush=True)
        try:
            # Delete if exists and recreate
            client.delete_collection(name)
        except:
            pass
        collections[name] = client.create_collection(name)

print("RAG_SERVER_READY", flush=True)

# Read queries from stdin
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    
    try:
        request = json.loads(line)
        query = request.get('query', '')
        
        q_emb = model.encode([query]).tolist()
        
        all_docs = []
        for name, col in collections.items():
            try:
                results = col.query(query_embeddings=q_emb, n_results=4, include=['documents'])
                all_docs.extend(results.get('documents', [[]])[0])
            except Exception as e:
                print(f"[SERVER] {name} query error: {e}", file=sys.stderr, flush=True)
        
        seen = set()
        unique = []
        for doc in all_docs:
            if doc not in seen:
                seen.add(doc)
                unique.append(doc)
        
        print(json.dumps({'documents': unique[:8]}), flush=True)
        
    except Exception as e:
        print(json.dumps({'error': str(e), 'documents': []}), flush=True)