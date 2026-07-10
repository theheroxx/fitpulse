# database/city.py

from database.db import get_db

DEFAULT_CITIES = [
    {"name": "Tehran", "country": "Iran", "temp": 28, "humidity": 35, "wind": 12, "uv": 8,
     "pm25": 85, "pm10": 120, "co": 180, "o3": 55, "no2": 45, "so2": 12, "aqi": 142},
    {"name": "Mashhad", "country": "Iran", "temp": 24, "humidity": 40, "wind": 10, "uv": 7,
     "pm25": 65, "pm10": 95, "co": 150, "o3": 45, "no2": 35, "so2": 10, "aqi": 110},
    {"name": "Isfahan", "country": "Iran", "temp": 26, "humidity": 30, "wind": 8, "uv": 9,
     "pm25": 70, "pm10": 105, "co": 160, "o3": 50, "no2": 40, "so2": 11, "aqi": 125},
    {"name": "Shiraz", "country": "Iran", "temp": 27, "humidity": 32, "wind": 9, "uv": 8,
     "pm25": 55, "pm10": 85, "co": 140, "o3": 42, "no2": 30, "so2": 9, "aqi": 95},
    {"name": "Tabriz", "country": "Iran", "temp": 22, "humidity": 45, "wind": 14, "uv": 6,
     "pm25": 60, "pm10": 90, "co": 145, "o3": 40, "no2": 32, "so2": 8, "aqi": 105},
    {"name": "Karaj", "country": "Iran", "temp": 25, "humidity": 38, "wind": 10, "uv": 7,
     "pm25": 75, "pm10": 110, "co": 170, "o3": 48, "no2": 42, "so2": 10, "aqi": 130},
    {"name": "Yazd", "country": "Iran", "temp": 32, "humidity": 25, "wind": 8, "uv": 10,
     "pm25": 50, "pm10": 75, "co": 130, "o3": 60, "no2": 25, "so2": 8, "aqi": 85}
]

def init_city_table():
    """Initialize cities table with default data (if empty)."""
    with get_db() as conn:
        with conn.cursor() as cur:
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
            cur.execute("SELECT COUNT(*) FROM cities")
            if cur.fetchone()['count'] == 0:
                for city in DEFAULT_CITIES:
                    cur.execute("""
                        INSERT INTO cities (
                            name, country, temp, humidity, wind, uv,
                            pm25, pm10, co, o3, no2, so2, aqi
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        city["name"], city["country"],
                        city["temp"], city["humidity"], city["wind"], city["uv"],
                        city["pm25"], city["pm10"], city["co"], city["o3"],
                        city["no2"], city["so2"], city["aqi"]
                    ))
                conn.commit()
                print(f"✅ Added {len(DEFAULT_CITIES)} default cities")

def get_all_cities():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, country FROM cities ORDER BY name")
            return [dict(row) for row in cur.fetchall()]

def get_city_weather(city_id):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT temp, humidity, wind, uv, pm25, pm10, co, o3, no2, so2, aqi
                FROM cities WHERE id = %s
            """, (city_id,))
            row = cur.fetchone()
            return dict(row) if row else None

def get_city_by_name(city_name):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, country, temp, humidity, wind, uv,
                       pm25, pm10, co, o3, no2, so2, aqi
                FROM cities WHERE name = %s
            """, (city_name,))
            row = cur.fetchone()
            return dict(row) if row else None

def add_city(city_data):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO cities (
                    name, country, temp, humidity, wind, uv,
                    pm25, pm10, co, o3, no2, so2, aqi
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                city_data["name"], city_data.get("country", ""),
                city_data["temp"], city_data["humidity"], city_data["wind"], city_data["uv"],
                city_data["pm25"], city_data["pm10"], city_data["co"], city_data["o3"],
                city_data["no2"], city_data["so2"], city_data["aqi"]
            ))
            row = cur.fetchone()
            return row['id']

def update_city(city_id, city_data):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE cities SET
                    name = %s, country = %s, temp = %s, humidity = %s,
                    wind = %s, uv = %s, pm25 = %s, pm10 = %s,
                    co = %s, o3 = %s, no2 = %s, so2 = %s, aqi = %s
                WHERE id = %s
            """, (
                city_data["name"], city_data.get("country", ""),
                city_data["temp"], city_data["humidity"], city_data["wind"], city_data["uv"],
                city_data["pm25"], city_data["pm10"], city_data["co"], city_data["o3"],
                city_data["no2"], city_data["so2"], city_data["aqi"], city_id
            ))
            return cur.rowcount > 0