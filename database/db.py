# database/db.py

import hashlib
import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "ed_database.db")


# =============================================================================
# DATABASE CONNECTION
# =============================================================================

@contextmanager
def get_db():

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        yield conn
        conn.commit()

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        conn.close()


def get_table_columns(conn, table_name):

    cursor = conn.cursor()

    cursor.execute(f"PRAGMA table_info({table_name})")

    return [col[1] for col in cursor.fetchall()]


# =============================================================================
# INIT DATABASE
# =============================================================================

def init_db():

    with get_db() as conn:

        cursor = conn.cursor()

        # =========================================================================
        # CITIES
        # =========================================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                name TEXT NOT NULL,
                country TEXT,

                temp REAL,
                humidity REAL,
                wind REAL,
                uv REAL,

                pm25 REAL,
                pm10 REAL,
                co REAL,
                o3 REAL,
                no2 REAL,
                so2 REAL,

                aqi INTEGER,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # =========================================================================
        # USERS (MUST BE CREATED BEFORE experience_records)
        # =========================================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                username TEXT UNIQUE,
                email TEXT UNIQUE,

                password TEXT,

                age INTEGER NOT NULL,
                health_condition TEXT NOT NULL,
                fitness_level TEXT NOT NULL,

                city_id INTEGER,

                is_admin BOOLEAN DEFAULT 0,
                last_login TIMESTAMP,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (city_id) REFERENCES cities(id)
            )
        """)

        # =========================================================================
        # USERS MIGRATIONS
        # =========================================================================

        columns = get_table_columns(conn, "users")

        migrations = {
            "username": "ALTER TABLE users ADD COLUMN username TEXT UNIQUE",
            "email": "ALTER TABLE users ADD COLUMN email TEXT UNIQUE",
            "password": "ALTER TABLE users ADD COLUMN password TEXT",
            "city_id": "ALTER TABLE users ADD COLUMN city_id INTEGER REFERENCES cities(id)",
            "is_admin": "ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0",
            "last_login": "ALTER TABLE users ADD COLUMN last_login TIMESTAMP",
            "updated_at": "ALTER TABLE users ADD COLUMN updated_at TIMESTAMP"
        }

        for col, query in migrations.items():

            if col not in columns:

                try:
                    cursor.execute(query)
                    print(f"✅ Added column: {col}")

                except Exception as e:
                    print(f"Migration failed for {col}: {e}")

        # =========================================================================
        # EXPERIENCE RECORDS (AFTER users table)
        # =========================================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experience_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                experience_value TEXT NOT NULL,  -- 'good', 'neutral', 'bad'
                emoji TEXT NOT NULL,             -- '😊', '😐', '☹️'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # =========================================================================
        # ANALYSIS HISTORY
        # =========================================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER NOT NULL,

                result TEXT NOT NULL,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # =========================================================================
        # EXERCISE LIBRARY
        # =========================================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exercise_library (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                name TEXT UNIQUE,
                type TEXT,
                intensity TEXT,

                duration_minutes INTEGER,
                calories_per_hour INTEGER,

                benefits TEXT,
                precautions TEXT,
                contraindications TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # =========================================================================
        # FOOD LIBRARY
        # =========================================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS food_library (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                name TEXT UNIQUE,
                category TEXT,

                calories_per_100g REAL,
                protein_g REAL,
                carbs_g REAL,
                fat_g REAL,
                fiber_g REAL,

                glycemic_index INTEGER,

                benefits TEXT,
                allergens TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # =========================================================================
        # ANALYSIS LOGS
        # =========================================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER,

                ed_score REAL,
                risk_label TEXT,

                activity_type TEXT,
                duration INTEGER,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # =========================================================================
        # USER RECORDS
        # =========================================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER NOT NULL,

                title TEXT NOT NULL,
                description TEXT,
                record_type TEXT NOT NULL,  -- 'workout' or 'diet'
                due_date TEXT,
                is_done BOOLEAN DEFAULT 0,
                intensity TEXT DEFAULT 'Medium',
                exercise_name TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # =========================================================================
        # DEFAULT CITIES
        # =========================================================================

        cursor.execute("SELECT COUNT(*) FROM cities")

        count = cursor.fetchone()[0]

        if count == 0:

            default_cities = [
                ("Tehran", "Iran", 28, 35, 12, 8, 85, 120, 180, 55, 45, 12, 142),
                ("Mashhad", "Iran", 24, 40, 10, 7, 65, 95, 150, 45, 35, 10, 110),
                ("Isfahan", "Iran", 26, 30, 8, 9, 70, 105, 160, 50, 40, 11, 125),
                ("Shiraz", "Iran", 27, 32, 9, 8, 55, 85, 140, 42, 30, 9, 95),
                ("Tabriz", "Iran", 22, 45, 14, 6, 60, 90, 145, 40, 32, 8, 105),
            ]

            for city in default_cities:

                cursor.execute("""
                    INSERT INTO cities (
                        name,
                        country,
                        temp,
                        humidity,
                        wind,
                        uv,
                        pm25,
                        pm10,
                        co,
                        o3,
                        no2,
                        so2,
                        aqi
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, city)

            print("✅ Default cities inserted")

        # =========================================================================
        # DEFAULT ADMIN
        # =========================================================================

        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]

        if user_count == 0:

            admin_password = hashlib.sha256(
                "admin123".encode()
            ).hexdigest()

            cursor.execute("""
                INSERT INTO users (
                    username,
                    email,
                    password,
                    age,
                    health_condition,
                    fitness_level,
                    is_admin
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                "admin",
                "admin@example.com",
                admin_password,
                30,
                "Healthy",
                "Medium",
                1
            ))

            print("✅ Default admin created")

        print("✅ Database initialized")


# =============================================================================
# EXPERIENCE RECORDS
# =============================================================================

def save_experience_record(user_id, experience_value, emoji):
    """Save user experience (😊, 😐, ☹️) to database"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO experience_records (user_id, experience_value, emoji, created_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, experience_value, emoji))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error saving experience: {e}")
        return False


def get_latest_experience(user_id):
    """Get the most recent experience record for a user"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT experience_value, emoji, created_at
                FROM experience_records
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (user_id,))
            row = cursor.fetchone()
            if row:
                return {"experience": row[0], "emoji": row[1], "created_at": row[2]}
            return None
    except Exception as e:
        print(f"Error getting latest experience: {e}")
        return None


def get_experience_history(user_id, limit=20):
    """Get experience history for a user"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT experience_value, emoji, created_at
                FROM experience_records
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error getting experience history: {e}")
        return []


# =============================================================================
# USERS
# =============================================================================

def save_user(
    age,
    health_condition,
    fitness_level,
    city_id=None,
    username=None,
    email=None
):

    with get_db() as conn:

        cursor = conn.cursor()

        # Check if a non-admin user already exists
        cursor.execute("""
            SELECT id
            FROM users
            WHERE is_admin = 0
            LIMIT 1
        """)

        user = cursor.fetchone()

        if user:
            # Update existing non-admin user
            cursor.execute("""
                UPDATE users
                SET
                    age = ?,
                    health_condition = ?,
                    fitness_level = ?,
                    city_id = ?,
                    username = ?,
                    email = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                age,
                health_condition,
                fitness_level,
                city_id,
                username,
                email,
                user["id"]
            ))

            return user["id"]

        else:
            # Create new non-admin user
            cursor.execute("""
                INSERT INTO users (
                    age,
                    health_condition,
                    fitness_level,
                    city_id,
                    username,
                    email,
                    is_admin
                )
                VALUES (?, ?, ?, ?, ?, ?, 0)
            """, (
                age,
                health_condition,
                fitness_level,
                city_id,
                username,
                email
            ))

            return cursor.lastrowid


def get_user():
    """Get the current non-admin user (most recent or last logged in)"""

    with get_db() as conn:

        cursor = conn.cursor()

        # Try to get non-admin user first
        cursor.execute("""
            SELECT
                u.*,
                c.name AS city_name,
                c.country
            FROM users u
            LEFT JOIN cities c ON u.city_id = c.id
            WHERE u.is_admin = 0
            ORDER BY u.last_login DESC, u.id DESC
            LIMIT 1
        """)

        row = cursor.fetchone()

        if row:
            return dict(row)

        # Fallback: get any user (admin) if no non-admin exists
        cursor.execute("""
            SELECT
                u.*,
                c.name AS city_name,
                c.country
            FROM users u
            LEFT JOIN cities c ON u.city_id = c.id
            LIMIT 1
        """)

        row = cursor.fetchone()

        return dict(row) if row else None


def get_user_by_username(username):
    """Get user by username (for authentication)"""

    with get_db() as conn:

        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                u.*,
                c.name AS city_name,
                c.country
            FROM users u
            LEFT JOIN cities c ON u.city_id = c.id
            WHERE u.username = ? OR u.email = ?
        """, (username, username))

        row = cursor.fetchone()

        return dict(row) if row else None


def update_user_login(user_id):
    """Update user's last login timestamp"""

    with get_db() as conn:

        cursor = conn.cursor()

        cursor.execute("""
            UPDATE users
            SET last_login = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (user_id,))


def get_user_city():

    with get_db() as conn:

        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                c.*
            FROM users u
            LEFT JOIN cities c ON u.city_id = c.id
            WHERE u.is_admin = 0
            LIMIT 1
        """)

        row = cursor.fetchone()

        return dict(row) if row else None


# =============================================================================
# ANALYSIS
# =============================================================================

def save_analysis(user_id, result):

    with get_db() as conn:

        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO analysis_history (
                user_id,
                result
            )
            VALUES (?, ?)
        """, (user_id, result))

        return cursor.lastrowid


def get_analysis_history(user_id, limit=20):

    with get_db() as conn:

        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM analysis_history
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))

        return [dict(row) for row in cursor.fetchall()]


# =============================================================================
# USER RECORDS
# =============================================================================

def save_record(user_id, title, description, record_type, due_date, intensity="Medium", exercise_name=""):
    """Save a new record for a user"""

    with get_db() as conn:
        
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_records (
                user_id, title, description, record_type, due_date, 
                intensity, exercise_name, is_done
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, title, description, record_type, due_date, intensity, exercise_name, False))
        return cursor.lastrowid


def get_user_records(user_id):
    """Get all records for a user"""

    with get_db() as conn:

        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM user_records
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))

        return [dict(row) for row in cursor.fetchall()]


def update_record(record_id, title=None, description=None, record_type=None, due_date=None,
                  is_done=None, intensity=None, exercise_name=None):
    """Update an existing record"""

    with get_db() as conn:

        cursor = conn.cursor()

        # Build update query dynamically
        updates = []
        params = []

        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if record_type is not None:
            updates.append("record_type = ?")
            params.append(record_type)
        if due_date is not None:
            updates.append("due_date = ?")
            params.append(due_date)
        if is_done is not None:
            updates.append("is_done = ?")
            params.append(is_done)
        if intensity is not None:
            updates.append("intensity = ?")
            params.append(intensity)
        if exercise_name is not None:
            updates.append("exercise_name = ?")
            params.append(exercise_name)

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            query = f"UPDATE user_records SET {', '.join(updates)} WHERE id = ?"
            params.append(record_id)
            cursor.execute(query, params)

        return cursor.rowcount > 0


def delete_record(record_id):
    """Delete a record"""

    with get_db() as conn:

        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM user_records
            WHERE id = ?
        """, (record_id,))

        return cursor.rowcount > 0


# =============================================================================
# PROFILE
# =============================================================================

def load_profile():
    """Load user profile (compatibility function)"""
    try:
        user = get_user()
        if user:
            return {
                "Age": user.get("age", 25),
                "HealthCondition": user.get("health_condition", "Healthy"),
                "FitnessLevel": user.get("fitness_level", "Medium")
            }
        return None
    except Exception as e:
        print(f"Error loading profile: {e}")
        return None