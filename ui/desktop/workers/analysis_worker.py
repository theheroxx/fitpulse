# ui/desktop/workers/analysis_worker.py
from PySide6.QtCore import QThread, Signal
import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from core.orchestrator import run_pipeline
from ed_calculator.ed_engine import ExerciseDangerMathModel

# Singleton pattern for ED model
_ED_MODEL = None

def get_ed_model():
    global _ED_MODEL
    if _ED_MODEL is None:
        _ED_MODEL = ExerciseDangerMathModel()
    return _ED_MODEL


class AnalysisWorker(QThread):
    analysis_started = Signal()
    analysis_finished = Signal(dict)
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        self.ed_model = get_ed_model()

    def run(self):
        try:
            self.progress.emit("Starting analysis...")
            
            # STEP 1: Extract and validate data
            weather_data, air_data = self._extract_environmental_data()
            self.progress.emit("Environmental data extracted")
            
            # STEP 2: Calculate ED score using mathematical model
            ed_result = self._calculate_ed_score(weather_data, air_data)
            self.progress.emit(f"Risk assessment: {ed_result['risk_level']}")
            
            # STEP 3: Prepare pipeline data
            pipeline_data = self._prepare_pipeline_data(weather_data, air_data, ed_result)
            self.progress.emit("Preparing comprehensive analysis...")
            
            # STEP 4: Run orchestrator pipeline
            result = self._run_orchestrator(pipeline_data, ed_result)
            self.progress.emit("Analysis complete")
            
            # STEP 5: Finalize and emit
            final_result = self._finalize_result(result, weather_data, air_data, ed_result)
            self.analysis_finished.emit(final_result)
            
        except Exception as e:
            self._handle_error(e)

    def _extract_environmental_data(self):
        """Extract weather and air quality data with validation"""
        # Weather data with bounds checking
        weather_data = {
            "temp": self._clamp_value(
                self.user_data.get("temp", self.user_data.get("Temperature", 22)),
                -30, 50
            ),
            "humid": self._clamp_value(
                self.user_data.get("humid", self.user_data.get("Humidity", 45)),
                0, 100
            ),
            "wind": max(0, self.user_data.get("wind", self.user_data.get("Wind", 10))),
            "uv": self._clamp_value(
                self.user_data.get("uv", self.user_data.get("UV", 3)),
                0, 15
            )
        }
        
        # Air quality data with bounds
        air_data = {
            "pm25": self._clamp_value(
                self.user_data.get("pm25", self.user_data.get("PM25", 25)),
                0, 500
            ),
            "pm10": self._clamp_value(
                self.user_data.get("pm10", self.user_data.get("PM10", 45)),
                0, 600
            ),
            "co": max(0, self.user_data.get("co", self.user_data.get("CO", 200))),
            "o3": max(0, self.user_data.get("o3", self.user_data.get("O3", 40))),
            "no2": max(0, self.user_data.get("no2", self.user_data.get("NO2", 10))),
            "so2": max(0, self.user_data.get("so2", self.user_data.get("SO2", 5)))
        }
        
        return weather_data, air_data
    
    def _clamp_value(self, value, min_val, max_val):
        """Safely clamp a value within bounds"""
        try:
            return max(min_val, min(max_val, float(value)))
        except (TypeError, ValueError):
            return (min_val + max_val) / 2
    
    def _calculate_ed_score(self, weather_data, air_data):
        """Calculate Exercise Danger score using mathematical model"""
        sensitive = self.user_data.get("sensitive", False)
        
        # Get PM2.5 for PL parameter
        pl_value = air_data["pm25"]
        
        # Get temperature for WD parameter
        wd_value = weather_data["temp"]
        
        # Call the mathematical model
        ed_result = self.ed_model.calculate_danger_score(
            PL=pl_value,
            WD=wd_value,
            sensitive_population=sensitive
        )
        
        # Apply additional adjustments based on other factors
        ed_score = ed_result["ED"]
        
        # Adjust for humidity (high humidity makes heat worse)
        if weather_data["humid"] > 80 and weather_data["temp"] > 25:
            humidity_penalty = min(15, (weather_data["humid"] - 80) * 0.5)
            ed_score = min(100, ed_score + humidity_penalty)
            ed_result["dominant_factors"].append("High Humidity")
        
        # Adjust for UV index
        if weather_data["uv"] > 8:
            uv_penalty = min(10, (weather_data["uv"] - 8) * 2)
            ed_score = min(100, ed_score + uv_penalty)
            ed_result["dominant_factors"].append("Extreme UV")
        
        # Adjust for sensitive population
        if sensitive:
            ed_score = min(100, ed_score + 15)
            if "Sensitive Population" not in ed_result["dominant_factors"]:
                ed_result["dominant_factors"].append("Sensitive Population")
        
        ed_result["ED"] = round(ed_score, 2)
        
        # Recalculate risk level based on adjusted score
        if ed_score < 20:
            ed_result["risk_level"] = "Very Low"
        elif ed_score < 40:
            ed_result["risk_level"] = "Low"
        elif ed_score < 60:
            ed_result["risk_level"] = "Moderate"
        elif ed_score < 80:
            ed_result["risk_level"] = "High"
        else:
            ed_result["risk_level"] = "Extreme"
        
        return ed_result
    
    def _prepare_pipeline_data(self, weather_data, air_data, ed_result):
        """Prepare data for orchestrator pipeline"""
        sensitive = self.user_data.get("sensitive", False)
        
        pipeline_data = {
            # User profile
            "Age": self._clamp_value(self.user_data.get("Age", 30), 0, 120),
            "HealthCondition": self.user_data.get("HealthCondition", "Healthy"),
            "FitnessLevel": self.user_data.get("FitnessLevel", "Medium"),
            "ActivityType": self.user_data.get("ActivityType", "Mid Cardio"),
            "DurationMins": self._clamp_value(self.user_data.get("DurationMins", 30), 1, 480),
            "TimeOfDay": self.user_data.get("TimeOfDay", "Morning"),
            
            # Environmental (for ED model)
            "PL": air_data["pm25"],  # PM2.5 for pollution
            "WD": weather_data["temp"],  # Temperature
            
            # Sensitive flag
            "sensitive": sensitive,
            
            # ED score from mathematical model
            "ED": ed_result["ED"],
            
            # Detailed environmental data
            "Temperature": weather_data["temp"],
            "Humidity": weather_data["humid"],
            "Wind": weather_data["wind"],
            "UV": weather_data["uv"],
            "PM25": air_data["pm25"],
            "PM10": air_data["pm10"],
            "CO": air_data["co"],
            "O3": air_data["o3"],
            "NO2": air_data["no2"],
            "SO2": air_data["so2"]
        }
        
        return pipeline_data
    
    def _run_orchestrator(self, pipeline_data, ed_result):
        """Run the orchestrator pipeline with fallback"""
        try:
            print(f"\n{'='*60}")
            print(f"🔍 DEBUG: Calling run_pipeline with ED={pipeline_data.get('ED')}")
            
            result = run_pipeline(pipeline_data)
            
            print(f"\n🔍 DEBUG: run_pipeline returned:")
            print(f"   - result keys: {list(result.keys())}")
            
            # Check if detector exists in result
            if 'detector' not in result:
                print(f"   ⚠️ WARNING: No 'detector' key in result! Creating one.")
                result['detector'] = {}
            
            print(f"   - detector label: {result['detector'].get('label', 'MISSING')}")
            print(f"   - detector score: {result['detector'].get('score', 'MISSING')}")
            print(f"   - final_recommendation: {result.get('final_recommendation', 'N/A')[:100]}")
            
            # CRITICAL FIX: Check if ED is extreme and override if needed
            ed_score = ed_result['ED']
            
            # Case 1: Missing detector or invalid label
            if result['detector'].get('label') in [None, 'MISSING', 'Safe'] and ed_score >= 70:
                print(f"\n⚠️⚠️⚠️ CRITICAL BUG: ED={ed_score:.1f} but detector label is '{result['detector'].get('label')}'")
                print(f"   Overriding with correct UNSAFE label!")
                
                # Force correct values
                result['detector'] = {
                    "label": "Unsafe",
                    "confidence": 0.95,
                    "score": ed_score,
                    "reasons": [f"EXTREME ENVIRONMENTAL RISK (ED={ed_score:.1f})", 
                            f"Risk Level: {ed_result.get('risk_level', 'Extreme')}",
                            "Avoid outdoor exercise today"]
                }
                result['final_recommendation'] = f"⚠️ EXTREME RISK (ED={ed_score:.1f}) - Environment is hazardous for exercise. Move indoors or reschedule."
                result['risk_status'] = ed_result.get('risk_level', 'Extreme')
                
            # Case 2: Detector exists but score is too low compared to ED
            elif result['detector'].get('score', 0) < ed_score - 20 and ed_score >= 70:
                print(f"\n⚠️ WARNING: Detector score ({result['detector'].get('score')}) much lower than ED ({ed_score:.1f})")
                print(f"   Updating detector with correct values")
                
                result['detector']['label'] = "Unsafe"
                result['detector']['score'] = ed_score
                result['detector']['confidence'] = max(result['detector'].get('confidence', 0.8), 0.9)
                if 'reasons' not in result['detector']:
                    result['detector']['reasons'] = []
                result['detector']['reasons'].insert(0, f"⚠️ Environmental risk override (ED={ed_score:.1f})")
                result['final_recommendation'] = f"⚠️ HIGH ENVIRONMENTAL RISK (ED={ed_score:.1f}) - Exercise with extreme caution or reschedule"
            
            # Case 3: Everything seems correct but double-check extreme case
            elif ed_score >= 80 and result['detector'].get('label') != 'Unsafe':
                print(f"\n⚠️ EXTREME ED ({ed_score:.1f}) but detector says '{result['detector'].get('label')}' - FORCING UNSAFE")
                result['detector']['label'] = 'Unsafe'
                result['detector']['score'] = ed_score
                result['detector']['confidence'] = 0.99
                if 'reasons' not in result['detector']:
                    result['detector']['reasons'] = []
                result['detector']['reasons'].insert(0, f"🚨 EXTREME ENVIRONMENTAL HAZARD (ED={ed_score:.1f})")
                result['final_recommendation'] = "🚨 EXTREME RISK - DO NOT EXERCISE OUTDOORS TODAY"
            
            # Final verification print
            print(f"\n✅ FINAL RESULT AFTER FIXES:")
            print(f"   Detector label: {result['detector']['label']}")
            print(f"   Detector score: {result['detector']['score']}")
            print(f"   ED from model: {ed_score:.1f}")
            
            return result
            
        except Exception as e:
            print(f"❌ Error in _run_orchestrator: {e}")
            traceback.print_exc()
            
            # Ultimate fallback - use ED score directly
            fallback_result = {
                "ED": ed_result['ED'],
                "detector": {
                    "label": "Unsafe" if ed_result['ED'] >= 60 else "Moderate" if ed_result['ED'] >= 40 else "Safe",
                    "confidence": 0.9,
                    "score": ed_result['ED'],
                    "reasons": [f"Environmental risk score: {ed_result['ED']:.1f}/100",
                            f"Risk level: {ed_result.get('risk_level', 'Unknown')}",
                            "Based on temperature and air quality data"]
                },
                "ed_recommendations": self._generate_recommendations(ed_result),
                "final_recommendation": self._generate_final_recommendation(ed_result),
                "rag_context": {},
                "detailed_risk": ed_result
            }
            return fallback_result
    
    def _get_safety_label(self, ed_score):
        """Convert ED score to safety label"""
        if ed_score < 40:
            return "Safe"
        elif ed_score < 60:
            return "Moderate"
        elif ed_score < 80:
            return "Unsafe"
        else:
            return "Dangerous"
    
    def _generate_recommendations(self, ed_result):
        """Generate recommendations based on ED result"""
        recommendations = []
        
        if ed_result["risk_level"] in ["High", "Extreme"]:
            recommendations.append("Consider moving exercise indoors")
            recommendations.append("Reschedule outdoor activities")
        
        if "Temperature Stress" in ed_result["dominant_factors"]:
            recommendations.append("Take more frequent breaks in shade")
            recommendations.append("Stay well hydrated")
        
        if "Air Pollution" in ed_result["dominant_factors"]:
            recommendations.append("Wear N95 mask if exercising outdoors")
            recommendations.append("Choose less intense activities")
        
        if "Combined Environmental Stress" in ed_result["dominant_factors"]:
            recommendations.append("Reduce exercise duration and intensity")
        
        if not recommendations:
            recommendations = ["Good conditions for exercise", "Listen to your body"]
        
        return recommendations
    
    def _generate_final_recommendation(self, ed_result):
        """Generate final summary recommendation"""
        score = ed_result["ED"]
        level = ed_result["risk_level"]
        
        if score < 40:
            return f"Risk score: {score:.1f}/100 ({level}). Good conditions for exercise. Proceed as planned."
        elif score < 60:
            return f"Risk score: {score:.1f}/100 ({level}). Moderate risk. Take basic precautions and monitor how you feel."
        elif score < 80:
            return f"Risk score: {score:.1f}/100 ({level}). Significant risk. Strongly consider modifying or rescheduling exercise."
        else:
            return f"Risk score: {score:.1f}/100 ({level}). Extreme risk. Avoid outdoor exercise today."
    
    def _finalize_result(self, result, weather_data, air_data, ed_result):
        """Add metadata and ensure all required fields"""
        # Add mathematical model details
        result["ed_math_model"] = {
            "score": ed_result["ED"],
            "risk_level": ed_result["risk_level"],
            "temperature_score": ed_result["temperature_score"],
            "pollution_score": ed_result["pollution_score"],
            "interaction_score": ed_result["interaction_score"],
            "dominant_factors": ed_result["dominant_factors"]
        }
        
        # Add environmental data
        result["weather"] = weather_data
        result["air_quality"] = air_data
        
        # Add user data for reference
        result["user_data"] = self.user_data
        
        # Ensure required fields exist
        if "detector" not in result:
            result["detector"] = {
                "label": self._get_safety_label(ed_result["ED"]),
                "confidence": 0.85,
                "score": ed_result["ED"],
                "reasons": ed_result["dominant_factors"]
            }
        
        if "ed_recommendations" not in result:
            result["ed_recommendations"] = self._generate_recommendations(ed_result)
        
        if "final_recommendation" not in result:
            result["final_recommendation"] = self._generate_final_recommendation(ed_result)
        
        return result
    
    def _handle_error(self, error):
        """Handle errors gracefully"""
        error_msg = f"Worker error: {str(error)}"
        print("=" * 70)
        print(f"❌ {error_msg}")
        traceback.print_exc()
        print("=" * 70)
        
        fallback_result = {
            "ED": 50,
            "detector": {
                "label": "Moderate", 
                "confidence": 0.7, 
                "score": 50, 
                "reasons": ["Analysis error occurred"]
            },
            "ed_recommendations": ["Please try again", "Check your input values"],
            "final_recommendation": "Analysis encountered an error. Please check your inputs and try again.",
            "rag_context": {},
            "detailed_risk": None,
            "error": error_msg
        }
        
        self.analysis_finished.emit(fallback_result)