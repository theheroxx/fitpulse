# database/auth.py

import hashlib
from database.db import get_db


# =========================================================
# Password Hashing
# =========================================================
def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(
        password.encode()
    ).hexdigest()


def verify_password(password, hashed):
    """Verify password against hash"""
    return hash_password(password) == hashed


# =========================================================
# Create User
# =========================================================
def create_user(
    username,
    email,
    password,
    age=25,
    health_condition="Healthy",
    fitness_level="Medium"
):
    """Create a new user account"""

    with get_db() as conn:

        cursor = conn.cursor()

        # =================================================
        # Username Exists
        # =================================================
        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE username = ?
            """,
            (username,)
        )

        if cursor.fetchone():
            return None, "Username already exists"

        # =================================================
        # Email Exists
        # =================================================
        if email:

            cursor.execute(
                """
                SELECT id
                FROM users
                WHERE email = ?
                """,
                (email,)
            )

            if cursor.fetchone():
                return None, "Email already exists"

        # =================================================
        # Hash Password
        # =================================================
        hashed_password = hash_password(password)

        # =================================================
        # Create User
        # IMPORTANT:
        # using password column
        # NOT password_hash
        # =================================================
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
            username,
            email,
            hashed_password,
            age,
            health_condition,
            fitness_level,
            0
        ))

        conn.commit()

        return (
            cursor.lastrowid,
            "User created successfully"
        )


# =========================================================
# Authenticate User
# =========================================================
def authenticate_user(username, password):
    """Authenticate user and return user data"""

    with get_db() as conn:

        cursor = conn.cursor()

        # =================================================
        # IMPORTANT FIX:
        # using password column
        # =================================================
        cursor.execute("""
            SELECT
                id,
                username,
                email,
                password,
                age,
                health_condition,
                fitness_level,
                is_admin
            FROM users
            WHERE username = ?
               OR email = ?
        """, (
            username,
            username
        ))

        user = cursor.fetchone()

        # =================================================
        # User Not Found
        # =================================================
        if not user:
            return None, "User not found"

        user = dict(user)

        # =================================================
        # Verify Password
        # =================================================
        stored_password = user.get("password")

        if not verify_password(
            password,
            stored_password
        ):
            return None, "Invalid password"

        # =================================================
        # Update Last Login
        # =================================================
        try:

            cursor.execute("""
                UPDATE users
                SET last_login = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                user["id"],
            ))

            conn.commit()

        except Exception:
            pass

        # =================================================
        # Remove Password Before Return
        # =================================================
        user.pop("password", None)

        return user, "Login successful"


# =========================================================
# Get User By ID
# =========================================================
def get_user_by_id(user_id):
    """Get user by ID"""

    with get_db() as conn:

        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id,
                username,
                email,
                age,
                health_condition,
                fitness_level,
                is_admin,
                created_at,
                last_login
            FROM users
            WHERE id = ?
        """, (
            user_id,
        ))

        user = cursor.fetchone()

        return dict(user) if user else None


# =========================================================
# Update User
# =========================================================
def update_user(user_id, **kwargs):
    """Update user fields"""

    with get_db() as conn:

        cursor = conn.cursor()

        allowed_fields = [
            "age",
            "health_condition",
            "fitness_level",
            "city_id",
            "email"
        ]

        for key, value in kwargs.items():

            if key in allowed_fields:

                try:

                    cursor.execute(
                        f"""
                        UPDATE users
                        SET {key} = ?
                        WHERE id = ?
                        """,
                        (
                            value,
                            user_id
                        )
                    )

                except Exception as e:
                    print(
                        f"Update error ({key}): {e}"
                    )

        conn.commit()

        return True


# =========================================================
# Get All Users
# =========================================================
def get_all_users():
    """Get all non-admin users"""

    with get_db() as conn:

        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id,
                username,
                email,
                age,
                health_condition,
                fitness_level,
                is_admin,
                created_at,
                last_login
            FROM users
            WHERE is_admin = 0
            ORDER BY created_at DESC
        """)

        return [
            dict(row)
            for row in cursor.fetchall()
        ]


# =========================================================
# Delete User
# =========================================================
def delete_user(user_id):
    """Delete a user"""

    with get_db() as conn:

        cursor = conn.cursor()

        try:

            # Delete related records
            cursor.execute("""
                DELETE FROM analysis_history
                WHERE user_id = ?
            """, (
                user_id,
            ))

        except Exception:
            pass

        try:

            cursor.execute("""
                DELETE FROM analysis_logs
                WHERE user_id = ?
            """, (
                user_id,
            ))

        except Exception:
            pass

        # Delete user
        cursor.execute("""
            DELETE FROM users
            WHERE id = ?
              AND is_admin = 0
        """, (
            user_id,
        ))

        conn.commit()

        return True