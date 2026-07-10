import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import get_db

with get_db() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM food_library")
        print(f"count: {cur.fetchone()['count']}")