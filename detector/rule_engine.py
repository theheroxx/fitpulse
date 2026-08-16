# detector/rule_engine.py
from detector.rules import evaluate_rules
from detector.confidence import calculate_confidence
from detector.normalizer import normalize_input
import joblib
import os
import numpy as np
import pandas as pd

_lgbm_model = None
_lgbm_features = None
_lgbm_encoder = None
_ml_available = False

def _load_ml_model():
    global _lgbm_model, _lgbm_features, _lgbm_encoder, _ml_available
    
    base_path = r"D:\ED\LGBM"
    model_path = os.path.join(base_path, "detector_lgbm.pkl")
    features_path = os.path.join(base_path, "lgbm_features.pkl")
    encoder_path = os.path.join(base_path, "lgbm_label_encoder.pkl")
    
    if os.path.exists(model_path):
        try:
            _lgbm_model = joblib.load(model_path)
            if os.path.exists(features_path):
                _lgbm_features = joblib.load(features_path)
            if os.path.exists(encoder_path):
                _lgbm_encoder = joblib.load(encoder_path)
            _ml_available = True
            return
        except Exception as e:
            print(f"Failed to load LightGBM model: {e}")
    
    _ml_available = False

_load_ml_model()

def ed_to_risk_level(ed_score):
    if ed_score >= 80:
        return 4
    elif ed_score >= 65:
        return 3
    elif ed_score >= 45:
        return 2
    elif ed_score >= 30:
        return 1
    else:
        return 0

def check_hard_rules(data, ed_score):
    health = data.get("HealthCondition", "Healthy")
    activity = data.get("ActivityType", "Mid Cardio")
    duration = data.get("DurationMins", 30)
    tod = data.get("TimeOfDay", "Morning")
    
    if ed_score >= 80:
        return 100, ["Extreme environmental risk"], "Unsafe", 1.0
    
    if health == "Heart Condition" and activity == "High Cardio":
        return 100, ["Heart Condition: High Cardio unsafe"], "Unsafe", 1.0
    
    if ed_score >= 50 and health == "Asthma" and tod == "Afternoon" and activity in ["High Cardio", "Mid Cardio"]:
        return 100, ["Asthma + bad air + afternoon unsafe"], "Unsafe", 1.0
    
    if ed_score >= 50 and health == "Diabetes" and activity in ["High Cardio", "Mid Cardio"]:
        return 100, ["Diabetes + bad air quality unsafe"], "Unsafe", 1.0
    
    if ed_score >= 50 and tod == "Afternoon" and activity == "High Cardio":
        return 100, ["Bad ED + Afternoon + High Cardio unsafe"], "Unsafe", 1.0
    
    if duration > 120:
        return 100, ["Duration exceeds 120 minutes"], "Unsafe", 1.0
    
    return None

def ml_predict(data, ed_score, ed_raw=None, risk_score=None):
    if not _ml_available or _lgbm_model is None:
        return None
    
    try:
        features = {
            'Age': data.get('Age', 30),
            'DurationMins': data.get('DurationMins', 30),
            'ED': ed_score,
            'ED_raw': ed_raw if ed_raw is not None else ed_score,
            'RiskScore': risk_score if risk_score is not None else ed_score,
            'ED_Risk_Level': ed_to_risk_level(ed_score),
            'HealthCondition': data.get('HealthCondition', 'Healthy'),
            'FitnessLevel': data.get('FitnessLevel', 'Medium'),
            'ActivityType': data.get('ActivityType', 'Low Cardio'),
            'TimeOfDay': data.get('TimeOfDay', 'Morning')
        }
        
        X = pd.DataFrame([features])
        categorical_cols = ['HealthCondition', 'FitnessLevel', 'ActivityType', 'TimeOfDay']
        X = pd.get_dummies(X, columns=categorical_cols)
        
        if _lgbm_features:
            for col in _lgbm_features:
                if col not in X.columns:
                    X[col] = 0
            X = X[_lgbm_features]
        
        pred_label_encoded = _lgbm_model.predict(X)[0]
        pred_proba = _lgbm_model.predict_proba(X)[0]
        confidence = np.max(pred_proba)
        
        if _lgbm_encoder:
            label = _lgbm_encoder.inverse_transform([pred_label_encoded])[0]
        else:
            label_map = {0: "Safe", 1: "Moderate", 2: "Unsafe"}
            label = label_map.get(pred_label_encoded, "Moderate")
        
        score_map = {"Safe": 20, "Moderate": 50, "Unsafe": 80}
        score = score_map.get(label, 50)
        
        reasons = [f"ML prediction (confidence: {confidence:.2f})"]
        
        return score, reasons, label, confidence
        
    except Exception as e:
        print(f"ML prediction failed: {e}")
        return None

def rule_based_detector(input_data):
    data = normalize_input(input_data)
    ed_score = data.get("ED", 50)
    ed_raw = data.get("ED_raw", ed_score)
    risk_score = data.get("RiskScore", ed_score)
    
    hard_result = check_hard_rules(data, ed_score)
    if hard_result is not None:
        score, reasons, label, confidence = hard_result
        return {
            "label": label,
            "confidence": confidence,
            "score": score,
            "reasons": reasons,
            "normalized_input": data
        }
    
    ml_result = ml_predict(data, ed_score, ed_raw, risk_score)
    
    if ml_result is not None:
        score, reasons, label, confidence = ml_result
        if confidence > 0.70:
            return {
                "label": label,
                "confidence": confidence,
                "score": score,
                "reasons": reasons,
                "normalized_input": data
            }
    
    score, reasons, rule_label, rule_confidence = evaluate_rules(data)
    
    if rule_label:
        label = rule_label
    else:
        if score >= 70:
            label = "Unsafe"
        elif score >= 40:
            label = "Moderate"
        else:
            label = "Safe"
    
    if rule_confidence:
        confidence = rule_confidence
    else:
        confidence = calculate_confidence(score, reasons)
    
    return {
        "label": label,
        "confidence": confidence,
        "score": score,
        "reasons": reasons,
        "normalized_input": data
    }