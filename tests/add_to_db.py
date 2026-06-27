import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# add_sample_foods.py
from database.food import add_food, get_all_foods

sample_foods = [
    ("Oatmeal", "Grains", 68, 2.4, 12, 1.4, 2.4, 55, "Heart healthy, fiber", "None"),
    ("Salmon", "Protein", 208, 22, 0, 13, 0, 0, "Omega-3 fatty acids", "Fish"),
    ("Broccoli", "Vegetables", 34, 2.8, 7, 0.4, 2.4, 15, "Vitamin C, fiber", "None"),
    ("Greek Yogurt", "Dairy", 100, 17, 6, 0.4, 0, 35, "Probiotics, protein", "Dairy"),
    ("Brown Rice", "Grains", 111, 2.6, 23, 0.9, 1.8, 50, "Complex carbs, fiber", "None"),
    ("Almonds", "Nuts", 579, 21, 22, 50, 12, 0, "Healthy fats, vitamin E", "Tree nuts"),
    ("Spinach", "Vegetables", 23, 2.9, 3.6, 0.4, 2.2, 15, "Iron-rich, folate", "None"),
    ("Sweet Potato", "Vegetables", 86, 1.6, 20, 0.1, 3, 44, "Vitamin A, fiber", "None"),
    ("Avocado", "Fruits", 160, 2, 9, 15, 7, 15, "Healthy fats, potassium", "None"),
]

for food in sample_foods:
    add_food(*food)

print(f"\n Total foods: {len(get_all_foods())}")