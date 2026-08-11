# ui/desktop/workers/analysis_worker.py
from PySide6.QtCore import QThread, Signal
import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from core.orchestrator import run_pipeline
from ed_calculator.math_model import ExerciseDangerMathModel

# Singleton pattern for ED model (used only for fallback, not for main calculation)
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

            # STEP 1: Extract and validate data (no ED calculation here)
            weather_data, air_data = self._extract_environmental_data()
            self.progress.emit("Environmental data extracted")

            # STEP 2: Prepare pipeline data WITHOUT pre‑calculated ED
            # Let the orchestrator calculate ED using the new model
            pipeline_data = self._prepare_pipeline_data(weather_data, air_data)
            self.progress.emit("Preparing comprehensive analysis...")

            # STEP 3: Run orchestrator pipeline (this now calculates ED correctly)
            result = self._run_orchestrator(pipeline_data)
            self.progress.emit("Analysis complete")

            # STEP 4: Finalize and emit
            final_result = self._finalize_result(result, weather_data, air_data)
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
    
    def _prepare_pipeline_data(self, weather_data, air_data):
        """
        Prepare data for orchestrator pipeline.
        DO NOT calculate ED here – let the orchestrator handle it.
        """
        sensitive = self.user_data.get("sensitive", False)
        
        pipeline_data = {
            # User profile
            "Age": self._clamp_value(self.user_data.get("Age", 30), 0, 120),
            "HealthCondition": self.user_data.get("HealthCondition", "Healthy"),
            "FitnessLevel": self.user_data.get("FitnessLevel", "Medium"),
            "ActivityType": self.user_data.get("ActivityType", "Mid Cardio"),
            "DurationMins": self._clamp_value(self.user_data.get("DurationMins", 30), 1, 480),
            "TimeOfDay": self.user_data.get("TimeOfDay", "Morning"),
            
            # Environmental (raw data – orchestrator will compute ED)
            "Temperature": weather_data["temp"],
            "Humidity": weather_data["humid"],
            "Wind": weather_data["wind"],
            "UV": weather_data["uv"],
            "PM25": air_data["pm25"],
            "PM10": air_data["pm10"],
            "CO": air_data["co"],
            "O3": air_data["o3"],
            "NO2": air_data["no2"],
            "SO2": air_data["so2"],
            
            # Sensitive flag (orchestrator handles this)
            "sensitive": sensitive,
            "sensitive_population": sensitive,
            
            # ❌ REMOVED: "ED" – let orchestrator calculate
            # ❌ REMOVED: "PL" – use PM25 instead
            # ❌ REMOVED: "WD" – use Temperature instead
        }
        
        return pipeline_data
    
    def _run_orchestrator(self, pipeline_data):
        """Run the orchestrator pipeline with fallback"""
        try:
            print(f"\n{'='*60}")
            print(f"🔍 DEBUG: Calling run_pipeline (orchestrator will calculate ED)")
            
            result = run_pipeline(pipeline_data)
            
            print(f"\n🔍 DEBUG: run_pipeline returned:")
            print(f"   - result keys: {list(result.keys())}")
            print(f"   - ED: {result.get('ED', 'MISSING')}")
            
            # Check if detector exists in result
            if 'detector' not in result:
                print(f"   ⚠️ WARNING: No 'detector' key in result! Creating one.")
                result['detector'] = {}
            
            print(f"   - detector label: {result['detector'].get('label', 'MISSING')}")
            print(f"   - detector score: {result['detector'].get('score', 'MISSING')}")
            print(f"   - final_recommendation: {result.get('final_recommendation', 'N/A')[:100]}")
            
            # ─── Safety override: if ED is extreme, ensure detector reflects it ───
            ed_score = result.get('ED', 50)
            
            if ed_score >= 70 and result['detector'].get('label') not in ['Unsafe', 'Dangerous', 'Extreme']:
                print(f"\n⚠️⚠️⚠️ EXTREME ED ({ed_score:.1f}) – overriding detector label")
                result['detector'] = {
                    "label": "Unsafe",
                    "confidence": 0.95,
                    "score": ed_score,
                    "reasons": [f"EXTREME ENVIRONMENTAL RISK (ED={ed_score:.1f})", 
                                "Avoid outdoor exercise today"]
                }
                result['final_recommendation'] = f"🚨 EXTREME RISK (ED={ed_score:.1f}) – Environment is hazardous for exercise. Move indoors or reschedule."
            
            elif ed_score >= 60 and result['detector'].get('label') == 'Safe':
                print(f"\n⚠️ ED ({ed_score:.1f}) but detector says 'Safe' – updating")
                result['detector']['label'] = 'Moderate'
                result['detector']['score'] = ed_score
                result['detector']['confidence'] = 0.85
            
            print(f"\n✅ FINAL RESULT AFTER FIXES:")
            print(f"   Detector label: {result['detector']['label']}")
            print(f"   Detector score: {result['detector']['score']}")
            print(f"   ED from orchestrator: {ed_score:.1f}")
            
            return result
            
        except Exception as e:
            print(f"❌ Error in _run_orchestrator: {e}")
            traceback.print_exc()
            
            # Ultimate fallback – use ED from orchestrator if available
            ed_fallback = result.get('ED', 50) if 'result' in locals() else 50
            
            fallback_result = {
                "ED": ed_fallback,
                "detector": {
                    "label": "Unsafe" if ed_fallback >= 60 else "Moderate" if ed_fallback >= 40 else "Safe",
                    "confidence": 0.9,
                    "score": ed_fallback,
                    "reasons": [f"Environmental risk score: {ed_fallback:.1f}/100"]
                },
                "ed_recommendations": self._generate_recommendations(ed_fallback),
                "final_recommendation": self._generate_final_recommendation(ed_fallback),
                "rag_context": {},
                "detailed_risk": result.get('detailed_risk') if 'result' in locals() else None
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
    
    def _generate_recommendations(self, ed_score):
        """Generate recommendations based on ED score"""
        recommendations = []
        
        if ed_score >= 80:
            recommendations.append("🚫 Avoid outdoor exercise today")
            recommendations.append("Choose indoor activities instead")
            recommendations.append("Stay in air-conditioned environment")
        elif ed_score >= 60:
            recommendations.append("⚠️ Reduce exercise intensity and duration")
            recommendations.append("Take frequent breaks in shade")
            recommendations.append("Stay well hydrated")
        elif ed_score >= 40:
            recommendations.append("Exercise with caution")
            recommendations.append("Monitor how you feel")
            recommendations.append("Consider early morning or evening exercise")
        else:
            recommendations = ["Good conditions for exercise", "Listen to your body"]
        
        return recommendations
    
    def _generate_final_recommendation(self, ed_score):
        """Generate final summary recommendation"""
        if ed_score < 40:
            return f"Risk score: {ed_score:.1f}/100 (Safe). Good conditions for exercise. Proceed as planned."
        elif ed_score < 60:
            return f"Risk score: {ed_score:.1f}/100 (Moderate). Take basic precautions and monitor how you feel."
        elif ed_score < 80:
            return f"Risk score: {ed_score:.1f}/100 (Unsafe). Strongly consider modifying or rescheduling exercise."
        else:
            return f"Risk score: {ed_score:.1f}/100 (Extreme). Avoid outdoor exercise today."
    
    def _finalize_result(self, result, weather_data, air_data):
        """Add metadata and ensure all required fields"""
        # The orchestrator now returns the correct ED in result['ED']
        ed_score = result.get('ED', 50)
        
        # Add environmental data
        result["weather"] = weather_data
        result["air_quality"] = air_data
        result["user_data"] = self.user_data
        
        # Add simplified recommendation for backward compatibility
        if "ed_recommendations" not in result or not result["ed_recommendations"]:
            result["ed_recommendations"] = self._generate_recommendations(ed_score)
        
        if "final_recommendation" not in result or not result["final_recommendation"]:
            result["final_recommendation"] = self._generate_final_recommendation(ed_score)
        
        # Ensure detector exists
        if "detector" not in result:
            result["detector"] = {
                "label": self._get_safety_label(ed_score),
                "confidence": 0.85,
                "score": ed_score,
                "reasons": ["Environmental risk assessment"]
            }
        
        # Ensure detailed_risk exists
        if "detailed_risk" not in result:
            result["detailed_risk"] = {
                "FINAL_SCORE": ed_score,
                "STATUS": self._get_safety_label(ed_score).upper(),
                "RANGE": "0-100",
                "BIAS": "+0.0"
            }
        
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