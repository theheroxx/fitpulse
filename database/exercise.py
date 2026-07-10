# database/exercise.py

from database.db import get_db


def get_all_exercises():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM exercise_library
                ORDER BY name ASC
            """)
            return [dict(row) for row in cur.fetchall()]


def get_exercises(user_profile=None, risk_label="Safe"):
    """
    Smart filtered exercise recommendations
    """
    with get_db() as conn:
        with conn.cursor() as cur:
            query = """
                SELECT * FROM exercise_library
                WHERE 1=1
            """
            params = []

            # Risk filtering
            if risk_label == "Unsafe":
                query += " AND intensity != %s"
                params.append("High")

            # Health filtering
            if user_profile:
                health = user_profile.get("health_condition", "").lower()
                if health == "asthma":
                    query += " AND intensity != %s"
                    params.append("High")
                elif health == "heart condition":
                    query += " AND intensity = %s"
                    params.append("Low")

            query += " ORDER BY name ASC LIMIT 8"

            cur.execute(query, params)
            rows = cur.fetchall()
            if rows:
                return [dict(row) for row in rows]
            return []


def get_exercise_by_id(exercise_id):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM exercise_library
                WHERE id = %s
            """, (exercise_id,))
            row = cur.fetchone()
            return dict(row) if row else None


def get_exercise_details(name):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM exercise_library
                WHERE name = %s
            """, (name,))
            row = cur.fetchone()
            return dict(row) if row else {}