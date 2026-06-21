# database/city.py
import sqlite3
import os
from database.db import get_db, DB_PATH

# Default city weather data
DEFAULT_CITIES = [
    {
        "name": "Tehran",
        "country": "Iran",
        "temp": 28,
        "humidity": 35,
        "wind": 12,
        "uv": 8,
        "pm25": 85,
        "pm10": 120,
        "co": 180,
        "o3": 55,
        "no2": 45,
        "so2": 12,
        "aqi": 142
    },
    {
        "name": "Mashhad",
        "country": "Iran",
        "temp": 24,
        "humidity": 40,
        "wind": 10,
        "uv": 7,
        "pm25": 65,
        "pm10": 95,
        "co": 150,
        "o3": 45,
        "no2": 35,
        "so2": 10,
        "aqi": 110
    },
    {
        "name": "Isfahan",
        "country": "Iran",
        "temp": 26,
        "humidity": 30,
        "wind": 8,
        "uv": 9,
        "pm25": 70,
        "pm10": 105,
        "co": 160,
        "o3": 50,
        "no2": 40,
        "so2": 11,
        "aqi": 125
    },
    {
        "name": "Shiraz",
        "country": "Iran",
        "temp": 27,
        "humidity": 32,
        "wind": 9,
        "uv": 8,
        "pm25": 55,
        "pm10": 85,
        "co": 140,
        "o3": 42,
        "no2": 30,
        "so2": 9,
        "aqi": 95
    },
    {
        "name": "Tabriz",
        "country": "Iran",
        "temp": 22,
        "humidity": 45,
        "wind": 14,
        "uv": 6,
        "pm25": 60,
        "pm10": 90,
        "co": 145,
        "o3": 40,
        "no2": 32,
        "so2": 8,
        "aqi": 105
    },
    {
        "name": "Karaj",
        "country": "Iran",
        "temp": 25,
        "humidity": 38,
        "wind": 10,
        "uv": 7,
        "pm25": 75,
        "pm10": 110,
        "co": 170,
        "o3": 48,
        "no2": 42,
        "so2": 10,
        "aqi": 130
    },
    {
        "name": "Yazd",
        "country": "Iran",
        "temp": 32,
        "humidity": 25,
        "wind": 8,
        "uv": 10,
        "pm25": 50,
        "pm10": 75,
        "co": 130,
        "o3": 60,
        "no2": 25,
        "so2": 8,
        "aqi": 85
    }
]


def init_city_table():
    """Initialize cities table with default data"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Create cities table
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
        
        # Insert default cities if table is empty
        cursor.execute("SELECT COUNT(*) FROM cities")
        count = cursor.fetchone()[0]
        
        if count == 0:
            for city in DEFAULT_CITIES:
                cursor.execute("""
                    INSERT INTO cities (
                        name, country, temp, humidity, wind, uv,
                        pm25, pm10, co, o3, no2, so2, aqi
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    city["name"], city["country"],
                    city["temp"], city["humidity"], city["wind"], city["uv"],
                    city["pm25"], city["pm10"], city["co"], city["o3"],
                    city["no2"], city["so2"], city["aqi"]
                ))
            print(f"✅ Added {len(DEFAULT_CITIES)} default cities")


def get_all_cities():
    """Get list of all cities"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, country FROM cities ORDER BY name")
        return cursor.fetchall()


def get_city_weather(city_id):
    """Get weather data for a specific city"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT temp, humidity, wind, uv, pm25, pm10, co, o3, no2, so2, aqi
            FROM cities WHERE id = ?
        """, (city_id,))
        result = cursor.fetchone()
        if result:
            return dict(result)
        return None


def get_city_by_name(city_name):
    """Get city by name"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, country, temp, humidity, wind, uv, 
                   pm25, pm10, co, o3, no2, so2, aqi
            FROM cities WHERE name = ?
        """, (city_name,))
        result = cursor.fetchone()
        if result:
            return dict(result)
        return None


def add_city(city_data):
    """Add a new city to database"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO cities (
                name, country, temp, humidity, wind, uv,
                pm25, pm10, co, o3, no2, so2, aqi
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            city_data["name"], city_data.get("country", ""),
            city_data["temp"], city_data["humidity"], city_data["wind"], city_data["uv"],
            city_data["pm25"], city_data["pm10"], city_data["co"], city_data["o3"],
            city_data["no2"], city_data["so2"], city_data["aqi"]
        ))
        return cursor.lastrowid


def update_city(city_id, city_data):
    """Update existing city data"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE cities SET
                name = ?, country = ?, temp = ?, humidity = ?, wind = ?, uv = ?,
                pm25 = ?, pm10 = ?, co = ?, o3 = ?, no2 = ?, so2 = ?, aqi = ?
            WHERE id = ?
        """, (
            city_data["name"], city_data.get("country", ""),
            city_data["temp"], city_data["humidity"], city_data["wind"], city_data["uv"],
            city_data["pm25"], city_data["pm10"], city_data["co"], city_data["o3"],
            city_data["no2"], city_data["so2"], city_data["aqi"], city_id
        ))