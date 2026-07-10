# database/auth.py

import hashlib
from database.db import get_db

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def create_user(username, email, password, age=25, health_condition="Healthy", fitness_level="Medium"):
    with get_db() as conn:
        with conn.cursor() as cur:
            # Check username
            cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                return None, "Username already exists"
            # Check email
            if email:
                cur.execute("SELECT id FROM users WHERE email = %s", (email,))
                if cur.fetchone():
                    return None, "Email already exists"

            hashed_password = hash_password(password)
            cur.execute("""
                INSERT INTO users (
                    username, email, password, age,
                    health_condition, fitness_level, is_admin
                ) VALUES (%s, %s, %s, %s, %s, %s, FALSE)
                RETURNING id
            """, (username, email, hashed_password, age, health_condition, fitness_level))
            row = cur.fetchone()
            conn.commit()
            return row['id'], "User created successfully"

def authenticate_user(username, password):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, username, email, password, age,
                       health_condition, fitness_level, is_admin
                FROM users
                WHERE username = %s OR email = %s
            """, (username, username))
            user = cur.fetchone()
            if not user:
                return None, "User not found"
            user_dict = dict(user)
            if not verify_password(password, user_dict["password"]):
                return None, "Invalid password"
            # update last login
            try:
                cur.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s", (user_dict["id"],))
                conn.commit()
            except Exception:
                pass
            del user_dict["password"]
            return user_dict, "Login successful"

def get_user_by_id(user_id):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, username, email, age, health_condition,
                       fitness_level, is_admin, created_at, last_login
                FROM users
                WHERE id = %s
            """, (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None

def update_user(user_id, **kwargs):
    with get_db() as conn:
        with conn.cursor() as cur:
            allowed = ["age", "health_condition", "fitness_level", "city_id", "email"]
            for key, value in kwargs.items():
                if key in allowed:
                    try:
                        cur.execute(f"UPDATE users SET {key} = %s WHERE id = %s", (value, user_id))
                    except Exception as e:
                        print(f"Update error ({key}): {e}")
            conn.commit()
            return True

def get_all_users():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, username, email, age, health_condition,
                       fitness_level, is_admin, created_at, last_login
                FROM users
                WHERE is_admin = FALSE
                ORDER BY created_at DESC
            """)
            return [dict(row) for row in cur.fetchall()]

def delete_user(user_id):
    with get_db() as conn:
        with conn.cursor() as cur:
            # Delete related records (optional, if you have ON DELETE CASCADE you can skip)
            try:
                cur.execute("DELETE FROM analysis_history WHERE user_id = %s", (user_id,))
            except Exception:
                pass
            try:
                cur.execute("DELETE FROM analysis_logs WHERE user_id = %s", (user_id,))
            except Exception:
                pass
            cur.execute("DELETE FROM users WHERE id = %s AND is_admin = FALSE", (user_id,))
            conn.commit()
            return True