# database/food.py

from database.db import get_db


def get_foods(user_profile=None):
    """
    Smart nutrition recommendations
    """
    with get_db() as conn:
        with conn.cursor() as cur:
            query = """
                SELECT * FROM food_library
                WHERE 1=1
            """
            params = []

            if user_profile:
                health = user_profile.get("health_condition", "").lower()
                if health == "diabetes":
                    query += """
                        AND (glycemic_index IS NULL OR glycemic_index <= 55)
                    """

            query += " ORDER BY name ASC LIMIT 8"

            cur.execute(query, params)
            rows = cur.fetchall()
            if rows:
                return [dict(row) for row in rows]
            return []


def get_food_by_id(food_id):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM food_library
                WHERE id = %s
            """, (food_id,))
            row = cur.fetchone()
            return dict(row) if row else None


def get_food_details(name):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM food_library
                WHERE name = %s
            """, (name,))
            row = cur.fetchone()
            return dict(row) if row else {}


def add_food(name, category, calories_per_100g, protein_g, carbs_g, fat_g, fiber_g, glycemic_index, benefits, allergens):
    """Add a new food to the library"""
    with get_db() as conn:
        with conn.cursor() as cur:
            # Check if food already exists
            cur.execute("SELECT id FROM food_library WHERE name = %s", (name,))
            if cur.fetchone():
                print(f"⚠️ Food '{name}' already exists")
                return None

            cur.execute("""
                INSERT INTO food_library (
                    name, category, calories_per_100g, protein_g, carbs_g,
                    fat_g, fiber_g, glycemic_index, benefits, allergens
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (name, category, calories_per_100g, protein_g, carbs_g,
                  fat_g, fiber_g, glycemic_index, benefits, allergens))
            row = cur.fetchone()
            conn.commit()
            print(f"Added food: {name}")
            return row['id']


def get_all_foods():
    """Get all foods from library (for RAG ingestion)"""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM food_library
                ORDER BY name ASC
            """)
            return [dict(row) for row in cur.fetchall()]