"""
FastAPI server for RAG system
Provides endpoints for document ingestion and RAG queries
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uvicorn
import os
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# Lazy imports to prevent startup crashes
# ============================================================================
_rag_orchestrator = None
_retriever = None
_query_builder = None

def get_rag():
    """Lazy-load the RAG orchestrator"""
    global _rag_orchestrator
    if _rag_orchestrator is None:
        from rag.rag_system import rag_orchestrator
        _rag_orchestrator = rag_orchestrator
    return _rag_orchestrator

def get_retriever():
    """Lazy-load the retriever"""
    global _retriever
    if _retriever is None:
        from rag.retriever import retrieve_context, has_results
        _retriever = {'retrieve_context': retrieve_context, 'has_results': has_results}
    return _retriever

def get_query_builder():
    """Lazy-load the query builder"""
    global _query_builder
    if _query_builder is None:
        from rag.query_builder import build_query, get_rag_context, generate_rag_response
        _query_builder = {
            'build_query': build_query,
            'get_rag_context': get_rag_context,
            'generate_rag_response': generate_rag_response
        }
    return _query_builder


app = FastAPI(
    title="Fitness AI RAG API",
    description="Retrieval-Augmented Generation API for Fitness AI",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Pydantic models
# ============================================================================
class UserProfile(BaseModel):
    Age: Optional[int] = None
    HealthCondition: Optional[str] = None
    FitnessLevel: Optional[str] = None

class DetectorOutput(BaseModel):
    label: str
    reasons: List[str]

class RAGQuery(BaseModel):
    user_profile: UserProfile
    detector_output: DetectorOutput
    user_query: str

class DocumentMetadata(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    source: Optional[str] = None

class ExerciseData(BaseModel):
    name: str
    type: str
    intensity: str
    duration: str
    benefits: str
    precautions: str

class NutritionData(BaseModel):
    name: str
    category: str
    calories: float
    protein: float
    carbs: float
    fat: float
    benefits: str

class HealthResponse(BaseModel):
    status: str
    rag_available: bool
    chroma_available: bool
    collections: Dict[str, int]
    error: Optional[str] = None

class RAGResponse(BaseModel):
    success: bool
    response: str
    context_used: Dict[str, Any]
    intent: Optional[str] = None
    document_count: int = 0

# ============================================================================
# API Routes
# ============================================================================
@app.get("/")
async def root():
    """Basic health check"""
    return {"message": "Fitness AI RAG API is running", "status": "healthy"}

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """
    Detailed health check endpoint
    Returns RAG system status and collection stats
    """
    try:
        rag = get_rag()
        
        # Check ChromaDB heartbeat
        chroma_ok = False
        try:
            chroma_ok = rag.vector_store.heartbeat()
        except Exception as e:
            logger.warning(f"ChromaDB heartbeat failed: {e}")
        
        # Get collection stats
        stats = {}
        if chroma_ok:
            try:
                for name, collection in rag.vector_store.collections.items():
                    try:
                        stats[name] = collection.count()
                    except:
                        stats[name] = -1  # Unknown
            except Exception as e:
                logger.warning(f"Failed to get collection stats: {e}")
        
        # Also check JSON fallback files
        json_dir = Path("./data/chroma_db")
        if json_dir.exists():
            for json_file in json_dir.glob("*.json"):
                name = json_file.stem
                if name not in stats:
                    try:
                        import json
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        stats[name] = len(data)
                    except:
                        stats[name] = -1
        
        return HealthResponse(
            status="healthy",
            rag_available=True,
            chroma_available=chroma_ok,
            collections=stats,
            error=None
        )
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="degraded",
            rag_available=False,
            chroma_available=False,
            collections={},
            error=str(e)
        )

@app.post("/api/rag/query", response_model=RAGResponse)
async def rag_query(query: RAGQuery):
    """
    Main RAG query endpoint
    Retrieves context and generates response
    """
    try:
        qb = get_query_builder()
        ret = get_retriever()
        
        # Convert to dict format
        user_profile = query.user_profile.model_dump() if hasattr(query.user_profile, 'model_dump') else query.user_profile.dict()
        detector_output = query.detector_output.model_dump() if hasattr(query.detector_output, 'model_dump') else query.detector_output.dict()

        # Get RAG context using query builder
        context = qb['get_rag_context'](user_profile, detector_output, query.user_query)

        # Generate response
        response = qb['generate_rag_response'](context, query.user_query)

        # Get document count
        doc_count = 0
        try:
            if ret['has_results'](context):
                doc_count = len(context.get('documents', [[]])[0])
        except:
            pass

        return RAGResponse(
            success=True,
            response=response,
            context_used={
                "vector_collections": list(context.get('raw_results', {}).keys()),
                "has_context": ret['has_results'](context),
            },
            intent=context.get('intent', 'unknown'),
            document_count=doc_count
        )

    except Exception as e:
        logger.error(f"RAG query error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"RAG query failed: {str(e)}")

@app.post("/api/documents/upload-paper")
async def upload_paper(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = None
):
    """
    Upload and process a research paper PDF
    """
    try:
        # Validate file type
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

        # Validate file size (max 50MB)
        content = await file.read()
        if len(content) > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 50MB)")

        # Save file temporarily
        upload_dir = Path("uploads/papers")
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize filename
        safe_filename = Path(file.filename).name
        file_path = upload_dir / safe_filename

        with open(file_path, "wb") as buffer:
            buffer.write(content)

        # Process in background
        background_tasks.add_task(process_paper_background, str(file_path), title)

        return {
            "success": True,
            "message": f"Paper '{file.filename}' uploaded and processing started",
            "file_path": str(file_path)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Paper upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/api/data/add-exercises")
async def add_exercises(exercises: List[ExerciseData]):
    """
    Add exercise data to vector store
    """
    try:
        rag = get_rag()
        exercise_dicts = [exercise.model_dump() if hasattr(exercise, 'model_dump') else exercise.dict() for exercise in exercises]
        rag.add_exercise_data(exercise_dicts)

        return {
            "success": True,
            "message": f"Added {len(exercises)} exercises to knowledge base",
            "count": len(exercises)
        }

    except Exception as e:
        logger.error(f"Add exercises error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to add exercises: {str(e)}")

@app.post("/api/data/add-nutrition")
async def add_nutrition(foods: List[NutritionData]):
    """
    Add nutrition data to vector store
    """
    try:
        rag = get_rag()
        food_dicts = [food.model_dump() if hasattr(food, 'model_dump') else food.dict() for food in foods]
        rag.add_nutrition_data(food_dicts)

        return {
            "success": True,
            "message": f"Added {len(foods)} foods to knowledge base",
            "count": len(foods)
        }

    except Exception as e:
        logger.error(f"Add nutrition error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to add nutrition data: {str(e)}")

@app.get("/api/search/{collection}")
async def search_collection(collection: str, query: str, limit: int = 5):
    """
    Search specific collection
    """
    try:
        valid_collections = ["papers", "exercises", "nutrition", "medical"]
        if collection not in valid_collections:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid collection '{collection}'. Valid: {valid_collections}"
            )

        if not query or not query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        rag = get_rag()
        results = rag.vector_store.search(collection, query, limit)

        return {
            "success": True,
            "collection": collection,
            "query": query,
            "results": results
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/api/stats")
async def get_stats():
    """
    Get RAG system statistics
    """
    try:
        rag = get_rag()
        stats = {}
        total_docs = 0
        
        # Get ChromaDB stats
        for collection_name, collection in rag.vector_store.collections.items():
            try:
                count = collection.count()
                stats[collection_name] = count
                total_docs += count
            except Exception as e:
                logger.warning(f"Failed to count collection '{collection_name}': {e}")
                stats[collection_name] = -1
        
        # Also check JSON fallback files
        json_dir = Path("./data/chroma_db")
        if json_dir.exists():
            for json_file in json_dir.glob("*.json"):
                name = json_file.stem
                if name not in stats:
                    try:
                        import json
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        stats[name] = len(data)
                        total_docs += len(data)
                    except:
                        stats[name] = -1
        
        return {
            "success": True,
            "stats": stats,
            "total_documents": total_docs,
            "chroma_available": rag.vector_store._initialized,
            "chroma_path": str(rag.vector_store.persist_directory)
        }

    except Exception as e:
        logger.error(f"Stats error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@app.get("/api/retrieve")
async def direct_retrieve(query: str, limit: int = 5):
    """
    Direct retrieval endpoint — returns raw documents without LLM
    Useful for debugging and testing the retriever
    """
    try:
        if not query or not query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        ret = get_retriever()
        context = ret['retrieve_context'](query)
        
        docs = context.get('documents', [[]])[0][:limit]
        
        return {
            "success": True,
            "query": query,
            "intent": context.get('intent', 'unknown'),
            "document_count": len(docs),
            "documents": docs,
            "error": context.get('error')
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Direct retrieve error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")

# ============================================================================
# Background tasks
# ============================================================================
def process_paper_background(file_path: str, title: str = None):
    """Process paper in background"""
    try:
        logger.info(f"Processing paper: {file_path}")
        rag = get_rag()
        rag.add_paper(file_path, title)
        logger.info(f"Successfully processed paper: {file_path}")

        # Clean up file after processing
        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        logger.error(f"Background processing failed for {file_path}: {e}", exc_info=True)

# ============================================================================
# Startup event
# ============================================================================
@app.on_event("startup")
async def startup_event():
    """Initialize RAG system on startup"""
    try:
        logger.info("Initializing RAG system...")
        
        rag = get_rag()
        
        # Check if ChromaDB is available
        if rag.vector_store._initialized:
            try:
                rag.vector_store.heartbeat()
                logger.info("✅ ChromaDB connected")
            except Exception as e:
                logger.warning(f"⚠️ ChromaDB heartbeat failed: {e}")
        else:
            logger.warning("⚠️ ChromaDB not initialized — using JSON fallback")
        
        # Log collection stats
        stats = {}
        for name, collection in rag.vector_store.collections.items():
            try:
                stats[name] = collection.count()
            except:
                stats[name] = "unknown"
        
        logger.info(f"📊 Collections: {stats}")
        logger.info("✅ RAG system initialized successfully")
    
    except Exception as e:
        logger.error(f"❌ Failed to initialize RAG system: {e}", exc_info=True)
        # Don't crash — let the server start anyway

# ============================================================================
# Shutdown event
# ============================================================================
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down RAG API...")
    # ChromaDB PersistentClient auto-closes, but we can add cleanup here if needed

# ============================================================================
# Main
# ============================================================================
if __name__ == "__main__":
    uvicorn.run(
        "rag_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )