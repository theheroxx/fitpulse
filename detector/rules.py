# rules.py
def evaluate_rules(data):
    ED = data.get("ED", 0)
    age = data.get("Age", 30)
    health = data.get("HealthCondition", "Healthy")
    fitness = data.get("FitnessLevel", "Medium")
    activity = data.get("ActivityType", "Mid Cardio")
    duration = data.get("DurationMins", 30)
    tod = data.get("TimeOfDay", "Morning")
    
    age_group = "Child/Teen" if age <= 17 else ("Adult" if age <= 64 else "Older Adult")
    ed_state = "good" if ED < 50 else "bad"
    
    score = 0
    reasons = []
    
    if ED >= 80:
        return 100, [f"Extreme environmental risk (ED={ED:.1f})"], "Unsafe", 1.0
    
    if ED >= 70:
        return 95, [f"Very high environmental risk (ED={ED:.1f})"], "Unsafe", 0.98
    
    if duration > 120:
        return 100, ["Duration exceeds 120 minutes"], "Unsafe", 1.0
    
    if health == "Heart Condition" and activity == "High Cardio":
        return 100, ["High Cardio unsafe for Heart Disease"], "Unsafe", 1.0
    
    if ed_state == "bad" and health == "Asthma" and activity in ["High Cardio", "Mid Cardio"]:
        return 100, ["Bad ED + Asthma + cardio unsafe"], "Unsafe", 1.0
    
    if ed_state == "bad" and health == "Diabetes" and activity in ["High Cardio", "Mid Cardio"]:
        return 100, ["Bad ED + outdoor cardio unsafe for Diabetes"], "Unsafe", 1.0
    
    if ed_state == "bad" and tod == "Afternoon" and activity == "High Cardio":
        return 100, ["Bad ED + Afternoon + High Cardio unsafe"], "Unsafe", 1.0
    
    if ed_state == "good":
        if health == "Asthma" and activity in ["High Cardio", "Mid Cardio"]:
            score += 30
            reasons.append("Asthma + cardio: moderate danger baseline")
        
        if (activity == "High Cardio" and duration <= 30 and health == "Healthy" and 
            fitness == "High" and age_group in ["Adult", "Older Adult"]):
            score -= 20
            reasons.append("Good ED: 30 min High Cardio safe for Healthy High Fitness Adult/Older Adult")
        
        elif (activity == "High Cardio" and duration == 60 and health == "Healthy" and 
              fitness == "Medium" and tod in ["Morning", "Evening"] and age_group == "Adult"):
            score += 30
            reasons.append("Good ED: 60 min High Cardio moderate for Healthy Medium Fitness Adult")
        
        elif (activity == "High Cardio" and duration > 30 and health == "Healthy" and fitness == "Low"):
            score += 70
            reasons.append("Good ED: >30 min High Cardio unsafe for Healthy Low Fitness")
        
        elif (activity == "Mid Cardio" and duration == 60 and health == "Healthy"):
            score -= 15
            reasons.append("Good ED: 60 min Mid Cardio safe for all Healthy")
        
        elif (activity == "High Cardio" and duration <= 20 and health == "Asthma" and 
              fitness in ["Medium", "High"] and tod == "Morning"):
            score += 25
            reasons.append("Good ED: ≤20 min High Cardio moderate for controlled Asthma, Morning")
        
        elif (activity == "High Cardio" and duration > 30 and health == "Asthma"):
            score += 80
            reasons.append("Good ED: >30 min High Cardio unsafe for Asthma")
        
        elif (activity == "Mid Cardio" and 20 <= duration <= 30 and tod == "Morning" and 
              health == "Asthma" and fitness == "Low"):
            score -= 10
            reasons.append("Good ED: 20-30 min Mid Cardio Morning safe for Asthma Low Fitness")
        
        elif (activity == "Low Cardio" and 10 <= duration <= 30 and health == "Heart Condition" and 
              fitness == "Low" and tod == "Morning"):
            score -= 15
            reasons.append("Good ED: Low Cardio safe for Heart Disease Low Fitness Morning")
        
        elif (activity == "Mid Cardio" and 20 <= duration <= 40 and health == "Heart Condition" and 
              fitness == "Medium" and tod == "Evening"):
            score += 30
            reasons.append("Good ED: Mid Cardio moderate for Heart Disease Medium Fitness Evening")
        
        elif (activity == "Mid Cardio" and 30 <= duration <= 60 and tod == "Afternoon" and 
              health == "Diabetes" and fitness == "Medium"):
            score -= 10
            reasons.append("Good ED: Mid Cardio Afternoon safe for Diabetes Medium Fitness")
        
        elif (activity == "High Cardio" and 45 <= duration <= 60 and tod == "Evening" and 
              health == "Diabetes" and fitness == "High" and age_group == "Adult"):
            score += 30
            reasons.append("Good ED: High Cardio moderate for Diabetes High Fitness Evening")
        
        elif (activity == "Low Cardio" and 15 <= duration <= 20 and tod == "Morning" and 
              health == "Diabetes" and fitness == "Low"):
            score -= 10
            reasons.append("Good ED: Low Cardio safe for Diabetes Low Fitness Morning")
        
        elif (activity == "Low Cardio" and duration < 30):
            score -= 15
            reasons.append("Good ED: Indoor Low Cardio safe for all")
        
        elif activity == "Low Cardio":
            score -= 10
            reasons.append("Good ED: Low Cardio generally safe")
        
        else:
            score += 20
            reasons.append("Good ED: moderate risk - follow general precautions")
    
    else:
        score += 65
        reasons.append("Bad environmental quality - high risk for exercise")
        
        if (activity == "High Cardio" and health == "Healthy" and 
            tod == "Afternoon" and duration > 20):
            score += 25
            reasons.append("Bad ED: High Cardio Afternoon unsafe for Healthy")
        
        elif (activity == "Mid Cardio" and duration < 60 and tod == "Morning"):
            if age_group == "Child/Teen":
                score -= 10
                reasons.append("Bad ED: Morning indoor Mid Cardio safer for Child/Teen")
            elif age_group == "Older Adult":
                score += 20
                reasons.append("Bad ED: Morning indoor Mid Cardio moderate for Older Adult")
            else:
                score += 15
                reasons.append("Bad ED: Morning indoor Mid Cardio moderate")
        
        elif (health == "Heart Condition" and activity in ["Mid Cardio", "High Cardio"]):
            score += 35
            reasons.append("Bad ED: any Mid/High Cardio unsafe for Heart Disease")
        
        elif (health == "Healthy" and activity == "High Cardio" and duration >= 20):
            score += 25
            reasons.append("Bad ED: Healthy restrict High Cardio to <20 min")
        
        elif (health == "Asthma" and activity in ["High Cardio", "Mid Cardio"]):
            score += 35
            reasons.append("Bad ED: cardio very risky for Asthma - avoid outdoor")
        
        if activity == "High Cardio":
            score += 15
            reasons.append("High intensity exercise in bad conditions significantly increases risk")
        elif activity == "Mid Cardio":
            score += 10
            reasons.append("Moderate intensity still risky in bad environmental conditions")
    
    if age_group == "Older Adult":
        if activity == "High Cardio" and duration > 30:
            score += 40
            reasons.append("Older Adult: High Cardio >30 min risky")
        elif activity == "Low Cardio":
            score -= 10
            reasons.append("Older Adult: Low Cardio beneficial")
        else:
            score += 15
            reasons.append("Older Adult: extra caution needed")
    
    if age_group == "Child/Teen":
        if activity == "High Cardio" and duration > 45:
            score += 30
            reasons.append("Child/Teen: High Cardio >45 min risky")
        elif activity == "Low Cardio":
            score -= 5
            reasons.append("Child/Teen: Low Cardio safe")
    
    if fitness == "Low":
        if activity == "High Cardio" and duration > 20:
            score += 40
            reasons.append("Low Fitness: High Cardio >20 min unsafe")
        elif activity == "Low Cardio":
            score -= 10
            reasons.append("Low Fitness: Low Cardio recommended")
        else:
            score += 15
            reasons.append("Low Fitness: start gradually")
    elif fitness == "High":
        if activity in ["Mid Cardio", "Low Cardio"]:
            score -= 15
            reasons.append("High Fitness: can tolerate higher intensity")
    
    if duration > 90:
        score += 40
        reasons.append("Duration >90 min: unsafe unless well-conditioned")
    elif duration <= 20:
        score -= 10
        reasons.append("Short duration (≤20 min): safer")
    
    if tod == "Morning":
        score -= 5
        reasons.append("Morning exercise generally safer")
    elif tod == "Afternoon" and ed_state == "bad":
        score += 20
        reasons.append("Afternoon + bad ED: increased risk")
    elif tod == "Evening":
        if activity == "High Cardio":
            score += 10
            reasons.append("Evening High Cardio may disrupt sleep")
    
    if health == "Heart Condition":
        if activity != "Low Cardio":
            score += 30
            reasons.append("Heart Condition: only Low Cardio recommended")
    elif health == "Asthma":
        if ed_state == "bad" and activity in ["High Cardio", "Mid Cardio"]:
            score += 40
            reasons.append("Asthma: avoid cardio in bad air quality")
    elif health == "Diabetes":
        if ed_state == "bad":
            score += 30
            reasons.append("Diabetes: high risk in bad environmental conditions")
    
    score = max(0, min(100, score))
    
    if score >= 70:
        label = "Unsafe"
        confidence = 0.9 + (score - 70) / 100
    elif score >= 40:
        label = "Moderate"
        confidence = 0.6 + (score - 40) / 100
    else:
        label = "Safe"
        confidence = 0.5 + (40 - score) / 100
    
    confidence = min(0.99, confidence)
    
    return score, reasons, label, confidence