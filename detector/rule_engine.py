# # detector/rule_engine.py
# from detector.rules import evaluate_rules
# from detector.confidence import calculate_confidence
# from detector.normalizer import normalize_input
# import pickle 


# def rule_based_detector(input_data):
#     """
#     Full pipeline:
#     normalize → evaluate → classify → confidence
#     """

#     data = normalize_input(input_data)
    
#     # Debug: Print input to rules
#     print(f"🔍 RULES INPUT: Health={data.get('HealthCondition')}, "
#           f"Activity={data.get('ActivityType')}, Duration={data.get('DurationMins')}, "
#           f"ED={data.get('ED')}, TimeOfDay={data.get('TimeOfDay')}")

#     # Get ALL 4 values from evaluate_rules
#     score, reasons, rule_label, rule_confidence = evaluate_rules(data)
    
#     print(f"📊 RULES OUTPUT: score={score}, label={rule_label}, confidence={rule_confidence}, reasons={reasons}")

#     # Use the label from rules - this is the important part!
#     if rule_label:
#         label = rule_label
#     else:
#         # Fallback classification (should not happen if rules are comprehensive)
#         if score >= 70:
#             label = "Unsafe"
#         elif score >= 40:
#             label = "Moderate"
#         else:
#             label = "Safe"

#     # Use confidence from rules if provided
#     if rule_confidence:
#         confidence = rule_confidence
#     else:
#         confidence = calculate_confidence(score, reasons)

    

#     return {
#         "label": label,
#         "confidence": confidence,
#         "score": score,
#         "reasons": reasons,
#         "normalized_input": data
#     }




#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


#detector/rule_engine.py
from detector.rules import evaluate_rules
from detector.confidence import calculate_confidence
from detector.normalizer import normalize_input
import pickle
import joblib
import os
import numpy as np
import pandas as pd

# ============================================================================
# Load LightGBM model once at module load
# ============================================================================

_lgbm_model = None
_lgbm_features = None
_lgbm_encoder = None
_ml_available = False

def _load_ml_model():
    global _lgbm_model, _lgbm_features, _lgbm_encoder, _ml_available
    try:
        model_path = r"D:\ED\LGBM\detector_lgbm.pkl"
        features_path = r"D:\ED\LGBM\lgbm_features.pkl"
        encoder_path = r"D:\ED\LGBM\lgbm_label_encoder.pkl"
        
        if os.path.exists(model_path):
            _lgbm_model = joblib.load(model_path)
            _lgbm_features = joblib.load(features_path)
            _lgbm_encoder = joblib.load(encoder_path)
            _ml_available = True
            print("✅ LightGBM model loaded for detector")
        else:
            print("⚠️ LightGBM model not found, using rule-based only")
    except Exception as e:
        print(f"⚠️ Failed to load LightGBM model: {e}")

# Load at module import
_load_ml_model()

# ============================================================================
# Helper: Convert ED to risk level (matches training)
# ============================================================================

def ed_to_risk_level(ed_score):
    """Convert ED float to risk level (0-4) matching training data"""
    if ed_score >= 80:
        return 4  # Extreme Danger
    elif ed_score >= 65:
        return 3  # Dangerous
    elif ed_score >= 45:
        return 2  # Moderate Risk
    elif ed_score >= 30:
        return 1  # Moderate Safe
    else:
        return 0  # Safe

# ============================================================================
# Hard rules that always override ML
# ============================================================================

def check_hard_rules(data, ed_score):
    """
    Check non-negotiable safety rules from PDF.
    Returns (score, reasons, label, confidence) if triggered, else None.
    """
    health = data.get("HealthCondition", "Healthy")
    activity = data.get("ActivityType", "Mid Cardio")
    duration = data.get("DurationMins", 30)
    tod = data.get("TimeOfDay", "Morning")
    
    # Hard rule 1: ED >= 80 → Immediate Unsafe
    if ed_score >= 80:
        return 100, ["⚠️ EXTREME ENVIRONMENTAL RISK - Exercise dangerous"], "Unsafe", 1.0
    
    # Hard rule 2: Heart Condition + High Cardio → Unsafe
    if health == "Heart Condition" and activity == "High Cardio":
        return 100, ["Heart Condition: High Cardio unsafe (PDF rule 13)"], "Unsafe", 1.0
    
    # Hard rule 3: Asthma + Bad ED + Afternoon + outdoor cardio → Unsafe
    if ed_score >= 50 and health == "Asthma" and tod == "Afternoon" and activity in ["High Cardio", "Mid Cardio"]:
        return 100, ["Asthma + bad air + afternoon = unsafe outdoor cardio"], "Unsafe", 1.0
    
    # Hard rule 4: Diabetes + Bad ED + outdoor cardio → Unsafe
    if ed_score >= 50 and health == "Diabetes" and activity in ["High Cardio", "Mid Cardio"]:
        return 100, ["Diabetes + bad air quality = unsafe outdoor cardio"], "Unsafe", 1.0
    
    # Hard rule 5: Bad ED + Afternoon + High Cardio → Unsafe for all
    if ed_score >= 50 and tod == "Afternoon" and activity == "High Cardio":
        return 100, ["Bad ED + Afternoon + High Cardio = unsafe for all"], "Unsafe", 1.0
    
    # Hard rule 6: Duration > 120 minutes → Unsafe
    if duration > 120:
        return 100, ["Duration exceeds 120 minutes - unsafe for all"], "Unsafe", 1.0
    
    return None  # No hard rule triggered

# ============================================================================
# ML Prediction
# ============================================================================

def ml_predict(data, ed_score, ed_raw=None, risk_score=None):
    """
    Predict using trained LightGBM model.
    Returns (score, reasons, label, confidence) or None if ML unavailable.
    """
    if not _ml_available or _lgbm_model is None:
        return None
    
    try:
        # Build feature dictionary matching training
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
        
        # Convert to DataFrame and one-hot encode
        X = pd.DataFrame([features])
        categorical_cols = ['HealthCondition', 'FitnessLevel', 'ActivityType', 'TimeOfDay']
        X = pd.get_dummies(X, columns=categorical_cols)
        
        # Ensure all training columns are present
        for col in _lgbm_features:
            if col not in X.columns:
                X[col] = 0
        X = X[_lgbm_features]
        
        # Predict
        pred_label_encoded = _lgbm_model.predict(X)[0]
        pred_proba = _lgbm_model.predict_proba(X)[0]
        confidence = np.max(pred_proba)
        
        # Decode label
        label = _lgbm_encoder.inverse_transform([pred_label_encoded])[0]
        
        # Convert label to score
        score_map = {"Safe": 20, "Moderate": 50, "Unsafe": 80}
        score = score_map.get(label, 50)
        
        reasons = [f"ML prediction (confidence: {confidence:.2f})"]
        
        return score, reasons, label, confidence
        
    except Exception as e:
        print(f"⚠️ ML prediction failed: {e}")
        return None

# ============================================================================
# Main detector function (updated)
# ============================================================================

def rule_based_detector(input_data):
    """
    Hybrid detector: Hard Rules → LightGBM → Rule-based fallback
    
    Full pipeline:
    normalize → check hard rules → ML predict → rule fallback → confidence
    """
    
    data = normalize_input(input_data)
    ed_score = data.get("ED", 50)
    ed_raw = data.get("ED_raw", ed_score)
    risk_score = data.get("RiskScore", ed_score)
    
    # Debug: Print input
    print(f"🔍 DETECTOR INPUT: Health={data.get('HealthCondition')}, "
          f"Activity={data.get('ActivityType')}, Duration={data.get('DurationMins')}, "
          f"ED={ed_score:.1f}, TimeOfDay={data.get('TimeOfDay')}")
    
    # ============================================
    # STEP 1: HARD RULES (always override)
    # ============================================
    hard_result = check_hard_rules(data, ed_score)
    if hard_result is not None:
        score, reasons, label, confidence = hard_result
        print(f"📊 HARD RULE TRIGGERED: {label}")
        return {
            "label": label,
            "confidence": confidence,
            "score": score,
            "reasons": reasons,
            "normalized_input": data
        }
    
    # ============================================
    # STEP 2: LightGBM prediction (if available)
    # ============================================
    ml_result = ml_predict(data, ed_score, ed_raw, risk_score)
    
    if ml_result is not None:
        score, reasons, label, confidence = ml_result
        print(f"📊 ML PREDICTION: label={label}, confidence={confidence:.2f}, score={score}")
        
        # If ML confidence is high enough, use it
        if confidence > 0.70:
            print(f"   ✅ Using ML prediction (confidence > 0.70)")
            return {
                "label": label,
                "confidence": confidence,
                "score": score,
                "reasons": reasons,
                "normalized_input": data
            }
        else:
            print(f"   ⚠️ ML confidence too low ({confidence:.2f}), falling back to rules")
    
    # ============================================
    # STEP 3: Rule-based fallback
    # ============================================
    print(f"📋 Using rule-based evaluation (fallback)")
    
    # Get ALL 4 values from evaluate_rules
    score, reasons, rule_label, rule_confidence = evaluate_rules(data)
    
    print(f"📊 RULES OUTPUT: score={score}, label={rule_label}, confidence={rule_confidence}, reasons={reasons}")
    
    # Use the label from rules
    if rule_label:
        label = rule_label
    else:
        # Fallback classification (should not happen if rules are comprehensive)
        if score >= 70:
            label = "Unsafe"
        elif score >= 40:
            label = "Moderate"
        else:
            label = "Safe"
    
    # Use confidence from rules if provided
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