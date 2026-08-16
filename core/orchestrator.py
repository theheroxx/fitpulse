# core/orchestrator.py


import os
os.environ['CHROMA_TELEMETRY'] = 'False'
os.environ['ANONYMIZED_TELEMETRY'] = 'False'

from ed_calculator.math_model import ExerciseDangerPredictor
from detector import rule_based_detector
from database import get_exercises, get_foods
from transformer.recommender import generate_recommendation, generate_recommendation_with_rag



# RAG functions — use JSON search only (thread-safe from QThread)

def retrieve_context(query):
    """Thread-safe RAG retrieval using JSON files only (no ChromaDB on QThread)"""
    import json
    from pathlib import Path
    
    all_docs = []
    json_dir = Path("./data/chroma_db")
    
    for collection in ["medical", "exercises", "nutrition"]:
        json_file = json_dir / f"{collection}.json"
        if json_file.exists():
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                query_lower = query.lower()
                query_words = query_lower.split()
                
                for item in data:
                    doc = item.get('document', '')
                    doc_lower = doc.lower()
                    score = sum(1 for word in query_words if word in doc_lower)
                    if score > 0:
                        all_docs.append((score, doc))
            except Exception:
                pass
    
    all_docs.sort(key=lambda x: x[0], reverse=True)
    docs = [doc for score, doc in all_docs[:8]]
    
    return {"documents": [docs], "error": None}


def build_query(user_data, detector_output):
    """Build query string from user data and detector output"""
    parts = []
    
    health = user_data.get('HealthCondition', '')
    if health and health != 'Healthy':
        parts.append(f"Health condition: {health}")
    
    fitness = user_data.get('FitnessLevel', '')
    if fitness:
        parts.append(f"Fitness level: {fitness}")
    
    activity = user_data.get('ActivityType', '')
    if activity:
        parts.append(f"Activity: {activity}")
    
    label = detector_output.get('label', '')
    if label:
        parts.append(f"Risk level: {label}")
    
    reasons = detector_output.get('reasons', [])
    if reasons:
        parts.append(f"Risk factors: {', '.join(reasons[:2])}")
    
    return " | ".join(parts) if parts else "fitness exercise safety"


class PipelineCache:
    """Singleton cache for the ExerciseDangerPredictor model"""
    _model_instance = None
    
    @classmethod
    def get_ed_predictor(cls):
        if cls._model_instance is None:
            cls._model_instance = ExerciseDangerPredictor()
        return cls._model_instance


def calculate_simple_ed_score(PL, WD, sensitive):
    """Simple ED calculation (fallback)"""
    score = 0
    
    if PL > 150:
        score += 40
    elif PL > 100:
        score += 30
    elif PL > 50:
        score += 20
    elif PL > 25:
        score += 10
    
    if WD > 35 or WD < 0:
        score += 30
    elif WD > 30 or WD < 5:
        score += 20
    elif WD > 25 or WD < 10:
        score += 10
    
    if sensitive:
        score += 15
    
    return min(100, score)


def get_simple_recommendations(ed_score, PL, WD):
    """Get recommendations based on ED score"""
    recommendations = []
    
    if ed_score >= 70:
        recommendations.append("🚫 High risk! Avoid outdoor exercise today.")
        recommendations.append("🏠 Consider indoor alternatives like yoga or home workouts.")
    elif ed_score >= 50:
        recommendations.append("⚠️ Moderate risk. Limit outdoor exercise to 20-30 minutes.")
        recommendations.append("💧 Stay hydrated and take frequent breaks.")
    elif ed_score >= 30:
        recommendations.append("ℹ️ Acceptable conditions. Exercise with caution.")
        recommendations.append("👀 Monitor how you feel during activity.")
    else:
        recommendations.append("✅ Good conditions for outdoor exercise.")
    
    if PL > 100:
        recommendations.append("😷 Poor air quality. Consider wearing a mask if exercising outdoors.")
    if WD > 30:
        recommendations.append("🥵 High temperature! Exercise during cooler hours (morning/evening).")
    elif WD < 5:
        recommendations.append("🥶 Cold weather! Dress in layers and warm up properly.")
    
    return recommendations


# ============================================================================
# UNIT CONVERSION: µg/m³ → ppm
# ============================================================================

def ugm3_to_ppm(value: float, molecular_weight: float) -> float:
    """
    Convert concentration from µg/m³ to ppm at 25°C, 1 atm.
    Uses molar volume: 24.45 L/mol.
    ppm = (µg/m³ * 24.45) / (molecular_weight * 1000.0)
    """
    if value is None or value <= 0:
        return None
    return value * 24.45 / (molecular_weight * 1000.0)


# ============================================================================
# ED CALCULATION — FIXED with unit conversion for gases and safe AQI handling
# ============================================================================

def calculate_detailed_environmental_risk(weather_data, air_data):
    """
    Calculate environmental risk using the mathematical model.
    Converts gas pollutants from µg/m³ to ppm before passing to the model.
    Now with KNN cluster prediction.
    """
    try:
        from ed_calculator.math_model import ExerciseDangerMathModel
        from ed_calculator.pollution import (
            pm25_to_aqi, pm10_to_aqi, o3_to_aqi, no2_to_aqi,
            so2_to_aqi, co_to_aqi, aqi_to_epa_index
        )
        
        # Helper to safely add only valid (non‑None, non‑negative) AQI values
        def add_valid_aqi(container, name, value):
            if value is not None:
                try:
                    value = float(value)
                    if value >= 0:
                        container[name] = value
                except (TypeError, ValueError):
                    pass

        # Initialize model (singleton)
        if not hasattr(calculate_detailed_environmental_risk, '_model'):
            calculate_detailed_environmental_risk._model = ExerciseDangerMathModel()
        
        model = calculate_detailed_environmental_risk._model
        
        # ─── Extract weather ──────────────────────────────────────────
        temp = weather_data.get('temp', 22.0)
        humidity = weather_data.get('humid', 45.0)
        wind = weather_data.get('wind', 10.0)
        uv = weather_data.get('uv', 3.0)
        
        # ─── Extract pollutants (all in µg/m³ from UI) ──────────────
        pm25 = air_data.get('pm25', 10.0)
        pm10 = air_data.get('pm10', 0.0)
        o3_ug = air_data.get('o3', 0.0)
        no2_ug = air_data.get('no2', 0.0)
        so2_ug = air_data.get('so2', 0.0)
        co_ug = air_data.get('co', 0.0)
        
        # ─── Convert gases: µg/m³ → ppm ──────────────────────────────
        o3_ppm = ugm3_to_ppm(o3_ug, 48.0)
        no2_ppm = ugm3_to_ppm(no2_ug, 46.0)
        so2_ppm = ugm3_to_ppm(so2_ug, 64.07)
        co_ppm = ugm3_to_ppm(co_ug, 28.01)
        
        # ─── Compute EPA index from all pollutants ────────────────────
        aqi_values = {}
        
        if pm25 > 0:
            add_valid_aqi(aqi_values, "PM2.5", pm25_to_aqi(pm25))
        if pm10 > 0:
            add_valid_aqi(aqi_values, "PM10", pm10_to_aqi(pm10))
        if o3_ppm is not None and o3_ppm > 0:
            add_valid_aqi(aqi_values, "O3", o3_to_aqi(o3_ppm))
        if no2_ppm is not None and no2_ppm > 0:
            add_valid_aqi(aqi_values, "NO2", no2_to_aqi(no2_ppm))
        if so2_ppm is not None and so2_ppm > 0:
            add_valid_aqi(aqi_values, "SO2", so2_to_aqi(so2_ppm))
        if co_ppm is not None and co_ppm > 0:
            add_valid_aqi(aqi_values, "CO", co_to_aqi(co_ppm))
        
        valid_aqi_values = [v for v in aqi_values.values() if v is not None]
        epa_index = aqi_to_epa_index(max(valid_aqi_values)) if valid_aqi_values else 1
        
        # KNN Cluster Prediction 
        cluster_id = None
        knn_cluster_used = False
        try:
            from ed_calculator.knn_cluster_matcher import predict_cluster
            cluster_id = predict_cluster(
                temp=temp,
                pm25=pm25 if pm25 > 0 else 0.0
            )
            knn_cluster_used = True
            print(f"   🔮 KNN predicted cluster: {cluster_id}")
        except Exception as e:
            print(f"   ⚠️ KNN prediction failed: {e}")
            cluster_id = None
        
        # ─── Call the model with converted units + KNN cluster ──────
        result = model.predict(
            temperature_celsius=temp,
            humidity=humidity,
            wind_kph=wind,
            uv_index=uv,
            air_quality_us_epa_index=epa_index,
            air_quality_PM2_5=pm25 if pm25 > 0 else None,
            air_quality_PM10=pm10 if pm10 > 0 else None,
            air_quality_Ozone=o3_ppm if o3_ppm is not None and o3_ppm > 0 else None,
            air_quality_Nitrogen_dioxide=no2_ppm if no2_ppm is not None and no2_ppm > 0 else None,
            air_quality_Sulphur_dioxide=so2_ppm if so2_ppm is not None and so2_ppm > 0 else None,
            air_quality_Carbon_Monoxide=co_ppm if co_ppm is not None and co_ppm > 0 else None,
            cluster_id=cluster_id,  # ← KNN predicted cluster
            anomaly_flag=False,
            use_knn=False,  # ← cluster قبلاً با KNN گرفته شده
        )
        
        return {
            'FINAL_SCORE': result['ED'],
            'STATUS': result['Risk_Level'].upper(),
            'RANGE': result['confidence_range'],
            'BIAS': f"{result['regional_adjustment']:+.1f}",
            'DETAILS': result,
            'KNN_CLUSTER': cluster_id,  # ← جدید
            'KNN_CLUSTER_USED': knn_cluster_used,  # ← جدید
        }
        
    except Exception as e:
        print(f"ERROR in calculate_detailed_environmental_risk: {e}")
        import traceback
        traceback.print_exc()
        return {
            'FINAL_SCORE': 50,
            'STATUS': 'MODERATE',
            'RANGE': '0-100',
            'BIAS': '+0.0',
            'DETAILS': None,
            'KNN_CLUSTER': None,
            'KNN_CLUSTER_USED': False,
        }


def get_risk_recommendation(risk_score):
    """Get recommendation based on risk score"""
    if risk_score >= 80:
        return "🚫 No outdoor exercise - Conditions are dangerous. Stay indoors.", "danger"
    elif risk_score >= 65:
        return "⚠️ High risk - Very limited outdoor activity only. Keep it under 15 minutes.", "high"
    elif risk_score >= 45:
        return "⚠️ Moderate risk - Light exercise only. Limit to 20-30 minutes.", "moderate"
    elif risk_score >= 30:
        return "ℹ️ Moderate safe - Exercise with caution. Take breaks as needed.", "caution"
    else:
        return "✅ Fully safe - Good conditions for outdoor exercise.", "safe"


# MAIN PIPELINE — ALWAYS CALLS THE LLM

def run_pipeline(user_input):
    """Full system pipeline — LLM is ALWAYS called for the final recommendation."""
    user_data = user_input.copy()

    # 1) ED Calculation
    if "ED" not in user_data:
        weather_data = {
            "temp": user_data.get("Temperature", user_data.get("temp", user_data.get("WD", 22))),
            "humid": user_data.get("Humidity", user_data.get("humid", 45)),
            "wind": user_data.get("Wind", user_data.get("wind", 10)),
            "uv": user_data.get("UV", user_data.get("uv", 3))
        }
        
        air_data = {
            "pm25": user_data.get("PM25", user_data.get("pm25", user_data.get("PL", 25))),
            "pm10": user_data.get("PM10", user_data.get("pm10", 45)),
            "co": user_data.get("CO", user_data.get("co", 200)),
            "o3": user_data.get("O3", user_data.get("o3", 40)),
            "no2": user_data.get("NO2", user_data.get("no2", 10)),
            "so2": user_data.get("SO2", user_data.get("so2", 5))
        }
        
        try:
            detailed_result = calculate_detailed_environmental_risk(weather_data, air_data)
            ed = detailed_result["FINAL_SCORE"]
            user_data["ED"] = ed
            user_data["detailed_risk"] = detailed_result

            # ─── KNN cluster info 
            if detailed_result.get("KNN_CLUSTER") is not None:
                user_data["cluster_id"] = detailed_result["KNN_CLUSTER"]
                print(f"Cluster: {detailed_result['KNN_CLUSTER']} (via KNN)")
        except Exception as e:
            print(f"Math model error, using fallback: {e}")
            PL = user_data.get("PL", user_data.get("PM25", 50))
            WD = user_data.get("WD", user_data.get("Temperature", 22))
            sensitive = user_data.get("sensitive", False)
            ed = calculate_simple_ed_score(PL, WD, sensitive)
            user_data["ED"] = ed
            detailed_result = None
    else:
        ed = user_data["ED"]
        detailed_result = None

    PL = user_data.get("PL", user_data.get("PM25", 50))
    WD = user_data.get("WD", user_data.get("Temperature", 22))
    ed_recommendations = get_simple_recommendations(ed, PL, WD)

    # 2) Detector (Rules + ML)
    detector_output = rule_based_detector(user_data)

    # 3) Exercise/Food Recommendations
    # ------------------------------
    user_profile = {
        "health_condition": user_data.get("HealthCondition", "Healthy"),
        "fitness_level": user_data.get("FitnessLevel", "Medium")
    }
    
    try:
        exercise_recommendations = get_exercises(user_profile, detector_output.get("label", "Safe"))
        food_recommendations = get_foods(user_profile)
    except Exception as e:
        print(f"Database error: {e}")
        exercise_recommendations = ["Walking", "Yoga", "Stretching"]
        food_recommendations = ["Oatmeal", "Chicken Breast", "Broccoli"]
    
    if exercise_recommendations:
        ed_recommendations.append("\n🏋️ Recommended Exercises:")
        ed_recommendations.extend([f"  • {ex}" for ex in exercise_recommendations[:5]])
    
    if food_recommendations:
        ed_recommendations.append("\n🥗 Recommended Foods:")
        ed_recommendations.extend([f"  • {food}" for food in food_recommendations[:5]])



    # 4) RAG Context (thread-safe JSON search)
    # 
    query = build_query(user_data, detector_output)
    rag_context = ""
    try:
        context_result = retrieve_context(query)
        docs = context_result.get('documents', [[]])[0] if context_result.get('documents') else []
        if docs:
            rag_context = "\n\n".join(docs[:5])
    except Exception as e:
        print(f"RAG retrieval error: {e}")

    # 
    # 5) LLM Recommendation — ALWAYS CALLED
    # 
    final_recommendation = ""
    
    try:
        # ALWAYS call the LLM — regardless of detector confidence
        print("🤖 Orchestrator: Calling LLM for final recommendation...")
        
        # Get ED score safely
        ed_score = user_data.get("ED", 0)
        
        # Ensure detector_output has all needed fields
        if "label" not in detector_output:
            detector_output["label"] = "Safe"
        if "confidence" not in detector_output:
            detector_output["confidence"] = 0.8
            
        # Call LLM with full context
        if rag_context and len(rag_context) > 50:
            final_recommendation = generate_recommendation_with_rag(
                user_data, 
                detector_output, 
                query=query,
                rag_context=rag_context
            )
        else:
            final_recommendation = generate_recommendation(user_data, detector_output, query=query)
            
        print(f"🤖 Orchestrator: LLM response received ({len(final_recommendation)} chars)")
        
    except Exception as e:
        print(f" LLM generation error: {e}")
        # Fallback to a human-friendly message based on the detector label
        label = detector_output.get('label', 'Safe')
        if label == 'Safe':
            final_recommendation = "✅ Great conditions! Enjoy your workout today. Stay hydrated and listen to your body."
        elif label == 'Moderate':
            final_recommendation = "💡 Moderate risk. Take it a bit easier, use extra breaks, and stay aware of how you feel."
        elif label == 'High':
            final_recommendation = "🔶 High risk. Consider reducing intensity, taking more breaks, or moving indoors."
        else:
            final_recommendation = "⚠️ Unsafe conditions. Avoid outdoor exercise today. Choose an indoor activity instead."

    # =========================================================
    # 6) Return Results
    # =========================================================
    return {
        "ED": ed,
        "detector": detector_output,
        "ed_recommendations": ed_recommendations,
        "exercise_recommendations": exercise_recommendations,
        "food_recommendations": food_recommendations,
        "rag_context": context_result if 'context_result' in locals() else {"documents": []},
        "final_recommendation": final_recommendation,
        "detailed_risk": detailed_result
    }