# detector/normalizer.py
def normalize_input(data):
    """
    Normalize all inputs to standard format
    """
    normalized = {}
    
    # Health Condition - convert to exact match for rules
    health = str(data.get("HealthCondition", "Healthy"))
    if "asthma" in health.lower():
        normalized["HealthCondition"] = "Asthma"
    elif "heart" in health.lower():
        normalized["HealthCondition"] = "Heart Condition"
    elif "diabet" in health.lower():
        normalized["HealthCondition"] = "Diabetes"
    else:
        normalized["HealthCondition"] = "Healthy"
    
    # Fitness Level - capitalize properly
    fitness = str(data.get("FitnessLevel", "Medium"))
    if fitness.lower() == "low":
        normalized["FitnessLevel"] = "Low"
    elif fitness.lower() == "high":
        normalized["FitnessLevel"] = "High"
    else:
        normalized["FitnessLevel"] = "Medium"
    
    # Activity Type
    activity = str(data.get("ActivityType", "Low Cardio"))
    if "low" in activity.lower():
        normalized["ActivityType"] = "Low Cardio"
    elif "mid" in activity.lower() or "moderate" in activity.lower():
        normalized["ActivityType"] = "Mid Cardio"
    elif "high" in activity.lower():
        normalized["ActivityType"] = "High Cardio"
    elif "strength" in activity.lower():
        normalized["ActivityType"] = "Strength"
    else:
        normalized["ActivityType"] = "Low Cardio"
    
    # Time of Day
    time = str(data.get("TimeOfDay", "Morning"))
    if "morning" in time.lower():
        normalized["TimeOfDay"] = "Morning"
    elif "afternoon" in time.lower():
        normalized["TimeOfDay"] = "Afternoon"
    elif "evening" in time.lower():
        normalized["TimeOfDay"] = "Evening"
    else:
        normalized["TimeOfDay"] = "Night"
    
    # Numbers
    normalized["Age"] = int(data.get("Age", 30))
    normalized["DurationMins"] = int(data.get("DurationMins", 30))
    normalized["ED"] = float(data.get("ED", 0))
    
    print(f"🔄 NORMALIZED: {normalized}")  # Debug
    
    return normalized