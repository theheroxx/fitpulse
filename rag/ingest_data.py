
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag.rag_system import rag_orchestrator
from database.db import get_db
from database.exercise import get_all_exercises
from database.food import get_all_foods
import logging
import re
import json
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

DOCS_DIR = "D:/ED/data/documents/"
CHROMA_DIR = "D:/ED/data/chroma_db/"
MANIFEST_PATH = os.path.join(CHROMA_DIR, "ingestion_manifest.json")
COLLECTION_NAME = "medical"
SUPPORTED_EXTENSIONS = (".txt",)

# If a file disappears from DOCS_DIR, also delete its chunks from the vector store.
# Set False if you'd rather keep old chunks around even after deleting the source file.
SYNC_DELETIONS = True

DEFAULT_CATEGORY = "General"

# Topic keys are just labels for metadata/filtering — kept from your original config
# for reference and used by the auto-tagging heuristic below.
TOPICS = {
    "cardio_guides": "Overall High/mid/low cardio practice guides",
    "exercise_effects_groups": "Different types of exercise effects on different groups of people",
    "exercises_for_diseases": "Best exercises for diseases such as Asthma, Heart conditions, diabetes",
    "weather_effects": "How weather conditions affect exercising",
    "air_pollution_exercise": "What air pollutions are worse while exercising",
    "indoor_outdoor_climates": "Differences between indoor and outdoor exercises in various climates",
    "diet_guidelines": "Up-to-date guidelines for food diet",
    "diets_for_individuals": "Best diets for specific individuals",
    "food_nutrition_info": "Amount of calories, proteins, vitamins and important nutrients in foods",
    "optimal_schedule": "Sweet-spot amount of days and practice times for different individuals",
}

# Keyword heuristic used ONLY when a file has no front-matter "topics:" and isn't
# one of the manually-curated files below. Tune freely.
TOPIC_KEYWORDS = {
    "cardio_guides": ["cardio", "aerobic", "heart rate zone"],
    "exercise_effects_groups": ["elderly", "children", "pregnan", "age group", "population"],
    "exercises_for_diseases": ["asthma", "diabetes", "heart condition", "disease", "copd", "hypertension"],
    "weather_effects": ["weather", "temperature", "humidity", "heatwave", "cold exposure"],
    "air_pollution_exercise": ["pollution", "air quality", "pm2.5", "ozone", "smog"],
    "indoor_outdoor_climates": ["indoor", "outdoor", "altitude", "climate"],
    "diet_guidelines": ["diet guideline", "dietary guideline", "nutrition guideline"],
    "diets_for_individuals": ["keto", "vegan", "paleo", "mediterranean diet", "diet plan"],
    "food_nutrition_info": ["calorie", "protein", "carbohydrate", "vitamin", "nutrient"],
    "optimal_schedule": ["days per week", "frequency", "how often", "schedule"],
}

# Curated metadata for files that already existed under the old hardcoded config.
# This preserves their original tagging exactly. New files you add later don't need
# an entry here at all — front-matter or auto-detection covers them.
MANUAL_OVERRIDES = {
    "asthma_guide.txt": {
        "loader": "double_newline",
        "title": "Asthma & Exercise Guide",
        "source": "Medical Research Compilation",
        "category": "Respiratory Health",
        "topics": ["exercises_for_diseases"],
    },
    "Exercise_1.txt": {
        "loader": "numbered_sections",
        "title": "Exercise & Health Medical Guide",
        "source": "Compilation of research (see embedded citations)",
        "category": "General Exercise Science",
        "topics": [
            "air_pollution_exercise",
            "exercises_for_diseases",
            "diet_guidelines",
            "diets_for_individuals",
            "food_nutrition_info",
            "optimal_schedule",
        ],
    },
    "Posture_Correction.txt": {
        "loader": "numbered_sections",
        "title": "Posture Correction: Evidence-Based Practices",
        "source": "Posture Correction Guide",
        "category": "Musculoskeletal Health",
        "topics": ["exercise_effects_groups"],
    },
    "cardio_guides.txt": {
        "loader": "double_newline",
        "title": "Cardio Exercise Guides",
        "source": "Compilation of cardio guidelines",
        "category": "Cardiovascular Health",
        "topics": ["cardio_guides", "weather_effects", "indoor_outdoor_climates"],
    },
}


# =============================================================================
# FRONT-MATTER PARSING (optional per-file metadata override)
# =============================================================================

FRONT_MATTER_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)


def parse_front_matter(raw_text):
    """
    If the file starts with a --- ... --- block, parse it as simple key: value
    metadata and return (metadata_dict, remaining_body_text).
    If there's no front-matter, returns ({}, raw_text) unchanged.
    """
    match = FRONT_MATTER_RE.match(raw_text)
    if not match:
        return {}, raw_text

    meta = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip().lower()] = value.strip()

    body = raw_text[match.end():]
    return meta, body


# =============================================================================
# LOADER AUTO-DETECTION
# =============================================================================

NUMBERED_HEADING_RE = re.compile(r'(?:^|\n)\s*\d+\.\s+\S')


def detect_loader(text):
    """Guess whether a file is structured into numbered sections or plain
    double-newline-separated paragraphs, based on how many numbered headings
    it contains."""
    if len(NUMBERED_HEADING_RE.findall(text)) >= 2:
        return "numbered_sections"
    return "double_newline"


def guess_topics(text):
    """Crude keyword-based topic tagging, used only when a file has no
    explicit topics (front-matter or MANUAL_OVERRIDES)."""
    text_lower = text.lower()
    matched = [
        topic for topic, keywords in TOPIC_KEYWORDS.items()
        if any(kw in text_lower for kw in keywords)
    ]
    return matched or ["general"]


# =============================================================================
# LOADER FUNCTIONS (operate on already-loaded text, not file paths)
# =============================================================================

def load_text_file_double_newline(text, title, source, category, topics, basename):
    chunks = [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]
    documents, metadatas, ids = [], [], []

    for i, chunk in enumerate(chunks):
        documents.append(chunk)
        metadatas.append({
            "title": title,
            "source": source,
            "category": category,
            "topics": topics,
            "chunk_id": i,
        })
        ids.append(f"{basename}_{i}")

    return documents, metadatas, ids


def load_text_file_numbered_sections(text, title, source, category, topics, basename):
    text = text.replace('\r\n', '\n')

    # FIX: the section regex requires a newline before "N. Heading". If the file's
    # very first line IS a numbered heading (no leading blank line), that section
    # used to be silently dropped. Prepending a newline guarantees it's matched.
    if not text.startswith('\n'):
        text = '\n' + text

    section_pattern = r'\n(\d+\.\s+[^\n]+)\n(.*?)(?=\n\d+\.\s+|\Z)'
    matches = re.findall(section_pattern, text, re.DOTALL)

    documents, metadatas, ids = [], [], []

    for i, (heading, content) in enumerate(matches):
        heading = heading.strip()
        content = content.strip()
        if not content:
            continue

        sub_chunks = [sub.strip() for sub in content.split("\n\n") if sub.strip()] or [content]
        for j, sub_chunk in enumerate(sub_chunks):
            full_chunk = f"{heading}\n{sub_chunk}"
            documents.append(full_chunk)
            metadatas.append({
                "title": title,
                "source": source,
                "category": category,
                "topics": topics,
                "section_heading": heading,
                "chunk_id": j,
            })
            ids.append(f"{basename}_{i}_{j}")

    # Executive Summary capture (unchanged from original, kept for compatibility).
    # Note: if a doc's Executive Summary also appears as a numbered section above,
    # you'll get some duplicated content in the store — worth a look if you notice
    # near-duplicate results at query time.
    if "Executive Summary" in text:
        summary_start = text.find("Executive Summary")
        if summary_start != -1:
            summary_text = text[summary_start:].strip()
            if len(summary_text) > 2000:
                summary_text = summary_text[:2000] + "..."
            documents.append(summary_text)
            metadatas.append({
                "title": title,
                "source": source,
                "category": "Summary",
                "topics": topics,
                "chunk_id": 0,
            })
            ids.append(f"{basename}_executive_summary")

    return documents, metadatas, ids


LOADER_MAP = {
    "double_newline": load_text_file_double_newline,
    "numbered_sections": load_text_file_numbered_sections,
}


# =============================================================================
# EXISTING DATABASE LOADERS (unchanged)
# =============================================================================

def load_exercises_from_db():
    try:
        exercises = get_all_exercises()
        if exercises:
            return exercises
        logger.warning("No exercises found in database")
        return []
    except Exception as e:
        logger.error(f"Failed to load exercises from database: {e}")
        return []


def load_foods_from_db():
    try:
        foods = get_all_foods()
        if foods:
            return foods
        logger.warning("No foods found in database")
        return []
    except Exception as e:
        logger.error(f"Failed to load foods from database: {e}")
        return []


def load_medical_guidelines_from_db():
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

    return get_sample_medical_guidelines()


def get_sample_medical_guidelines():
    return [
        {
            "title": "Asthma and Exercise",
            "content": """...""",
            "source": "American Lung Association",
            "category": "Respiratory Health",
        },
        # ... other samples ...
    ]


# =============================================================================
# MANIFEST (tracks what's already been ingested, so re-runs are safe)
# =============================================================================

def load_manifest():
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_manifest(manifest):
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def delete_ids(ids):
    """Remove previously-ingested chunks for a file that changed or was deleted.

    NOTE: this tries a few common method names on your vector_store since that
    class wasn't included in what you shared. If none of these match, this will
    log a warning instead of silently failing — check your rag/rag_system.py and
    either rename one of your existing methods to match, or add a thin wrapper
    around Chroma's collection.delete(ids=...).
    """
    if not ids:
        return

    vs = rag_orchestrator.vector_store
    try:
        if hasattr(vs, "delete_documents"):
            vs.delete_documents(COLLECTION_NAME, ids)
            return
        if hasattr(vs, "delete"):
            vs.delete(COLLECTION_NAME, ids)
            return
        if hasattr(vs, "collection"):
            vs.collection.delete(ids=ids)
            return
        if hasattr(vs, "get_collection"):
            vs.get_collection(COLLECTION_NAME).delete(ids=ids)
            return
    except Exception as e:
        logger.error(f"Failed to delete old chunk IDs {ids}: {e}")
        return

    logger.warning(
        "vector_store has no delete/delete_documents/collection.delete method I could "
        "find — old chunks for changed/removed files won't be cleaned up automatically. "
        "Add a delete method to your vector_store class to fix this."
    )


# =============================================================================
# FOLDER SYNC (this replaces DOCUMENT_CONFIGS)
# =============================================================================

def resolve_metadata(fname, front_matter, body_text):
    """Priority: front-matter in the file > MANUAL_OVERRIDES for known legacy
    files > auto-detected/guessed defaults."""
    override = MANUAL_OVERRIDES.get(fname, {})

    title = front_matter.get("title") or override.get("title") or \
        os.path.splitext(fname)[0].replace("_", " ").replace("-", " ").title()

    source = front_matter.get("source") or override.get("source") or f"Auto-ingested: {fname}"
    category = front_matter.get("category") or override.get("category") or DEFAULT_CATEGORY

    if "topics" in front_matter:
        topics = [t.strip() for t in front_matter["topics"].split(",") if t.strip()]
    elif "topics" in override:
        topics = override["topics"]
    else:
        topics = guess_topics(body_text)

    loader_name = front_matter.get("loader") or override.get("loader") or detect_loader(body_text)

    return title, source, category, topics, loader_name


def sync_documents_folder():
    if not os.path.isdir(DOCS_DIR):
        logger.warning(f"Documents folder not found: {DOCS_DIR} — skipping folder sync")
        return

    manifest = load_manifest()
    seen_files = set()
    new_count = updated_count = skipped_count = removed_count = failed_count = 0

    for fname in sorted(os.listdir(DOCS_DIR)):
        if not fname.lower().endswith(SUPPORTED_EXTENSIONS):
            continue

        path = os.path.join(DOCS_DIR, fname)
        seen_files.add(fname)

        try:
            current_hash = file_hash(path)
            prev = manifest.get(fname)

            if prev and prev.get("hash") == current_hash:
                logger.info(f"⏭️  {fname} unchanged — skipping")
                skipped_count += 1
                continue

            if prev:
                logger.info(f"♻️  {fname} changed — replacing old chunks")
                delete_ids(prev.get("ids", []))
                updated_count += 1
            else:
                logger.info(f"🆕 {fname} is new — ingesting")
                new_count += 1

            with open(path, "r", encoding="utf-8") as f:
                raw_text = f.read()

            front_matter, body_text = parse_front_matter(raw_text)
            title, source, category, topics, loader_name = resolve_metadata(fname, front_matter, body_text)

            loader_fn = LOADER_MAP.get(loader_name)
            if not loader_fn:
                logger.warning(f"Unknown loader '{loader_name}' for {fname} — defaulting to double_newline")
                loader_fn = load_text_file_double_newline

            basename = os.path.splitext(fname)[0]
            docs, metas, ids = loader_fn(body_text, title, source, category, topics, basename)

            if docs:
                rag_orchestrator.vector_store.add_documents(COLLECTION_NAME, docs, metas, ids)
                logger.info(f"✅ Ingested {len(docs)} chunks from {fname} (topics: {topics})")
                manifest[fname] = {"hash": current_hash, "ids": ids, "loader": loader_name}
            else:
                logger.warning(f"⚠️ {fname} produced no chunks — check its formatting")
                manifest[fname] = {"hash": current_hash, "ids": [], "loader": loader_name}

        except Exception as e:
            logger.error(f"❌ Failed to process {fname}, skipping it and continuing: {e}")
            failed_count += 1
            continue

    if SYNC_DELETIONS:
        removed_files = set(manifest.keys()) - seen_files
        for fname in removed_files:
            logger.info(f"🗑️  {fname} no longer in folder — removing its chunks")
            delete_ids(manifest[fname].get("ids", []))
            del manifest[fname]
            removed_count += 1

    save_manifest(manifest)
    logger.info(
        f"📄 Folder sync complete — new: {new_count}, updated: {updated_count}, "
        f"skipped: {skipped_count}, removed: {removed_count}, failed: {failed_count}"
    )


# =============================================================================
# MAIN INGESTION
# =============================================================================

def ingest_data():
    try:
        logger.info("Starting data ingestion from databases...")

        # 1) Exercises
        exercises = load_exercises_from_db()
        if exercises:
            rag_exercises = [{
                "name": ex.get("name", ""),
                "type": ex.get("type", ""),
                "intensity": ex.get("intensity", ""),
                "duration": f"{ex.get('duration_minutes', 30)} minutes",
                "benefits": ex.get("benefits", ""),
                "precautions": ex.get("precautions", ""),
            } for ex in exercises]
            rag_orchestrator.add_exercise_data(rag_exercises)
            logger.info(f"✅ Ingested {len(rag_exercises)} exercises from database")
        else:
            logger.warning("⚠️ No exercises found in database - skipping")

        # 2) Foods
        foods = load_foods_from_db()
        if foods:
            rag_foods = [{
                "name": food.get("name", ""),
                "category": food.get("category", ""),
                "calories": food.get("calories_per_100g", 0),
                "protein": food.get("protein_g", 0),
                "carbs": food.get("carbs_g", 0),
                "fat": food.get("fat_g", 0),
                "benefits": food.get("benefits", ""),
            } for food in foods]
            rag_orchestrator.add_nutrition_data(rag_foods)
            logger.info(f"✅ Ingested {len(rag_foods)} foods from database")
        else:
            logger.warning("⚠️ No foods found in database - skipping")

        # 3) Medical guidelines
        guidelines = load_medical_guidelines_from_db()
        documents = [g["content"] for g in guidelines]
        metadatas = [{"title": g["title"], "source": g["source"], "category": g["category"]} for g in guidelines]
        ids = [f"medical_{i}" for i in range(len(guidelines))]
        rag_orchestrator.vector_store.add_documents(COLLECTION_NAME, documents, metadatas, ids)
        logger.info(f"✅ Ingested {len(guidelines)} medical guidelines")

        # 4) Text documents folder (auto-synced — no per-file config needed)
        logger.info("📄 Syncing text documents folder...")
        sync_documents_folder()

        logger.info("🎉 Data ingestion completed successfully!")

    except Exception as e:
        logger.error(f"❌ Data ingestion failed: {e}")
        raise


if __name__ == "__main__":
    ingest_data()