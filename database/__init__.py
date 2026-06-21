# database/__init__.py
from database.db import (
    init_db, get_db, save_user, get_user, 
    save_analysis, get_analysis_history, get_user_city
)
from database.exercise import get_exercises, get_exercise_details
from database.food import get_foods, get_food_details
from database.city import (
    init_city_table, get_all_cities, get_city_weather, 
    get_city_by_name, add_city, update_city, DEFAULT_CITIES
)

__all__ = [
    'init_db', 'get_db', 'save_user', 'get_user',
    'save_analysis', 'get_analysis_history', 'get_user_city',
    'get_exercises', 'get_exercise_details',
    'get_foods', 'get_food_details',
    'init_city_table', 'get_all_cities', 'get_city_weather',
    'get_city_by_name', 'add_city', 'update_city', 'DEFAULT_CITIES'
]