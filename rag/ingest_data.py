"""
Data Ingestion Script for RAG System
Populates vector store with data from actual databases
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag.rag_system import rag_orchestrator
from database.db import get_db
from database.exercise import get_all_exercises
from database.food import get_all_foods
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_exercises_from_db():
    """Load exercises directly from database"""
    try:
        exercises = get_all_exercises()
        if exercises:
            return exercises
        else:
            logger.warning("No exercises found in database")
            return []
    except Exception as e:
        logger.error(f"Failed to load exercises from database: {e}")
        return []


def load_foods_from_db():
    """Load foods directly from database"""
    try:
        foods = get_all_foods()
        if foods:
            return foods
        else:
            logger.warning("No foods found in database")
            return []
    except Exception as e:
        logger.error(f"Failed to load foods from database: {e}")
        return []


def load_medical_guidelines_from_db():
    """Load medical guidelines from database (if you have them)"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT title, content, source, category
                FROM medical_guidelines
            """)
            rows = cursor.fetchall()
            if rows:
                return [dict(row) for row in rows]
    except Exception as e:
        logger.warning(f"No medical_guidelines table found or error loading: {e}")
    
    # Fallback to sample guidelines if no database table exists
    return get_sample_medical_guidelines()


def get_sample_medical_guidelines():
    """Fallback sample medical guidelines"""
    return [
        {
            "title": "Asthma and Exercise",
            "content": """
            For individuals with asthma, exercise can be beneficial but requires careful management.
            Key recommendations:
            - Choose low to moderate intensity activities
            - Avoid exercising in cold, dry air
            - Warm up properly before exercise
            - Use inhaler 15-30 minutes before exercise if prescribed
            - Stop if symptoms worsen and seek medical attention
            - Swimming is often well-tolerated due to humid environment
            """,
            "source": "American Lung Association",
            "category": "Respiratory Health"
        },
        {
            "title": "Heart Disease and Physical Activity",
            "content": """
            Regular physical activity is crucial for heart health but must be approached carefully.
            Guidelines:
            - Consult cardiologist before starting exercise program
            - Start with low intensity activities like walking
            - Monitor heart rate and symptoms during exercise
            - Stop immediately if experiencing chest pain, shortness of breath, or dizziness
            - Include both aerobic and strength training
            - Stay hydrated and avoid extreme temperatures
            """,
            "source": "American Heart Association",
            "category": "Cardiovascular Health"
        },
        {
            "title": "Diabetes and Exercise",
            "content": """
            Exercise is important for blood sugar control in diabetes management.
            Important considerations:
            - Monitor blood sugar before, during, and after exercise
            - Carry fast-acting glucose for hypoglycemia
            - Start slowly and build up gradually
            - Include both aerobic and resistance training
            - Stay hydrated and be aware of heat effects on insulin
            - Consult healthcare provider for personalized plan
            """,
            "source": "American Diabetes Association",
            "category": "Metabolic Health"
        },
        {
            "title": "Air Quality and Outdoor Exercise",
            "content": """
            Poor air quality can significantly impact exercise safety and effectiveness.
            Recommendations:
            - Check air quality index (AQI) before outdoor activities
            - Avoid exercise when AQI > 100 (unhealthy)
            - Choose indoor alternatives on poor air quality days
            - Use N95 masks if exercising in polluted areas
            - Reduce intensity and duration during poor air quality
            - Stay hydrated as respiratory issues increase fluid needs
            """,
            "source": "Environmental Protection Agency",
            "category": "Environmental Health"
        }
    ]


def load_asthma_exercise_guide():
    """Load the detailed asthma exercise guide from text file"""
    doc_path = "D:/ED/data/documents/asthma_guide.txt"
    
    if not os.path.exists(doc_path):
        logger.warning(f"Asthma guide not found at {doc_path}")
        return [], [], []
    
    with open(doc_path, "r", encoding="utf-8") as f:
        text = f.read()
    
    # Split into meaningful chunks (by double newline)
    chunks = [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]
    
    documents = []
    metadatas = []
    ids = []
    
    for i, chunk in enumerate(chunks):
        documents.append(chunk)
        metadatas.append({
            "title": "Asthma & Exercise Guide",
            "source": "Medical Research Compilation",
            "category": "Respiratory Health",
            "chunk_id": i,
            "topic": "asthma_cardio"
        })
        ids.append(f"asthma_guide_{i}")
    
    return documents, metadatas, ids

def load_posture_correction_guide():
    """Load the posture correction guide from text file"""
    doc_path = "D:/ED/data/documents/Posture_Correction.txt"
    
    if not os.path.exists(doc_path):
        logger.warning(f"Posture guide not found at {doc_path}")
        return [], [], []
    
    with open(doc_path, "r", encoding="utf-8") as f:
        text = f.read()
    
    # Split into sections (numbered headings 1., 2., etc.)
    sections = re.split(r'\n(\d+\.\s+[^\n]+)\n', text)
    
    documents = []
    metadatas = []
    ids = []
    
    for i in range(1, len(sections), 2):
        heading = sections[i].strip()
        content = sections[i+1].strip() if i+1 < len(sections) else ""
        if not content:
            continue
        
        # Determine category
        heading_lower = heading.lower()
        if "understanding" in heading_lower or "causes" in heading_lower:
            category = "Posture Fundamentals"
        elif "exercise" in heading_lower or "key exercises" in heading_lower:
            category = "Posture Exercises"
        elif "special-population" in heading_lower:
            category = "Special Populations"
        else:
            category = "Posture Correction"
        
        documents.append(f"{heading}\n{content}")
        metadatas.append({
            "title": "Posture Correction: Evidence-Based Practices",
            "source": "Posture Correction Guide",
            "category": category,
            "section_heading": heading,
        })
        ids.append(f"posture_guide_{i}")
    
    return documents, metadatas, ids


def load_exercise_medical_guide(doc_path: str = "D:/ED/data/documents/Exercise_1.txt"):
    """
    Load the comprehensive exercise medical guide (pollution, diabetes, heart, age, diet, VO2max).
    Splits into sections based on numbered headings (1., 2., ...).
    Returns (documents, metadatas, ids).
    """
    if not os.path.exists(doc_path):
        logger.warning(f"Exercise medical guide not found at {doc_path}")
        return [], [], []
    
    with open(doc_path, "r", encoding="utf-8") as f:
        text = f.read()
    
    # Normalize line endings
    text = text.replace('\r\n', '\n')
    
    # Split by major section headings like "1. High-cardio exercise in polluted air"
    # Use regex to capture heading + following content until next heading or end
    section_pattern = r'\n(\d+\.\s+[^\n]+)\n(.*?)(?=\n\d+\.\s+|\Z)'
    matches = re.findall(section_pattern, text, re.DOTALL)
    
    documents = []
    metadatas = []
    ids = []
    
    for i, (heading, content) in enumerate(matches):
        heading = heading.strip()
        content = content.strip()
        if not content:
            continue
        
        # Determine category from heading
        heading_lower = heading.lower()
        if "polluted air" in heading_lower:
            category = "Air Pollution & Exercise"
            topic = "pollution_exercise"
        elif "diabetes" in heading_lower:
            category = "Diabetes & Exercise"
            topic = "diabetes_workouts"
        elif "heart problems" in heading_lower or "heart conditions" in heading_lower:
            category = "Heart Conditions & Exercise"
            topic = "cardiac_rehab"
        elif "exercise efficacy by age/time" in heading_lower:
            category = "Age & Timing"
            topic = "exercise_timing"
        elif "diets for athletes" in heading_lower:
            category = "Sports Nutrition"
            topic = "athlete_diet"
        elif "maximizing vo₂max" in heading_lower or "vo₂max" in heading_lower:
            category = "Cardiorespiratory Fitness"
            topic = "vo2max_training"
        else:
            category = "General Exercise Science"
            topic = "general"
        
        # Split long sections into sub-chunks by double newline (preserve citations)
        sub_chunks = [sub.strip() for sub in content.split("\n\n") if sub.strip()]
        for j, sub_chunk in enumerate(sub_chunks):
            full_chunk = f"{heading}\n{sub_chunk}"
            documents.append(full_chunk)
            metadatas.append({
                "title": "Exercise & Health Medical Guide",
                "source": "Compilation of research (see embedded citations)",
                "category": category,
                "topic": topic,
                "section_heading": heading,
                "chunk_id": j,
            })
            ids.append(f"medical_guide_{topic}_{i}_{j}")
    
    # Also capture the executive summary if present
    if "Executive Summary" in text:
        summary_start = text.find("Executive Summary")
        if summary_start != -1:
            summary_text = text[summary_start:].strip()
            # Trim to reasonable length (first 2000 chars)
            if len(summary_text) > 2000:
                summary_text = summary_text[:2000] + "..."
            documents.append(summary_text)
            metadatas.append({
                "title": "Exercise & Health Medical Guide",
                "source": "Compilation of research",
                "category": "Summary",
                "topic": "executive_summary",
                "chunk_id": 0,
            })
            ids.append("medical_guide_executive_summary")
    
    logger.info(f"Loaded {len(documents)} chunks from Exercise_1.txt")
    return documents, metadatas, ids


def ingest_data():
    """Main data ingestion function - loads from actual databases"""
    try:
        logger.info("Starting data ingestion from databases...")

        # =========================================================
        # 1) Load exercises from database
        # =========================================================
        exercises = load_exercises_from_db()
        
        if exercises:
            # Convert database format to RAG format if needed
            rag_exercises = []
            for ex in exercises:
                rag_exercises.append({
                    "name": ex.get("name", ""),
                    "type": ex.get("type", ""),
                    "intensity": ex.get("intensity", ""),
                    "duration": f"{ex.get('duration_minutes', 30)} minutes",
                    "benefits": ex.get("benefits", ""),
                    "precautions": ex.get("precautions", "")
                })
            rag_orchestrator.add_exercise_data(rag_exercises)
            logger.info(f"✅ Ingested {len(rag_exercises)} exercises from database")
        else:
            logger.warning("⚠️ No exercises found in database - skipping")

        # =========================================================
        # 2) Load foods from database
        # =========================================================
        foods = load_foods_from_db()
        
        if foods:
            # Convert database format to RAG format if needed
            rag_foods = []
            for food in foods:
                rag_foods.append({
                    "name": food.get("name", ""),
                    "category": food.get("category", ""),
                    "calories": food.get("calories_per_100g", 0),
                    "protein": food.get("protein_g", 0),
                    "carbs": food.get("carbs_g", 0),
                    "fat": food.get("fat_g", 0),
                    "benefits": food.get("benefits", "")
                })
            rag_orchestrator.add_nutrition_data(rag_foods)
            logger.info(f"✅ Ingested {len(rag_foods)} foods from database")
        else:
            logger.warning("⚠️ No foods found in database - skipping")

        # =========================================================
        # 3) Load medical guidelines
        # =========================================================
        guidelines = load_medical_guidelines_from_db()
        documents = [g["content"] for g in guidelines]
        metadatas = [{"title": g["title"], "source": g["source"], "category": g["category"]}
                    for g in guidelines]
        ids = [f"medical_{i}" for i in range(len(guidelines))]

        rag_orchestrator.vector_store.add_documents("medical", documents, metadatas, ids)
        logger.info(f"✅ Ingested {len(guidelines)} medical guidelines")

        # =========================================================
        # 4) Load asthma exercise guide (optional text file)
        # =========================================================
        asthma_docs, asthma_metas, asthma_ids = load_asthma_exercise_guide()
        if asthma_docs:
            rag_orchestrator.vector_store.add_documents("medical", asthma_docs, asthma_metas, asthma_ids)
            logger.info(f"✅ Ingested {len(asthma_docs)} chunks from Asthma Exercise Guide")
        else:
            logger.info("ℹ️ Asthma guide not found - skipping")

        # =========================================================
        # 5) Load comprehensive exercise medical guide (Exercise_1.txt)
        # =========================================================
        med_docs, med_metas, med_ids = load_exercise_medical_guide()
        if med_docs:
            rag_orchestrator.vector_store.add_documents("medical", med_docs, med_metas, med_ids)
            logger.info(f"✅ Ingested {len(med_docs)} chunks from Exercise Medical Guide")
        else:
            logger.info("ℹ️ Exercise medical guide not found - skipping")

        # =========================================================
        # 6) Load posture correction guide (Posture_Correction.txt)
        # =========================================================
        posture_docs, posture_metas, posture_ids = load_posture_correction_guide()
        if posture_docs:
            rag_orchestrator.vector_store.add_documents("medical", posture_docs, posture_metas, posture_ids)
            logger.info(f"✅ Ingested {len(posture_docs)} chunks from Posture Correction Guide")
        else:
            logger.info("ℹ️ Posture correction guide not found - skipping")

        logger.info("🎉 Data ingestion completed successfully!")

    except Exception as e:
        logger.error(f"❌ Data ingestion failed: {e}")
        raise


if __name__ == "__main__":
    ingest_data()