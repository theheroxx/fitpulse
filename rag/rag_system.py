# rag/rag_system.py

# ============================================================================
# ENVIRONMENT & THREADING GUARDS
# ============================================================================
import os

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

os.environ['CHROMA_TELEMETRY'] = 'False'
os.environ['ANONYMIZED_TELEMETRY'] = 'False'
os.environ['POSTHOG_API_KEY'] = ''
os.environ['POSTHOG_HOST'] = ''

# ============================================================================
# PERMANENT SQLITE PATCH
# ============================================================================
import sqlite3 as _sqlite3
_original_connect = _sqlite3.connect
def _patched_connect(*args, **kwargs):
    kwargs['check_same_thread'] = False
    return _original_connect(*args, **kwargs)
_sqlite3.connect = _patched_connect

import warnings
warnings.filterwarnings("ignore")

import json
import threading
from typing import List, Dict, Any
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
except ImportError:
    pass

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE = True
except ImportError:
    HAS_SENTENCE = False

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    HAS_CHROMA = True
except ImportError:
    HAS_CHROMA = False


class EmbeddingManager:
    """Thread-safe singleton — CPU only"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is not None:
            return cls._instance
        with cls._lock:
            if cls._instance is None:
                obj = super().__new__(cls)
                obj.model = None
                obj._loaded = False
                cls._instance = obj
        return cls._instance
    
    def load(self):
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            if not HAS_SENTENCE:
                self._loaded = True
                return
            try:
                local = os.path.join(os.path.dirname(__file__), "msmarco-distilbert-base-v4")
                if os.path.exists(local):
                    self.model = SentenceTransformer(local, device='cpu')
                else:
                    self.model = SentenceTransformer("msmarco-distilbert-base-v4", device='cpu')
                logger.info("✅ Embedding model loaded on CPU")
            except Exception as e:
                logger.warning(f"Model failed: {e}")
            self._loaded = True
    
    def encode(self, texts, batch_size=32):
        self.load()
        if self.model is None:
            return [[0.0] * 384 for _ in texts]
        with self._lock:
            try:
                return self.model.encode(texts, batch_size=batch_size, show_progress_bar=False).tolist()
            except Exception:
                return [[0.0] * 384 for _ in texts]
    
    def encode_single(self, text):
        return self.encode([text])[0]


class VectorStore:
    """Thread-safe vector store"""
    
    def __init__(self, persist_directory="./data/chroma_db"):
        self.dir = Path(persist_directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.client = None
        self.collections = {}
        self._ok = False
        self._lock = threading.Lock()
        self._init()
    
    def _init(self):
        if not HAS_CHROMA:
            return
        try:
            self.client = chromadb.PersistentClient(
                path=str(self.dir),
                settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True)
            )
            for name in ["exercises", "nutrition", "medical"]:
                try:
                    self.collections[name] = self.client.get_collection(name)
                except Exception:
                    self.collections[name] = self.client.create_collection(name)
            self._ok = True
            logger.info("✅ ChromaDB initialized")
        except Exception as e:
            logger.warning(f"ChromaDB failed: {e}")
    
    def add_documents(self, col, docs, metas, ids):
        if not self._ok or col not in self.collections:
            self._json_save(col, docs, metas, ids)
            return
        with self._lock:
            try:
                emb = EmbeddingManager()
                embeddings = emb.encode(docs)
                self.collections[col].add(
                    embeddings=embeddings,
                    documents=docs,
                    metadatas=metas,
                    ids=ids
                )
                logger.info(f"✅ Added {len(docs)} to {col}")
            except Exception as e:
                logger.warning(f"Add to {col} failed: {e}")
                self._json_save(col, docs, metas, ids)
    
    def _json_save(self, col, docs, metas, ids):
        f = self.dir / f"{col}.json"
        with self._lock:
            data = []
            if f.exists():
                try:
                    data = json.load(open(f, encoding='utf-8'))
                except Exception:
                    pass
            for d, m, i in zip(docs, metas, ids):
                data.append({'id': i, 'document': d, 'metadata': m})
            json.dump(data, open(f, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
            logger.info(f"✅ Saved {len(docs)} to {f}")
    
    def search(self, col, query, n=5):
        j = self._json_search(col, query, n)
        if j['documents'][0]:
            return j
        if self._ok and col in self.collections:
            with self._lock:
                try:
                    emb = EmbeddingManager()
                    q_emb = emb.encode_single(query)
                    return self.collections[col].query(
                        query_embeddings=[q_emb],
                        n_results=n,
                        include=['documents', 'metadatas', 'distances']
                    )
                except Exception:
                    pass
        return {'documents': [[]], 'metadatas': [[]], 'distances': [[]]}
    
    def _json_search(self, col, query, n):
        f = self.dir / f"{col}.json"
        if not f.exists():
            return {'documents': [[]], 'metadatas': [[]], 'distances': [[]]}
        try:
            data = json.load(open(f, encoding='utf-8'))
            words = query.lower().split()
            scored = []
            for item in data:
                doc = item['document'].lower()
                s = sum(1 for w in words if w in doc)
                if s:
                    scored.append((s, item))
            scored.sort(key=lambda x: x[0], reverse=True)
            top = [m for _, m in scored[:n]]
            return {'documents': [[t['document'] for t in top]], 'metadatas': [[t['metadata'] for t in top]], 'distances': [[0.1] * len(top)]}
        except Exception:
            return {'documents': [[]], 'metadatas': [[]], 'distances': [[]]}
    
    def search_multiple(self, cols, query, n=3):
        return {c: self.search(c, query, n) for c in cols}


class RAGOrchestrator:
    def __init__(self):
        self._vs = None
        self._lock = threading.Lock()
    
    @property
    def vector_store(self):
        if self._vs is None:
            with self._lock:
                if self._vs is None:
                    self._vs = VectorStore()
        return self._vs
    
    def add_exercise_data(self, exercises):
        docs, metas, ids = [], [], []
        for i, ex in enumerate(exercises):
            doc_text = f"""Exercise: {ex.get('name','')}
Type: {ex.get('type','')}
Intensity: {ex.get('intensity','')}
Duration: {ex.get('duration','')}
Benefits: {ex.get('benefits','')}
Precautions: {ex.get('precautions','')}"""
            docs.append(doc_text)
            metas.append(ex.copy())
            ids.append(f"exercise_{i}")
        self.vector_store.add_documents("exercises", docs, metas, ids)
    
    def add_nutrition_data(self, foods):
        docs, metas, ids = [], [], []
        for i, food in enumerate(foods):
            doc_text = f"""Food: {food.get('name','')}
Category: {food.get('category','')}
Calories: {food.get('calories',0)} per 100g
Protein: {food.get('protein',0)}g
Carbs: {food.get('carbs',0)}g
Fat: {food.get('fat',0)}g
Benefits: {food.get('benefits','')}"""
            docs.append(doc_text)
            metas.append(food.copy())
            ids.append(f"nutrition_{i}")
        self.vector_store.add_documents("nutrition", docs, metas, ids)


rag_orchestrator = RAGOrchestrator()