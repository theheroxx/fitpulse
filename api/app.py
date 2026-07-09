# api/app.py
"""
FastAPI server using Open-Meteo (free, no API key).
Combines weather + air quality data for the ED system.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional

# ─── Config ──────────────────────────────────────────────────────────
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

# ─── App ────────────────────────────────────────────────────────────
app = FastAPI(
    title="Fitness Advisor Weather API (Open-Meteo)",
    description="Free weather and air quality data using Open-Meteo",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Simple Cache ──────────────────────────────────────────────────
_cache: Dict[str, tuple] = {}
CACHE_TTL = 600  # 10 minutes

def _get_cache_key(city: str) -> str:
    return city.lower().strip()

def _get_cached(city: str) -> Optional[Dict]:
    key = _get_cache_key(city)
    if key in _cache:
        data, timestamp = _cache[key]
        if (datetime.now() - timestamp).seconds < CACHE_TTL:
            return data
    return None

def _set_cache(city: str, data: Dict):
    key = _get_cache_key(city)
    _cache[key] = (data, datetime.now())

# ─── Geocoding ──────────────────────────────────────────────────────
def get_coordinates(city: str) -> tuple:
    """Convert city name to latitude/longitude."""
    params = {"name": city, "count": 1, "language": "en", "format": "json"}
    resp = requests.get(GEOCODING_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("results"):
        raise HTTPException(status_code=404, detail=f"City '{city}' not found")
    result = data["results"][0]
    return result["latitude"], result["longitude"], result["name"], result["country"]

# ─── Endpoints ──────────────────────────────────────────────────────

@app.get("/")
def home():
    return {
        "message": "Fitness Advisor Weather API (Open-Meteo)",
        "endpoints": {
            "/weather?city=London": "Get weather + air quality",
            "/health": "Health check"
        }
    }

@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/weather")
def get_weather(city: str = Query(..., min_length=1)):
    """Get current weather + air quality for a city."""
    # 1. Check cache
    cached = _get_cached(city)
    if cached:
        return cached

    # 2. Geocode city → lat/lon
    try:
        lat, lon, city_name, country = get_coordinates(city)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"City not found: {str(e)}")

    # 3. Fetch weather
    weather_params = {
        "latitude": lat,
        "longitude": lon,
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "precipitation",
            "weather_code",
            "cloud_cover",
            "wind_speed_10m",
            "uv_index"
        ],
        "timezone": "auto"
    }
    try:
        w_resp = requests.get(WEATHER_URL, params=weather_params, timeout=10)
        w_resp.raise_for_status()
        w_data = w_resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Weather API error: {str(e)}")

    # 4. Fetch air quality
    aq_params = {
        "latitude": lat,
        "longitude": lon,
        "current": [
            "pm10",
            "pm2_5",
            "carbon_monoxide",
            "nitrogen_dioxide",
            "sulphur_dioxide",
            "ozone"
        ],
        "timezone": "auto"
    }
    try:
        aq_resp = requests.get(AIR_QUALITY_URL, params=aq_params, timeout=10)
        aq_resp.raise_for_status()
        aq_data = aq_resp.json()
    except Exception as e:
        # Air quality is optional; return weather without it
        print(f"Air quality API error: {e}")
        aq_data = {"current": {}}

    current_w = w_data.get("current", {})
    current_aq = aq_data.get("current", {})

    # Weather code to condition text
    weather_codes = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Fog", 48: "Depositing rime fog",
        51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
        61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        71: "Slight snow fall", 73: "Moderate snow fall", 75: "Heavy snow fall",
        80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
        95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
    }
    weather_code = current_w.get("weather_code", 0)
    condition = weather_codes.get(weather_code, "Unknown")

    result = {
        "city": city_name,
        "country": country,
        "temperature": current_w.get("temperature_2m"),
        "humidity": current_w.get("relative_humidity_2m"),
        "wind_kph": current_w.get("wind_speed_10m"),
        "uv": current_w.get("uv_index"),
        "condition": condition,
        "air_quality": {
            "pm2_5": current_aq.get("pm2_5"),
            "pm10": current_aq.get("pm10"),
            "co": current_aq.get("carbon_monoxide"),
            "no2": current_aq.get("nitrogen_dioxide"),
            "so2": current_aq.get("sulphur_dioxide"),
            "o3": current_aq.get("ozone"),
        }
    }

    _set_cache(city, result)
    return result

# ─── Run ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)