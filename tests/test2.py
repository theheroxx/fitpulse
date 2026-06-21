import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.orchestrator import run_pipeline

from transformer.recommender import generate_recommendation

user = {
    "Age": 65,
    "HealthCondition": "Asthma",
    "FitnessLevel": "Low",
    "ActivityType": "High Cardio",
    "DurationMins": 40,
    "TimeOfDay": "Afternoon",
    "ED": 85
}

detector_output = {
    "label": "Unsafe",
    "confidence": 92 # /100
}

print(generate_recommendation(user, detector_output))