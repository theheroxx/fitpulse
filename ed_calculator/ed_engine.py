# ed_calculator/ed_engine.py
# ============================================================================
# PHASE 2: MATHEMATICAL MODEL (CORE BRAIN) - FINAL BALANCED VERSION
# - Realistic pollution weighting (70% pollution, 30% temperature)
# - Multi‑pollutant synergy (1.1x when >1 pollutant >45)
# - Wind, UV, humidity modifiers
# - Heat‑pollution synergy (1.15x when T>28°C and pollution>40)
# ============================================================================

import pandas as pd
import numpy as np
import os
import warnings
from typing import Dict, Optional

warnings.filterwarnings("ignore")


class ExerciseDangerMathModel:

    def __init__(
        self,
        mining_dir: Optional[str] = None,
        anomaly_dir: Optional[str] = None
    ):
        if mining_dir is None:
            mining_dir = r"D:\Data mining\data mining\2- Decision Tree Analysis\decision_tree_results"
        if anomaly_dir is None:
            anomaly_dir = r"D:\Data mining\data mining\5- Anomaly Detection\anomaly_results"

        self.params = self._load_parameters(mining_dir, anomaly_dir)

        print("🧠 Exercise Danger Model Ready (Final Balanced Version)")
        print(f"   • Temperature Danger Threshold: {self.params['temp_danger']}°C")
        print(f"   • PM2.5 Danger Threshold: {self.params['pm25_danger']} µg/m³")
        print(f"   • Weights: Temp {self.params['w_temp']*100:.0f}% / Pollution {self.params['w_pollution']*100:.0f}%")
        print(f"   • Multi-pollutant synergy: ENABLED")
        print(f"   • Wind/UV modifiers: ENABLED")

    # =========================================================================
    # LOAD PARAMETERS
    # =========================================================================

    def _load_parameters(self, mining_dir: str, anomaly_dir: str) -> Dict:
        params = {
            # Temperature thresholds
            "temp_safe": 10.0,
            "temp_caution": 24.0,
            "temp_danger": 30.0,

            # Pollution danger thresholds (WHO + document)
            "pm25_danger": 55.0,
            "pm10_danger": 150.0,
            "co_danger": 1500.0,
            "o3_danger": 120.0,
            "no2_danger": 200.0,
            "so2_danger": 300.0,

            # Sigmoid steepness
            "sigmoid_k_pm25": 0.20,
            "sigmoid_k_pm10": 0.08,
            "sigmoid_k_co": 0.008,
            "sigmoid_k_o3": 0.10,
            "sigmoid_k_no2": 0.07,
            "sigmoid_k_so2": 0.05,
            "sigmoid_k_temp": 0.4,

            # *** FIXED WEIGHTS: pollution dominates (70/30) ***
            "w_temp": 0.30,
            "w_pollution": 0.70,

            # Synergy multipliers
            "pollution_synergy_threshold": 45,
            "pollution_synergy_multiplier": 1.1,
            "heat_pollution_synergy_temp": 28,
            "heat_pollution_synergy_pol": 40,
            "heat_pollution_synergy_multiplier": 1.15,

            # Wind modifiers (document)
            "wind_cold_threshold": 10,
            "wind_cold_speed": 15,
            "wind_cold_penalty": 15,
            "wind_hot_threshold": 30,
            "wind_hot_benefit": -10,
            "wind_hot_still_penalty": 10,
            "wind_hot_still_speed": 5,

            # UV modifier
            "uv_threshold": 8,
            "uv_penalty": 7,

            # Humidity modifier
            "humidity_temp_threshold": 20,
            "humidity_base": 50,
            "humidity_factor": 0.3,

            # Clamping
            "clamp_max_temp": 50.0,
            "clamp_min_temp": -30.0,
            "clamp_max_pm25": 500.0,
            "clamp_min_pm25": 0.0,
        }

        # Load custom thresholds from data mining (if available)
        try:
            thresh_path = os.path.join(mining_dir, "critical_thresholds.csv")
            if os.path.exists(thresh_path):
                df = pd.read_csv(thresh_path)
                temp_row = df[df["feature"] == "temperature_celsius"]
                if not temp_row.empty:
                    thresholds = sorted([float(x) for x in eval(temp_row.iloc[0]["thresholds"])])
                    if len(thresholds) >= 2:
                        params["temp_caution"] = thresholds[0]
                        params["temp_danger"] = thresholds[1]
        except Exception:
            pass

        return params

    # =========================================================================
    # SIGMOID UTILITY
    # =========================================================================

    def _sigmoid(self, x: float, center: float, k: float) -> float:
        return 100 / (1 + np.exp(-k * (x - center)))

    # =========================================================================
    # MULTI-POLLUTANT SCORE (realistic for exercise)
    # =========================================================================

    def _pollution_score(self, pollutants: Dict) -> float:
        scores = []

        # ----- PM2.5 (primary, with linear scaling above 55) -----
        pm25 = pollutants.get("pm25", 0)
        if pm25 <= self.params["pm25_danger"]:
            s_pm25 = self._sigmoid(pm25, self.params["pm25_danger"], 0.20)
        else:
            # Linear from 55→60 up to 300→100
            excess = min(245, pm25 - self.params["pm25_danger"])
            linear_portion = (excess / 245) * 40   # 40 points to reach 100
            s_pm25 = min(100, 60 + linear_portion) # start at 60 at 55 µg/m³
        scores.append(s_pm25)

        # ----- PM10 -----
        pm10 = pollutants.get("pm10", 0)
        if pm10 and pm10 > 0:
            if pm10 <= self.params["pm10_danger"]:
                s_pm10 = self._sigmoid(pm10, self.params["pm10_danger"], 0.08)
            else:
                excess = min(350, pm10 - self.params["pm10_danger"])
                linear_portion = (excess / 350) * 30
                s_pm10 = min(100, 60 + linear_portion)
            scores.append(s_pm10)

        # ----- Gases (sigmoid only, rarely extreme) -----
        for pollutant, danger_key, k in [
            ("co", "co_danger", 0.008),
            ("o3", "o3_danger", 0.10),
            ("no2", "no2_danger", 0.07),
            ("so2", "so2_danger", 0.05)
        ]:
            val = pollutants.get(pollutant, 0)
            if val and val > 0:
                s = self._sigmoid(val, self.params[danger_key], k)
                scores.append(s)

        if not scores:
            return 0.0

        max_score = max(scores)
        # Synergy: if more than one pollutant > 45
        high_count = sum(1 for s in scores if s > 45)
        if high_count > 1:
            max_score *= self.params["pollution_synergy_multiplier"]

        return float(np.clip(max_score, 0, 100))

    # =========================================================================
    # TEMPERATURE SCORE (with humidity interaction)
    # =========================================================================

    def _temperature_score(self, temperature: float, humidity: Optional[float] = None) -> float:
        temperature = np.clip(temperature, self.params["clamp_min_temp"], self.params["clamp_max_temp"])

        # Heat stress (above 25°C)
        if temperature > 25:
            heat_score = self._sigmoid(temperature, self.params["temp_danger"], self.params["sigmoid_k_temp"])
        else:
            heat_score = 0.0

        # Cold stress – starts at 15°C, increases smoothly, reaches 100 at -10°C
        cold_start = 15.0   # temperature at which cold risk begins
        if temperature < cold_start:
            delta = cold_start - temperature
            # Exponential: gentle start, then steeper (no cliff)
            cold_score = 100 * (1 - np.exp(-delta / 5))
            # Alternative linear: cold_score = min(100, delta * 4)   # 4 points per degree
        else:
            cold_score = 0.0

        # Combine: take the larger (only one active in normal conditions)
        temp_base = max(heat_score, cold_score)

        # Humidity penalty (only when warm, >20°C)
        humidity_penalty = 0.0
        if humidity is not None and temperature > self.params["humidity_temp_threshold"]:
            if humidity > self.params["humidity_base"]:
                humidity_penalty = self.params["humidity_factor"] * (humidity - self.params["humidity_base"])

        total = temp_base + humidity_penalty
        return float(np.clip(total, 0, 100))

    # =========================================================================
    # WIND MODIFIER (document rules)
    # =========================================================================

    def _wind_modifier(self, temperature: float, wind_speed: float) -> float:
        modifier = 0.0
        if temperature < self.params["wind_cold_threshold"] and wind_speed > self.params["wind_cold_speed"]:
            modifier += self.params["wind_cold_penalty"]
        elif temperature > self.params["wind_hot_threshold"]:
            if wind_speed > self.params["wind_cold_speed"]:
                modifier += self.params["wind_hot_benefit"]
            elif wind_speed < self.params["wind_hot_still_speed"]:
                modifier += self.params["wind_hot_still_penalty"]
        return modifier

    # =========================================================================
    # UV MODIFIER
    # =========================================================================

    def _uv_modifier(self, uv_index: float) -> float:
        return self.params["uv_penalty"] if uv_index > self.params["uv_threshold"] else 0.0

    # =========================================================================
    # HEAT-POLLUTION SYNERGY
    # =========================================================================

    def _apply_heat_pollution_synergy(self, score: float, temperature: float, pollution_score: float) -> float:
        if (temperature > self.params["heat_pollution_synergy_temp"] and
            pollution_score > self.params["heat_pollution_synergy_pol"]):
            score *= self.params["heat_pollution_synergy_multiplier"]
        return min(100, score)

    # =========================================================================
    # INTERACTION SCORE (for output only)
    # =========================================================================

    def _interaction_score(self, temp_score: float, pollution_score: float) -> float:
        return float(np.clip(np.sqrt(temp_score * pollution_score), 0, 100))

    # =========================================================================
    # MAIN ED CALCULATION
    # =========================================================================

    def calculate_danger_score(
        self,
        PL: float,
        WD: float,
        sensitive_population: bool = False,
        humidity: Optional[float] = None,
        wind_speed: Optional[float] = None,
        uv_index: Optional[float] = None,
        pm10: Optional[float] = None,
        co: Optional[float] = None,
        o3: Optional[float] = None,
        no2: Optional[float] = None,
        so2: Optional[float] = None
    ) -> Dict:
        # Build pollutant dict
        pollutants = {
            "pm25": PL,
            "pm10": pm10,
            "co": co,
            "o3": o3,
            "no2": no2,
            "so2": so2
        }

        # Base scores
        temp_score = self._temperature_score(WD, humidity)
        pollution_score = self._pollution_score(pollutants)

        # Modifiers
        wind_mod = self._wind_modifier(WD, wind_speed) if wind_speed is not None else 0.0
        uv_mod = self._uv_modifier(uv_index) if uv_index is not None else 0.0
        total_modifiers = wind_mod + uv_mod

        # Sensitive population
        if sensitive_population:
            temp_score *= 1.10
            pollution_score *= 1.15

        temp_score = min(temp_score, 100)
        pollution_score = min(pollution_score, 100)

        # Weighted combination (70% pollution, 30% temperature)
        weighted_score = (self.params["w_temp"] * temp_score +
                          self.params["w_pollution"] * pollution_score)

        # Add modifiers and synergy
        score = weighted_score + total_modifiers
        score = self._apply_heat_pollution_synergy(score, WD, pollution_score)
        score = float(np.clip(score, 0, 100))

        interaction_score = self._interaction_score(temp_score, pollution_score)

        # Risk levels (aligned with Streamlit)
        if score >= 80:
            risk_level = "Extreme"
            status_text = "EXTREME DANGER"
        elif score >= 65:
            risk_level = "High"
            status_text = "HIGH RISK"
        elif score >= 45:
            risk_level = "Moderate"
            status_text = "MODERATE RISK"
        elif score >= 30:
            risk_level = "Low"
            status_text = "MODERATE SAFE"
        else:
            risk_level = "Very Low"
            status_text = "SAFE"

        # Dominant factors
        dominant_factors = []
        if pollution_score >= 60:
            dominant_factors.append("Air Pollution")
        if temp_score >= 60:
            dominant_factors.append("Temperature Stress")
        if interaction_score >= 60:
            dominant_factors.append("Combined Environmental Stress")
        if sensitive_population:
            dominant_factors.append("Sensitive Population")
        if wind_mod != 0:
            dominant_factors.append(f"Wind Effect ({wind_mod:+.0f})")
        if uv_mod > 0:
            dominant_factors.append("High UV Radiation")

        return {
            "ED": round(score, 2),
            "risk_level": risk_level,
            "status_text": status_text,
            "temperature_score": round(temp_score, 2),
            "pollution_score": round(pollution_score, 2),
            "interaction_score": round(interaction_score, 2),
            "wind_modifier": round(wind_mod, 2),
            "uv_modifier": round(uv_mod, 2),
            "dominant_factors": dominant_factors,
            "weights_used": {
                "temperature": self.params["w_temp"],
                "pollution": self.params["w_pollution"]
            }
        }


# Backward compatibility alias
ExerciseDangerPredictor = ExerciseDangerMathModel


# Simple wrapper for callers that only pass PL and WD
def calculate_simple_danger_score(PL: float, WD: float, sensitive_population: bool = False) -> Dict:
    model = ExerciseDangerMathModel()
    return model.calculate_danger_score(
        PL=PL, WD=WD,
        sensitive_population=sensitive_population,
        humidity=50, wind_speed=10, uv_index=3
    )