# api/__init__.py
"""
API package for the Fitness Advisor application.

Contains:
- app.py: FastAPI server for weather and air quality data
- weather_api.py: Client wrapper for the desktop app to call the API
"""

from api.weather_api import get_weather, get_weather_with_fallback

__all__ = [
    "get_weather",
    "get_weather_with_fallback",
]