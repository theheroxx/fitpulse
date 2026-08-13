"""
Ingest from correct database tables (exercise_library, food_library)
Run: python ingest_db.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rag.rag_system import rag_orchestrator
from database.db import get_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def safe_get(item, key, default=""):
    """Safely get value from dict or object"""
    if isinstance(item, dict):
        return item.get(key, default)
    else:
        return getattr(item, key, default)

def inspect_table(table_name):
    """Show columns of a table"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        
        print(f"\n  Columns in '{table_name}':")
        for col in columns:
            if isinstance(col, dict):
                print(f"    - {col.get('column_name')}: {col.get('data_type')}")
            else:
                print(f"    - {col[0]}: {col[1]}")

def ingest_exercises():
    """Load exercises from exercise_library table"""
    print("\n[1] Loading exercises from exercise_library...")
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # First, check columns
            inspect_table("exercise_library")
            
            # Query all exercises
            cursor.execute("SELECT * FROM exercise_library")
            exercises = cursor.fetchall()
            
            print(f"  Found {len(exercises)} exercises")
            
            if not exercises:
                return 0
            
            # Convert to RAG format
            rag_exercises = []
            for ex in exercises:
                rag_exercises.append({
                    "name": safe_get(ex, "name", safe_get(ex, "exercise_name", "Unknown")),
                    "type": safe_get(ex, "type", safe_get(ex, "exercise_type", "general")),
                    "intensity": safe_get(ex, "intensity", safe_get(ex, "difficulty", "moderate")),
                    "duration": f"{safe_get(ex, 'duration_minutes', safe_get(ex, 'duration', 30))} minutes",
                    "benefits": safe_get(ex, "benefits", ""),
                    "precautions": safe_get(ex, "precautions", safe_get(ex, "caution", "")),
                })
            
            # Show first item to verify
            if rag_exercises:
                print(f"  Sample: {rag_exercises[0]}")
            
            rag_orchestrator.add_exercise_data(rag_exercises)
            print(f"  ✅ Added {len(rag_exercises)} exercises")
            return len(rag_exercises)
            
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return 0

def ingest_foods():
    """Load foods from food_library table"""
    print("\n[2] Loading foods from food_library...")
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Check columns
            inspect_table("food_library")
            
            # Query all foods
            cursor.execute("SELECT * FROM food_library")
            foods = cursor.fetchall()
            
            print(f"  Found {len(foods)} foods")
            
            if not foods:
                return 0
            
            # Convert to RAG format
            rag_foods = []
            for food in foods:
                rag_foods.append({
                    "name": safe_get(food, "name", safe_get(food, "food_name", "Unknown")),
                    "category": safe_get(food, "category", safe_get(food, "food_category", "general")),
                    "calories": safe_get(food, "calories", safe_get(food, "calories_per_100g", 0)),
                    "protein": safe_get(food, "protein", safe_get(food, "protein_g", 0)),
                    "carbs": safe_get(food, "carbs", safe_get(food, "carbs_g", 0)),
                    "fat": safe_get(food, "fat", safe_get(food, "fat_g", 0)),
                    "benefits": safe_get(food, "benefits", ""),
                })
            
            # Show first item
            if rag_foods:
                print(f"  Sample: {rag_foods[0]}")
            
            rag_orchestrator.add_nutrition_data(rag_foods)
            print(f"  ✅ Added {len(rag_foods)} foods")
            return len(rag_foods)
            
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return 0

if __name__ == "__main__":
    print("=" * 80)
    print("INGESTING FROM DATABASE (exercise_library, food_library)")
    print("=" * 80)
    
    # Ingest exercises
    exercise_count = ingest_exercises()
    
    # Ingest foods
    food_count = ingest_foods()
    
    # Verify
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    
    vs = rag_orchestrator.vector_store
    for name, collection in vs.collections.items():
        count = collection.count()
        print(f"  {name}: {count} documents")
    
    print(f"\n✅ Database ingestion complete!")
    print(f"   Exercises added: {exercise_count}")
    print(f"   Foods added: {food_count}")