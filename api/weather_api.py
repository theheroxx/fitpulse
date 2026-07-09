# api/weather_api.py
import requests
from typing import Dict, Any, Optional

API_BASE_URL = "http://127.0.0.1:8000"

def get_weather(city: str) -> Dict[str, Any]:
    url = f"{API_BASE_URL}/weather"
    params = {"city": city}
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    return {
        "temperature": data["temperature"],
        "humidity": data["humidity"],
        "wind_kph": data["wind_kph"],
        "uv": data["uv"],
        "pm25": data["air_quality"]["pm2_5"],
        "pm10": data["air_quality"]["pm10"],
        "co": data["air_quality"]["co"],
        "o3": data["air_quality"]["o3"],
        "no2": data["air_quality"]["no2"],
        "so2": data["air_quality"]["so2"],
    }

def get_weather_with_fallback(city: str, fallback: Optional[Dict] = None) -> Dict[str, Any]:
    if fallback is None:
        fallback = {
            "temperature": 22, "humidity": 45, "wind_kph": 10, "uv": 3,
            "pm25": 25, "pm10": 45, "co": 200, "o3": 40, "no2": 10, "so2": 5,
        }
    try:
        return get_weather(city)
    except Exception as e:
        print(f"Weather API error: {e}")
        return fallback