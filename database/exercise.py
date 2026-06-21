# database/exercise.py

from database.db import get_db


def get_all_exercises():
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM exercise_library
            ORDER BY name ASC
        """)

        return [dict(row) for row in cursor.fetchall()]


def get_exercises(user_profile=None, risk_label="Safe"):
    """
    Smart filtered exercise recommendations
    """

    with get_db() as conn:
        cursor = conn.cursor()

        query = """
            SELECT *
            FROM exercise_library
            WHERE 1=1
        """

        params = []

        # Risk filtering
        if risk_label == "Unsafe":
            query += " AND intensity != ?"
            params.append("High")

        # Health filtering
        if user_profile:
            health = user_profile.get("health_condition", "").lower()

            if health == "asthma":
                query += " AND intensity != ?"
                params.append("High")

            elif health == "heart condition":
                query += " AND intensity = ?"
                params.append("Low")

        query += " ORDER BY name ASC LIMIT 8"

        cursor.execute(query, params)

        rows = cursor.fetchall()

        if rows:
            return [dict(r) for r in rows]

        return []


def get_exercise_by_id(exercise_id):
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM exercise_library
            WHERE id = ?
        """, (exercise_id,))

        row = cursor.fetchone()

        return dict(row) if row else None


def get_exercise_details(name):
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM exercise_library
            WHERE name = ?
        """, (name,))

        row = cursor.fetchone()

        return dict(row) if row else {}
    

# for RAG

def get_all_exercises():
    """Get all exercises from library (for RAG ingestion)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT *
            FROM exercise_library
            ORDER BY name ASC
        """)
        return [dict(row) for row in cursor.fetchall()]