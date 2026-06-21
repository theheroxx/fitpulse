# database/food.py

from database.db import get_db


def get_foods(user_profile=None):
    """
    Smart nutrition recommendations
    """

    with get_db() as conn:
        cursor = conn.cursor()

        query = """
            SELECT *
            FROM food_library
            WHERE 1=1
        """

        params = []

        if user_profile:
            health = user_profile.get("health_condition", "").lower()

            # Diabetes filtering
            if health == "diabetes":
                query += """
                    AND (
                        glycemic_index IS NULL
                        OR glycemic_index <= 55
                    )
                """

        query += " ORDER BY name ASC LIMIT 8"

        cursor.execute(query, params)

        rows = cursor.fetchall()

        if rows:
            return [dict(r) for r in rows]

        return []


def get_food_by_id(food_id):
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM food_library
            WHERE id = ?
        """, (food_id,))

        row = cursor.fetchone()

        return dict(row) if row else None


def get_food_details(name):
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM food_library
            WHERE name = ?
        """, (name,))

        row = cursor.fetchone()

        return dict(row) if row else {}
    


def add_food(name, category, calories_per_100g, protein_g, carbs_g, fat_g, fiber_g, glycemic_index, benefits, allergens):
    """Add a new food to the library"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if food already exists
        cursor.execute("SELECT id FROM food_library WHERE name = ?", (name,))
        if cursor.fetchone():
            print(f"⚠️ Food '{name}' already exists")
            return None
        
        cursor.execute("""
            INSERT INTO food_library (
                name, category, calories_per_100g, protein_g, carbs_g, 
                fat_g, fiber_g, glycemic_index, benefits, allergens
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, category, calories_per_100g, protein_g, carbs_g, 
              fat_g, fiber_g, glycemic_index, benefits, allergens))
        
        print(f"Added food: {name}")
        return cursor.lastrowid


def get_all_foods():
    """Get all foods from library (for RAG ingestion)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT *
            FROM food_library
            ORDER BY name ASC
        """)
        return [dict(row) for row in cursor.fetchall()]