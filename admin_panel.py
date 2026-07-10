# admin_panel.py
"""
Updated admin panel with:
- Auto-start FastAPI server if not running
- Graceful handling of missing tables
- New tables: experience_records, graph_edges in dashboard
- New page: 😊 Experience (diet check-ins)
- API status indicator in sidebar
- Consistent styling
"""

import streamlit as st
import pandas as pd
import hashlib
import requests
import subprocess
import sys
import time
import os

from database.db import (
    init_db,
    get_db,
    table_exists 
)

# =============================================================================
# CONFIG
# =============================================================================

st.set_page_config(
    page_title="Fitness AI Admin",
    page_icon="🚀",
    layout="wide"
)

# =============================================================================
# STYLE
# =============================================================================

st.markdown("""
<style>
.stApp {
    background-color: #0f172a;
    color: white;
}
section[data-testid="stSidebar"] {
    background: #111827;
    border-right: 1px solid #1f2937;
}
.main-header {
    font-size: 2.8rem;
    font-weight: 800;
    background: linear-gradient(90deg, #8b5cf6, #3b82f6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 20px;
}
.stat-card {
    background: linear-gradient(145deg, #1e293b, #111827);
    border: 1px solid #334155;
    padding: 24px;
    border-radius: 20px;
    text-align: center;
}
.stat-number {
    font-size: 2.5rem;
    font-weight: 800;
    color: #818cf8;
}
.stButton button {
    background: linear-gradient(90deg, #6366f1, #8b5cf6);
    color: white;
    border: none;
    border-radius: 12px;
    font-weight: 700;
}
[data-testid="stDataFrame"] {
    border: 1px solid #334155;
    border-radius: 12px;
}
.status-online {
    color: #22c55e;
    font-weight: 700;
}
.status-offline {
    color: #ef4444;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# INIT DB
# =============================================================================

init_db()

# =============================================================================
# HELPERS
# =============================================================================

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_dataframe(query, params=None):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            rows = cur.fetchall()
            return pd.DataFrame(rows)

def execute_query(query, params=None):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            conn.commit()


def table_exists(table_name):
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # PostgreSQL stores table names in lowercase
                cur.execute(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = %s)",
                    (table_name.lower(),)
                )
                return cur.fetchone()[0]
    except Exception:
        return False
        
def start_api_server():
    """Start the FastAPI server as a background process."""
    try:
        subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn",
                "api.app:app",
                "--host", "127.0.0.1",
                "--port", "8000",
                "--log-level", "warning"
            ],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        time.sleep(2)
        return True
    except Exception as e:
        st.error(f"Failed to start API server: {e}")
        return False

def check_api_status():
    """Check if the FastAPI server is running. If not, try to start it."""
    # First, check if it's already running
    try:
        resp = requests.get("http://127.0.0.1:8000/health", timeout=2)
        if resp.status_code == 200:
            return True
    except:
        pass

    # If not running, attempt to start it
    st.warning("API server not running. Attempting to start...")
    success = start_api_server()
    if success:
        # Verify again
        try:
            resp = requests.get("http://127.0.0.1:8000/health", timeout=2)
            if resp.status_code == 200:
                st.success("API server started successfully.")
                return True
        except:
            pass
        st.error("API server start attempt failed. Please start it manually.")
    return False

# =============================================================================
# SIDEBAR
# =============================================================================

st.sidebar.title("🚀 Fitness AI Admin")

pages = [
    "📊 Dashboard",
    "👥 Users",
    "🌍 Cities",
    "🏋️ Exercises",
    "🥗 Foods",
    "😊 Experience",
    "📈 Analysis"
]

page = st.sidebar.radio("Navigation", pages)

# API status indicator with auto-start
api_ok = check_api_status()
status_text = "🟢 Online" if api_ok else "🔴 Offline"
st.sidebar.markdown(f"**API Server:** {status_text}")

if not api_ok:
    st.sidebar.warning("Weather sync will not work. Please start the server manually.")

# =============================================================================
# DASHBOARD
# =============================================================================

if page == "📊 Dashboard":
    st.markdown('<div class="main-header">Fitness AI Dashboard</div>', unsafe_allow_html=True)

    # Load data from existing tables
    users = load_dataframe("SELECT * FROM users")
    cities = load_dataframe("SELECT * FROM cities")
    exercises = load_dataframe("SELECT * FROM exercise_library")
    foods = load_dataframe("SELECT * FROM food_library")
    analyses = load_dataframe("SELECT * FROM analysis_logs")

    # Check for optional tables
    experiences_count = 0
    if table_exists("experience_records"):
        experiences = load_dataframe("SELECT * FROM experience_records")
        experiences_count = len(experiences)

    graph_count = 0
    if table_exists("graph_edges"):
        graph_edges = load_dataframe("SELECT * FROM graph_edges")
        graph_count = len(graph_edges)

    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

    stats = [
        ("Users", len(users)),
        ("Cities", len(cities)),
        ("Exercises", len(exercises)),
        ("Foods", len(foods)),
        ("Analyses", len(analyses)),
        ("Check‑ins", experiences_count),
        ("Graph Edges", graph_count)
    ]

    for col, (title, value) in zip(
        [col1, col2, col3, col4, col5, col6, col7],
        stats
    ):
        with col:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{value}</div>
                <div>{title}</div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    st.subheader("Recent Analysis Logs")
    recent_logs = load_dataframe("""
        SELECT
            al.id,
            u.username,
            al.ed_score,
            al.risk_label,
            al.activity_type,
            al.duration,
            al.created_at
        FROM analysis_logs al
        LEFT JOIN users u ON al.user_id = u.id
        ORDER BY al.created_at DESC
        LIMIT 10
    """)
    st.dataframe(recent_logs, use_container_width=True)

    st.divider()

    if table_exists("experience_records"):
        st.subheader("Recent Diet Check‑ins")
        recent_exp = load_dataframe("""
            SELECT
                er.id,
                u.username,
                er.emoji,
                er.experience_value,
                er.created_at
            FROM experience_records er
            LEFT JOIN users u ON er.user_id = u.id
            ORDER BY er.created_at DESC
            LIMIT 10
        """)
        st.dataframe(recent_exp, use_container_width=True)

# =============================================================================
# USERS
# =============================================================================

elif page == "👥 Users":
    st.title("👥 User Management")
    users_df = load_dataframe("""
        SELECT
            u.id,
            u.username,
            u.email,
            u.age,
            u.health_condition,
            u.fitness_level,
            c.name AS city,
            u.is_admin,
            u.last_login,
            u.created_at,
            u.updated_at
        FROM users u
        LEFT JOIN cities c ON u.city_id = c.id
        ORDER BY u.id
    """)
    st.dataframe(users_df, use_container_width=True)
    st.divider()

    # Add user form
    st.subheader("➕ Add New User")
    with st.form("add_user_form"):
        col1, col2 = st.columns(2)
        with col1:
            new_username = st.text_input("Username*")
            new_email = st.text_input("Email")
            new_password = st.text_input("Password*", type="password")
            new_age = st.number_input("Age", 10, 100, 25)
        with col2:
            new_health = st.selectbox("Health Condition", ["Healthy", "Asthma", "Heart Condition", "Diabetes"])
            new_fitness = st.selectbox("Fitness Level", ["Low", "Medium", "High"])
            new_is_admin = st.checkbox("Admin User")
            new_city = st.text_input("City (optional)")
        submit_user = st.form_submit_button("Add User")
        if submit_user:
            if not new_username or not new_password:
                st.error("Username and password are required")
            else:
                try:
                    hashed_pw = hash_password(new_password)
                    city_id = None
                    if new_city:
                        city_result = load_dataframe("SELECT id FROM cities WHERE name = %s", (new_city,))
                        if not city_result.empty:
                            city_id = city_result.iloc[0]["id"]
                    execute_query("""
                        INSERT INTO users (
                            username, email, password, age,
                            health_condition, fitness_level,
                            city_id, is_admin
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (new_username, new_email, hashed_pw, new_age,
                          new_health, new_fitness, city_id, new_is_admin))
                    st.success(f"✅ User '{new_username}' created")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    st.divider()

    # Reset password
    st.subheader("🔑 Reset User Password")
    users_list = load_dataframe("SELECT id, username FROM users")
    user_options = {row["username"]: row["id"] for _, row in users_list.iterrows()}
    selected_user = st.selectbox("Select User", list(user_options.keys()))
    new_password = st.text_input("New Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")
    if st.button("Reset Password"):
        if not new_password:
            st.error("Please enter a new password")
        elif new_password != confirm_password:
            st.error("Passwords do not match")
        else:
            try:
                hashed_pw = hash_password(new_password)
                execute_query("UPDATE users SET password = %s WHERE id = %s", (hashed_pw, user_options[selected_user]))
                st.success(f"✅ Password reset for '{selected_user}'")
            except Exception as e:
                st.error(f"Error: {e}")

    st.divider()

    # Delete user
    st.subheader("🗑️ Delete User")
    user_to_delete = st.selectbox("Select User to Delete", list(user_options.keys()), key="delete_user")
    if st.button("Delete User", type="secondary"):
        try:
            user_id = user_options[user_to_delete]
            admin_count = load_dataframe("SELECT COUNT(*) as count FROM users WHERE is_admin = 1").iloc[0]["count"]
            is_admin = load_dataframe("SELECT is_admin FROM users WHERE id = %s", (user_id,)).iloc[0]["is_admin"]
            if is_admin and admin_count <= 1:
                st.error("Cannot delete the last admin user")
            else:
                execute_query("DELETE FROM analysis_logs WHERE user_id = %s", (user_id,))
                if table_exists("analysis_history"):
                    execute_query("DELETE FROM analysis_history WHERE user_id = %s", (user_id,))
                if table_exists("experience_records"):
                    execute_query("DELETE FROM experience_records WHERE user_id = %s", (user_id,))
                execute_query("DELETE FROM users WHERE id = %s", (user_id,))
                st.success(f"✅ User '{user_to_delete}' deleted")
                st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

# =============================================================================
# CITIES
# =============================================================================

elif page == "🌍 Cities":
    st.title("🌍 Cities")
    cities_df = load_dataframe("SELECT * FROM cities ORDER BY created_at DESC")
    st.dataframe(cities_df, use_container_width=True)
    st.divider()

    if not api_ok:
        st.warning("⚠️ FastAPI server is not running. Weather data in the desktop app will use fallback values.")

    st.subheader("➕ Add City")
    with st.form("city_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("City Name")
            country = st.text_input("Country")
            temp = st.number_input("Temperature", -20.0, 60.0, 25.0)
            humidity = st.number_input("Humidity", 0.0, 100.0, 40.0)
            wind = st.number_input("Wind", 0.0, 150.0, 10.0)
            uv = st.number_input("UV", 0.0, 15.0, 5.0)
        with col2:
            pm25 = st.number_input("PM2.5", 0.0, 500.0, 20.0)
            pm10 = st.number_input("PM10", 0.0, 500.0, 30.0)
            co = st.number_input("CO", 0.0, 1000.0, 100.0)
            o3 = st.number_input("O3", 0.0, 300.0, 30.0)
            no2 = st.number_input("NO2", 0.0, 300.0, 20.0)
            so2 = st.number_input("SO2", 0.0, 300.0, 10.0)
            aqi = st.number_input("AQI", 0, 500, 80)
        submit = st.form_submit_button("Add City")
        if submit:
            if not name.strip():
                st.error("City name required")
            else:
                execute_query("""
                    INSERT INTO cities (
                        name, country, temp, humidity, wind, uv,
                        pm25, pm10, co, o3, no2, so2, aqi
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (name, country, temp, humidity, wind, uv,
                      pm25, pm10, co, o3, no2, so2, aqi))
                st.success("✅ City added")
                st.rerun()

# =============================================================================
# EXERCISES
# =============================================================================

elif page == "🏋️ Exercises":
    st.title("🏋️ Exercise Library")
    df = load_dataframe("SELECT * FROM exercise_library ORDER BY created_at DESC")
    st.dataframe(df, use_container_width=True)
    st.divider()
    st.subheader("➕ Add Exercise")
    with st.form("exercise_form"):
        name = st.text_input("Exercise Name")
        ex_type = st.text_input("Type")
        intensity = st.selectbox("Intensity", ["Low", "Medium", "High"])
        duration = st.number_input("Duration (minutes)", 1, 300, 30)
        calories = st.number_input("Calories per hour", 0, 5000, 300)
        benefits = st.text_area("Benefits")
        precautions = st.text_area("Precautions")
        contraindications = st.text_area("Contraindications")
        submit = st.form_submit_button("Add Exercise")
        if submit:
            try:
                execute_query("""
                    INSERT INTO exercise_library (
                        name, type, intensity, duration_minutes,
                        calories_per_hour, benefits, precautions, contraindications
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (name, ex_type, intensity, duration, calories, benefits, precautions, contraindications))
                st.success("✅ Exercise added")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

# =============================================================================
# FOODS
# =============================================================================

elif page == "🥗 Foods":
    st.title("🥗 Food Library")
    df = load_dataframe("SELECT * FROM food_library ORDER BY created_at DESC")
    st.dataframe(df, use_container_width=True)
    st.divider()
    st.subheader("➕ Add Food")
    with st.form("food_form"):
        name = st.text_input("Food Name")
        category = st.text_input("Category")
        calories = st.number_input("Calories / 100g", 0.0, 2000.0, 100.0)
        protein = st.number_input("Protein (g)", 0.0, 100.0, 10.0)
        carbs = st.number_input("Carbs (g)", 0.0, 200.0, 20.0)
        fat = st.number_input("Fat (g)", 0.0, 100.0, 5.0)
        fiber = st.number_input("Fiber (g)", 0.0, 100.0, 3.0)
        glycemic_index = st.number_input("Glycemic Index", 0, 150, 50)
        benefits = st.text_area("Benefits")
        allergens = st.text_area("Allergens")
        submit = st.form_submit_button("Add Food")
        if submit:
            try:
                execute_query("""
                    INSERT INTO food_library (
                        name, category, calories_per_100g, protein_g,
                        carbs_g, fat_g, fiber_g, glycemic_index,
                        benefits, allergens
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (name, category, calories, protein, carbs, fat, fiber, glycemic_index, benefits, allergens))
                st.success("✅ Food added")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

# =============================================================================
# EXPERIENCE (Diet Check-ins)
# =============================================================================

elif page == "😊 Experience":
    st.title("😊 Diet Check‑ins")

    # ── Bypass table_exists check ─────────────────────────────
    try:
        df = load_dataframe("""
            SELECT
                er.id,
                u.username,
                er.emoji,
                er.experience_value,
                er.created_at
            FROM experience_records er
            LEFT JOIN users u ON er.user_id = u.id
            ORDER BY er.created_at DESC
        """)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.stop()

    if df.empty:
        st.info("No diet check‑in records yet.")
        st.stop()

    st.dataframe(df, use_container_width=True)

    st.divider()

    st.subheader("📊 Summary by Emoji")
    summary = load_dataframe("""
        SELECT
            emoji,
            COUNT(*) as count,
            ROUND(AVG(CASE experience_value WHEN 'good' THEN 3 WHEN 'neutral' THEN 2 WHEN 'bad' THEN 1 END), 2) as avg_score
        FROM experience_records
        GROUP BY emoji
        ORDER BY count DESC
    """)
    st.dataframe(summary, use_container_width=True)

    # Optional: Add a manual insert (for testing)
    st.divider()
    with st.expander("➕ Add Test Check‑in"):
        with st.form("add_exp_form"):
            user_id = st.number_input("User ID", min_value=1, step=1)
            emoji = st.selectbox("Emoji", ["😊", "😐", "☹️"])
            value = st.selectbox("Value", ["good", "neutral", "bad"])
            submit_exp = st.form_submit_button("Add Check‑in")
            if submit_exp:
                try:
                    execute_query(
                        "INSERT INTO experience_records (user_id, experience_value, emoji) VALUES (%s, %s, %s)",
                        (user_id, value, emoji)
                    )
                    st.success("✅ Check‑in added")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# =============================================================================
# ANALYSIS
# =============================================================================

elif page == "📈 Analysis":
    st.title("📈 Analysis Logs")
    df = load_dataframe("""
        SELECT
            al.id,
            u.username,
            al.ed_score,
            al.risk_label,
            al.activity_type,
            al.duration,
            al.created_at
        FROM analysis_logs al
        LEFT JOIN users u ON al.user_id = u.id
        ORDER BY al.created_at DESC
    """)
    st.dataframe(df, use_container_width=True)

    st.divider()

    if table_exists("analysis_history"):
        st.subheader("📜 Analysis History")
        history_df = load_dataframe("""
            SELECT
                ah.id,
                u.username,
                ah.result,
                ah.created_at
            FROM analysis_history ah
            LEFT JOIN users u ON ah.user_id = u.id
            ORDER BY ah.created_at DESC
        """)
        st.dataframe(history_df, use_container_width=True)