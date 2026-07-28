# core/user_profile.py

from database.db import save_user, get_user, init_db


# =============================================================================
# SAVE PROFILE (for new user)
# =============================================================================

def save_profile(data):
    """Save new user profile (creates new record)"""
    try:
        init_db()

        city_id = data.get("city_id")

        # Support city name lookup
        if not city_id:
            city_name = data.get("City") or data.get("city_name")
            if city_name:
                try:
                    from database.city import get_city_by_name
                    city = get_city_by_name(city_name)
                    if city:
                        city_id = city["id"]
                except:
                    pass

        user_id = save_user(
            age=data.get("Age", 25),
            health_condition=data.get("HealthCondition", "Healthy"),
            fitness_level=data.get("FitnessLevel", "Medium"),
            city_id=city_id,
            username=data.get("username"),
            email=data.get("email")
        )

        print(f"✅ Profile saved successfully (ID: {user_id})")
        return user_id

    except Exception as e:
        print(f"❌ Error saving profile: {e}")
        raise


# =============================================================================
# UPDATE PROFILE (for editing existing user) - FIXED
# =============================================================================

def update_profile(data):
    """Update existing user profile"""
    try:
        init_db()

        city_id = data.get("city_id")

        # Support city name lookup
        if not city_id:
            city_name = data.get("City") or data.get("city_name")
            if city_name:
                try:
                    from database.city import get_city_by_name
                    city = get_city_by_name(city_name)
                    if city:
                        city_id = city["id"]
                except:
                    pass

        # First, get the existing user
        existing_user = get_user()
        
        if existing_user:
            # Get the user ID from existing record
            user_id = existing_user["id"]
            
            # ─── FIX: Use %s instead of ? for PostgreSQL ────────
            from database.db import get_db
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users
                    SET age = %s,
                        health_condition = %s,
                        fitness_level = %s,
                        city_id = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (
                    data.get("Age", 25),
                    data.get("HealthCondition", "Healthy"),
                    data.get("FitnessLevel", "Medium"),
                    city_id,
                    user_id
                ))
                conn.commit()
            
            print(f"✅ Profile updated successfully (ID: {user_id})")
            return user_id
        else:
            # No existing user, create new one
            return save_profile(data)

    except Exception as e:
        print(f"❌ Error updating profile: {e}")
        raise


# =============================================================================
# LOAD PROFILE
# =============================================================================

def load_profile():
    """Load user profile from database"""
    try:
        init_db()
        user = get_user()

        if user:
            profile = {
                "Age": user.get("age", 25),
                "HealthCondition": user.get("health_condition", "Healthy"),
                "FitnessLevel": user.get("fitness_level", "Medium"),
                "city_id": user.get("city_id")
            }

            if user.get("city_name"):
                profile["City"] = user["city_name"]
            
            if user.get("username"):
                profile["username"] = user["username"]
            
            if user.get("email"):
                profile["email"] = user["email"]

            print(f"✅ Profile loaded: {profile}")
            return profile

        print("ℹ️ No profile found")
        return None

    except Exception as e:
        print(f"❌ Error loading profile: {e}")
        return None


# =============================================================================
# USER CITY WEATHER
# =============================================================================

def load_user_city_weather():
    try:
        from database.db import get_user_city
        return get_user_city()
    except Exception as e:
        print(f"❌ Error loading city weather: {e}")
        return None