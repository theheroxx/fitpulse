import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from detector.rule_engine import rule_based_detector

data = {
    "ED": 85,
    "Age": 70,
    "HealthCondition": "Asthma",
    "FitnessLevel": "Low",
    "ActivityType": "High Cardio",
    "DurationMins": 45,
    "TimeOfDay": "Afternoon"
}

result = rule_based_detector(data)
print(result)