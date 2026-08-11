# database/db.py

import hashlib
import os
from contextlib import contextmanager
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

import time
import psycopg2
from psycopg2.extras import RealDictCursor

DB_HOST = os.getenv("PG_HOST", "localhost")
DB_PORT = os.getenv("PG_PORT", "5432")
DB_NAME = os.getenv("PG_DB", "fitpulse")
DB_USER = os.getenv("PG_USER", "admin")
DB_PASS = os.getenv("PG_PASS", "hossein100")

@contextmanager
def get_db(retries=3, delay=1):
    last_exception = None
    for attempt in range(retries):
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASS,
                cursor_factory=RealDictCursor,
                connect_timeout=5,
                keepalives_idle=5,
                keepalives_interval=1,
                keepalives_count=2,
            )
            conn.autocommit = False
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
            return
        except psycopg2.OperationalError as e:
            last_exception = e
            print(f"Database connection attempt {attempt+1}/{retries} failed: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
                continue
            raise
    # pyrefly: ignore [bad-raise]
    raise last_exception


def table_exists(table_name):
    """Check if a table exists in the database."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = %s)",
                    (table_name,)
                )
                return cur.fetchone()[0]
    except Exception:
        return False

def get_table_columns(conn, table_name):
    """Get column names for a table."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position
        """, (table_name,))
        return [row['column_name'] for row in cur.fetchall()]

# ─── Init database ──────────────────────────────────────────────────
def init_db():
    with get_db() as conn:
        with conn.cursor() as cur:

            # ─── Cities ──────────────────────────────────────────
            cur.execute("""
                CREATE TABLE IF NOT EXISTS cities (
                    id SERIAL PRIMARY KEY,
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

            # ─── Users ───────────────────────────────────────────
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE,
                    email TEXT UNIQUE,
                    password TEXT,
                    age INTEGER NOT NULL,
                    health_condition TEXT NOT NULL,
                    fitness_level TEXT NOT NULL,
                    city_id INTEGER REFERENCES cities(id) ON DELETE SET NULL,
                    is_admin BOOLEAN DEFAULT FALSE,
                    last_login TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    bio TEXT
                )
            """)

            # ─── Migrations (add missing columns if any) ──────
            existing_cols = get_table_columns(conn, 'users')
            migrations = {
                "username": "ALTER TABLE users ADD COLUMN username TEXT UNIQUE",
                "email": "ALTER TABLE users ADD COLUMN email TEXT UNIQUE",
                "password": "ALTER TABLE users ADD COLUMN password TEXT",
                "city_id": "ALTER TABLE users ADD COLUMN city_id INTEGER REFERENCES cities(id)",
                "is_admin": "ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE",
                "last_login": "ALTER TABLE users ADD COLUMN last_login TIMESTAMP",
                "updated_at": "ALTER TABLE users ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "bio": "ALTER TABLE users ADD COLUMN bio TEXT"
            }
            for col, query in migrations.items():
                if col not in existing_cols:
                    try:
                        cur.execute(query)
                        print(f"✅ Added column: {col}")
                    except Exception as e:
                        print(f"Migration failed for {col}: {e}")

            # ─── Experience Records ─────────────────────────────
            cur.execute("""
                CREATE TABLE IF NOT EXISTS experience_records (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    experience_value TEXT NOT NULL,
                    emoji TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # ─── Analysis History ───────────────────────────────
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analysis_history (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    result TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # ─── Exercise Library ───────────────────────────────
            cur.execute("""
                CREATE TABLE IF NOT EXISTS exercise_library (
                    id SERIAL PRIMARY KEY,
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

            # ─── Food Library ───────────────────────────────────
            cur.execute("""
                CREATE TABLE IF NOT EXISTS food_library (
                    id SERIAL PRIMARY KEY,
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

            # ─── Analysis Logs ──────────────────────────────────
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analysis_logs (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    ed_score REAL,
                    risk_label TEXT,
                    activity_type TEXT,
                    duration INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # ─── User Records ───────────────────────────────────
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_records (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    description TEXT,
                    record_type TEXT NOT NULL,
                    due_date TEXT,
                    is_done BOOLEAN DEFAULT FALSE,
                    intensity TEXT DEFAULT 'Medium',
                    exercise_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # ─── Chat Messages ───────────────────────────────────
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_messages_user_created
                ON chat_messages (user_id, created_at)
            """)

            # ─── Default cities ─────────────────────────────────
            cur.execute("SELECT COUNT(*) FROM cities")
            if cur.fetchone()['count'] == 0:
                default_cities = [
                    ("Tehran", "Iran", 28, 35, 12, 8, 85, 120, 180, 55, 45, 12, 142),
                    ("Mashhad", "Iran", 24, 40, 10, 7, 65, 95, 150, 45, 35, 10, 110),
                    ("Isfahan", "Iran", 26, 30, 8, 9, 70, 105, 160, 50, 40, 11, 125),
                    ("Shiraz", "Iran", 27, 32, 9, 8, 55, 85, 140, 42, 30, 9, 95),
                    ("Tabriz", "Iran", 22, 45, 14, 6, 60, 90, 145, 40, 32, 8, 105),
                ]
                for city in default_cities:
                    cur.execute("""
                        INSERT INTO cities (
                            name, country, temp, humidity, wind, uv,
                            pm25, pm10, co, o3, no2, so2, aqi
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, city)
                print(f"✅ Added {len(default_cities)} default cities")

            # ─── Default admin ──────────────────────────────────
            cur.execute("SELECT COUNT(*) FROM users")
            if cur.fetchone()['count'] == 0:
                admin_password = hashlib.sha256("admin123".encode()).hexdigest()
                cur.execute("""
                    INSERT INTO users (
                        username, email, password, age, health_condition,
                        fitness_level, is_admin, bio
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, ("admin", "admin@example.com", admin_password, 30, "Healthy", "Medium", True, ""))
                print("✅ Default admin created")

            conn.commit()
            print("✅ PostgreSQL Database initialized")

# ─── All existing CRUD functions ──────────────────────────────────

# ─── EXPERIENCE RECORDS ───────────────────────────────────────────

def save_experience_record(user_id, experience_value, emoji):
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO experience_records (user_id, experience_value, emoji, created_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    RETURNING id
                """, (user_id, experience_value, emoji))
                row = cur.fetchone()
                return row['id']
    except Exception as e:
        print(f"Error saving experience: {e}")
        return None

def get_latest_experience(user_id):
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT experience_value, emoji, created_at
                    FROM experience_records
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (user_id,))
                row = cur.fetchone()
                return dict(row) if row else None
    except Exception as e:
        print(f"Error getting latest experience: {e}")
        return None

def get_all_experience_records(user_id, limit=50):
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, user_id, experience_value, emoji, created_at
                    FROM experience_records
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (user_id, limit))
                return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        print(f"Error getting all experience records: {e}")
        return []

def get_experience_history(user_id, limit=20):
    return get_all_experience_records(user_id, limit)

# ─── USERS ──────────────────────────────────────────────────────────

def save_user(age, health_condition, fitness_level, city_id=None, username=None, email=None, bio=None):
    with get_db() as conn:
        with conn.cursor() as cur:
            # Check existing non-admin user
            cur.execute("SELECT id FROM users WHERE is_admin = FALSE LIMIT 1")
            user = cur.fetchone()
            if user:
                cur.execute("""
                    UPDATE users
                    SET age = %s, health_condition = %s, fitness_level = %s,
                        city_id = %s, username = %s, email = %s, bio = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING id
                """, (age, health_condition, fitness_level, city_id, username, email, bio, user['id']))
                row = cur.fetchone()
                return row['id']
            else:
                cur.execute("""
                    INSERT INTO users (
                        age, health_condition, fitness_level,
                        city_id, username, email, bio, is_admin
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, FALSE)
                    RETURNING id
                """, (age, health_condition, fitness_level, city_id, username, email, bio))
                row = cur.fetchone()
                return row['id']

def get_user():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.*, c.name AS city_name, c.country
                FROM users u
                LEFT JOIN cities c ON u.city_id = c.id
                WHERE u.is_admin = FALSE
                ORDER BY u.last_login DESC, u.id DESC
                LIMIT 1
            """)
            row = cur.fetchone()
            if row:
                return dict(row)
            # fallback to any user
            cur.execute("""
                SELECT u.*, c.name AS city_name, c.country
                FROM users u
                LEFT JOIN cities c ON u.city_id = c.id
                LIMIT 1
            """)
            row = cur.fetchone()
            return dict(row) if row else None

def get_user_by_id(user_id):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, username, email, age, health_condition,
                       fitness_level, is_admin, created_at, last_login, bio
                FROM users
                WHERE id = %s
            """, (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None

def get_user_by_username(username):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.*, c.name AS city_name, c.country
                FROM users u
                LEFT JOIN cities c ON u.city_id = c.id
                WHERE u.username = %s OR u.email = %s
            """, (username, username))
            row = cur.fetchone()
            return dict(row) if row else None

def update_user_login(user_id):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s
            """, (user_id,))

def get_user_city():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.*
                FROM users u
                LEFT JOIN cities c ON u.city_id = c.id
                WHERE u.is_admin = FALSE
                LIMIT 1
            """)
            row = cur.fetchone()
            return dict(row) if row else None

# ─── ANALYSIS ──────────────────────────────────────────────────────

def save_analysis(user_id, result):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO analysis_history (user_id, result)
                VALUES (%s, %s)
                RETURNING id
            """, (user_id, result))
            row = cur.fetchone()
            return row['id']

def get_analysis_history(user_id, limit=20):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM analysis_history
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (user_id, limit))
            return [dict(row) for row in cur.fetchall()]

# ─── USER RECORDS ──────────────────────────────────────────────────

def save_record(user_id, title, description, record_type, due_date, intensity="Medium", exercise_name=""):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_records (
                    user_id, title, description, record_type, due_date,
                    intensity, exercise_name, is_done
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, FALSE)
                RETURNING id
            """, (user_id, title, description, record_type, due_date, intensity, exercise_name))
            row = cur.fetchone()
            return row['id']

def get_user_records(user_id):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM user_records WHERE user_id = %s
                ORDER BY created_at DESC
            """, (user_id,))
            return [dict(row) for row in cur.fetchall()]

def update_record(record_id, title=None, description=None, record_type=None, due_date=None,
                  is_done=None, intensity=None, exercise_name=None):
    with get_db() as conn:
        with conn.cursor() as cur:
            updates = []
            params = []
            if title is not None:
                updates.append("title = %s")
                params.append(title)
            if description is not None:
                updates.append("description = %s")
                params.append(description)
            if record_type is not None:
                updates.append("record_type = %s")
                params.append(record_type)
            if due_date is not None:
                updates.append("due_date = %s")
                params.append(due_date)
            if is_done is not None:
                updates.append("is_done = %s")
                params.append(is_done)
            if intensity is not None:
                updates.append("intensity = %s")
                params.append(intensity)
            if exercise_name is not None:
                updates.append("exercise_name = %s")
                params.append(exercise_name)
            if updates:
                updates.append("updated_at = CURRENT_TIMESTAMP")
                query = f"UPDATE user_records SET {', '.join(updates)} WHERE id = %s"
                params.append(record_id)
                cur.execute(query, params)
                return cur.rowcount > 0
            return False

def delete_record(record_id):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM user_records WHERE id = %s", (record_id,))
            return cur.rowcount > 0

# ─── CHAT MESSAGES ──────────────────────────────────────────────────

def save_chat_message(user_id, role, content):
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO chat_messages (user_id, role, content)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (user_id, role, content))
                row = cur.fetchone()
                return row['id']
    except Exception as e:
        print(f"Error saving chat message: {e}")
        return None

def get_recent_chat_messages(user_id, limit=20):
    """Returns the most recent messages in chronological order (oldest first)."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT role, content, created_at FROM chat_messages
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (user_id, limit))
                rows = [dict(row) for row in cur.fetchall()]
                return list(reversed(rows))
    except Exception as e:
        print(f"Error getting chat messages: {e}")
        return []

def clear_chat_messages(user_id):
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM chat_messages WHERE user_id = %s", (user_id,))
                return cur.rowcount
    except Exception as e:
        print(f"Error clearing chat messages: {e}")
        return 0

# ─── PROFILE ──────────────────────────────────────────────────────

def load_profile():
    try:
        user = get_user()
        if user:
            return {
                "Age": user.get("age", 25),
                "HealthCondition": user.get("health_condition", "Healthy"),
                "FitnessLevel": user.get("fitness_level", "Medium"),
                "bio": user.get("bio", "")
            }
        return None
    except Exception as e:
        print(f"Error loading profile: {e}")
        return None