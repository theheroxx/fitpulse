# ed_calculator/math_model.py
"""
math_model.py
=============
Thin wrapper around ed_baseline.py.
Adds GNN regional adjustment (Step 3) and anomaly override (Step 5).
All core scoring is delegated to ed_baseline.

UPDATED (2026-08-10):
  - Added safe defaults (like old ed_engine) to prevent None crashes.
  - Added Optional import.
  - All external calls now have fallback defaults.
  - Maintains compatibility with old UI/API expectations.
"""
import json
import numpy as np
from pathlib import Path
import sys
from typing import Dict, Optional

# ─── Path fix for FitPulse ──────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

# ─── Relative imports (same package) ──────────────────────────────
from .ed_baseline import compute_ed_baseline, _score_to_category


class ExerciseDangerMathModel:
    def __init__(
        self,
        gnn_min: float = -10.0,
        gnn_max: float = 15.0,
        bias_map: dict | None = None,
    ):
        self.gnn_min = gnn_min
        self.gnn_max = gnn_max
        self.bias_map = bias_map or self._load_bias_map()
        self.sigma_map = self._load_sigma_map()
        print(f"✅ ED model initialized. Bias map: {self.bias_map}")

    # =========================================================================
    # LOAD GNN BIAS MAP (from ed_calculator/data/)
    # =========================================================================
    def _load_bias_map(self) -> dict:
        """Load GNN bias map from ed_calculator/data/ (or fallback)."""
        # Primary location: ed_calculator/data/
        gnn_path = Path(__file__).resolve().parent / "data" / "FINAL_EXERCISE_DANGER_SCORES_R.csv"
        
        if gnn_path.exists():
            try:
                import pandas as pd
                df = pd.read_csv(gnn_path)
                if "cluster" in df.columns and "gnn_bias" in df.columns:
                    bias_map = df.groupby("cluster")["gnn_bias"].mean().to_dict()
                    print(f"   ✅ GNN bias map loaded from: {gnn_path}")
                    print(f"   📊 Biases: {bias_map}")
                    return bias_map
            except Exception as e:
                print(f"   ⚠️ Could not load GNN bias map: {e}")
        
        # Fallback: try outputs/gnn/
        gnn_path_fallback = PROJECT_ROOT / "outputs" / "gnn" / "FINAL_EXERCISE_DANGER_SCORES_R.csv"
        if gnn_path_fallback.exists():
            try:
                import pandas as pd
                df = pd.read_csv(gnn_path_fallback)
                if "cluster" in df.columns and "gnn_bias" in df.columns:
                    bias_map = df.groupby("cluster")["gnn_bias"].mean().to_dict()
                    print(f"   ✅ GNN bias map loaded from: {gnn_path_fallback}")
                    return bias_map
            except Exception as e:
                print(f"   ⚠️ Could not load fallback GNN bias map: {e}")
        
        # Final fallback: clustering profiles
        profiles_path = PROJECT_ROOT / "outputs" / "step3_clustering" / "cluster_profiles.csv"
        if profiles_path.exists():
            try:
                import pandas as pd
                df = pd.read_csv(profiles_path)
                if "cluster" in df.columns and "ed_offset_vs_global" in df.columns:
                    bias_map = dict(zip(df["cluster"], df["ed_offset_vs_global"]))
                    print(f"   ✅ Fallback bias map loaded from: {profiles_path}")
                    return bias_map
            except Exception as e:
                print(f"   ⚠️ Could not load fallback bias map: {e}")
        
        print("   ⚠️ No bias map found. Using no regional adjustment.")
        return {}

    def _load_sigma_map(self) -> dict:
        """Load per-cluster confidence (sigma) for confidence ranges."""
        gnn_path = Path(__file__).resolve().parent / "data" / "FINAL_EXERCISE_DANGER_SCORES_R.csv"
        if gnn_path.exists():
            try:
                import pandas as pd
                df = pd.read_csv(gnn_path)
                if "cluster" in df.columns and "final_danger_score" in df.columns:
                    sigma_map = df.groupby("cluster")["final_danger_score"].std().to_dict()
                    sigma_map = {k: max(v, 3.0) for k, v in sigma_map.items()}
                    return sigma_map
            except Exception as e:
                print(f"   ⚠️ Could not load sigma map: {e}")
        
        # Default sigma (like old code)
        return {0: 5.0, 1: 5.0, 2: 5.0, 3: 5.0, 4: 5.0, 5: 5.0}

    # =========================================================================
    # MAIN PREDICTION (with safe defaults like old ed_engine)
    # =========================================================================
    def predict(
        self,
        temperature_celsius: float = 22.0,
        humidity: float = 45.0,
        wind_kph: float = 10.0,
        uv_index: float = 3.0,
        air_quality_us_epa_index: float = 1.0,
        air_quality_PM2_5: Optional[float] = None,
        air_quality_PM10: Optional[float] = None,
        air_quality_Ozone: Optional[float] = None,
        air_quality_Nitrogen_dioxide: Optional[float] = None,
        air_quality_Sulphur_dioxide: Optional[float] = None,
        air_quality_Carbon_Monoxide: Optional[float] = None,
        cluster_id: Optional[int] = None,
        anomaly_flag: bool = False,
    ) -> dict:
        """
        Single‑observation prediction with safe defaults (like old ed_engine).
        
        All parameters have fallback defaults so that None values from the API
        do not crash the system.
        """
        # ─── Convert None to defaults (defensive) ──────────────────────
        temperature_celsius = temperature_celsius if temperature_celsius is not None else 22.0
        humidity = humidity if humidity is not None else 45.0
        wind_kph = wind_kph if wind_kph is not None else 10.0
        uv_index = uv_index if uv_index is not None else 3.0
        air_quality_us_epa_index = air_quality_us_epa_index if air_quality_us_epa_index is not None else 1.0

        # ─── Anomaly override ──────────────────────────────────────────
        if anomaly_flag:
            return {
                "ED": 100.0,
                "Risk_Level": "EXTREME",
                "Category": "ED_VERY_DANGEROUS",
                "breakdown": {"anomaly_override": 100.0},
                "regional_adjustment": 0.0,
                "safety_floor_activated": False,
                "max_component": 0.0,
                "confidence_range": "85 - 100",
                "note": "Anomaly detected – exercise not advised.",
                "status": "ANOMALY DETECTED",          # old compatibility
                "AI_Bias_Applied": 0.0,
                "Cluster": -1,
                "Physics_Component": 100.0,
            }

        # ─── Build weather dict ────────────────────────────────────────
        weather = {
            "temperature_celsius": temperature_celsius,
            "humidity": humidity,
            "wind_kph": wind_kph,
            "uv_index": uv_index,
            "air_quality_us-epa-index": air_quality_us_epa_index,
        }
        
        # Only add pollutants if they are not None
        if air_quality_PM2_5 is not None:
            weather["air_quality_PM2.5"] = air_quality_PM2_5
        if air_quality_PM10 is not None:
            weather["air_quality_PM10"] = air_quality_PM10
        if air_quality_Ozone is not None:
            weather["air_quality_Ozone"] = air_quality_Ozone
        if air_quality_Nitrogen_dioxide is not None:
            weather["air_quality_Nitrogen_dioxide"] = air_quality_Nitrogen_dioxide
        if air_quality_Sulphur_dioxide is not None:
            weather["air_quality_Sulphur_dioxide"] = air_quality_Sulphur_dioxide
        if air_quality_Carbon_Monoxide is not None:
            weather["air_quality_Carbon_Monoxide"] = air_quality_Carbon_Monoxide

        # ─── Call baseline ─────────────────────────────────────────────
        base_result = compute_ed_baseline(weather)
        baseline_ed = base_result["ed_score"]
        components = base_result["components"]
        baseline_category = base_result["ed_category"]

        # ─── Regional adjustment ──────────────────────────────────────
        regional_adj = 0.0
        if cluster_id is not None and self.bias_map:
            regional_adj = self.bias_map.get(cluster_id, 0.0)
        adj = float(max(self.gnn_min, min(self.gnn_max, regional_adj)))

        # ─── Final ED ─────────────────────────────────────────────────
        final_ed = float(np.clip(baseline_ed + adj, 0, 100))

        # ─── Category ─────────────────────────────────────────────────
        final_category = _score_to_category(np.array([final_ed]))[0]

        # ─── Safety floor ─────────────────────────────────────────────
        max_component = max(components.values())
        safety_floor_activated = max_component > 70

        # ─── Confidence range ─────────────────────────────────────────
        sigma = self.sigma_map.get(cluster_id, 5.0) if cluster_id is not None else 5.0
        range_min = max(0, int(final_ed - sigma))
        range_max = min(100, int(final_ed + sigma))

        # ─── Risk level ───────────────────────────────────────────────
        risk_map = {
            "ED_VERY_DANGEROUS": "EXTREME",
            "ED_DANGEROUS": "DANGEROUS",
            "ED_CAUTION": "CAUTION",
            "ED_MODERATE_SAFE": "MODERATE SAFE",
            "ED_VERY_SAFE": "VERY SAFE",
        }
        risk_level = risk_map.get(final_category, "UNKNOWN")

        # ─── Return with old compatibility fields ─────────────────────
        return {
            "ED": round(final_ed, 2),
            "Risk_Level": risk_level,
            "Category": final_category,
            "breakdown": components,
            "baseline_ed": round(baseline_ed, 2),
            "regional_adjustment": round(adj, 2),
            "safety_floor_activated": safety_floor_activated,
            "max_component": round(max_component, 2),
            "confidence_range": f"{range_min} - {range_max}",
            # ─── Old interface compatibility ──────────────────────────
            "AI_Bias_Applied": round(adj, 2),
            "Cluster": cluster_id if cluster_id is not None else -1,
            "Physics_Component": round(baseline_ed, 2),
            "status": "NORMAL",   # no anomaly
        }

    # =========================================================================
    # LEGACY WRAPPER (for old calculate_danger_score calls)
    # =========================================================================
    def calculate_danger_score(
        self,
        PL: float,
        WD: float,
        sensitive_population: bool = False,
        humidity: Optional[float] = 50,
        wind_speed: Optional[float] = 10,
        uv_index: Optional[float] = 3,
        pm10: float = 0.0,
        co: float = 0.0,
        o3: float = 0.0,
        no2: float = 0.0,
        so2: float = 0.0
    ) -> Dict:
        """
        Wrapper to maintain compatibility with old interface.
        """
        # Convert old parameter names to new
        result = self.predict(
            temperature_celsius=WD,
            humidity=humidity if humidity is not None else 50.0,
            wind_kph=wind_speed if wind_speed is not None else 10.0,
            uv_index=uv_index if uv_index is not None else 3.0,
            air_quality_us_epa_index=1,  # Default, could be improved
            air_quality_PM2_5=PL if PL > 0 else None,
            air_quality_PM10=pm10 if pm10 > 0 else None,
            air_quality_Ozone=o3 if o3 > 0 else None,
            air_quality_Nitrogen_dioxide=no2 if no2 > 0 else None,
            air_quality_Sulphur_dioxide=so2 if so2 > 0 else None,
            air_quality_Carbon_Monoxide=co if co > 0 else None,
            cluster_id=None,  # KNN not implemented
        )
        
        # Add old fields
        result['risk_level'] = result['Risk_Level']
        result['status_text'] = result.get('status', result['Risk_Level'])
        result['temperature_score'] = result['breakdown'].get('heat', 0) * 2.22  # approximate scaling
        result['pollution_score'] = result['breakdown'].get('air', 0)
        result['interaction_score'] = round(
            float(np.sqrt(
                result['breakdown'].get('heat', 0) * result['breakdown'].get('air', 0)
            )), 2
        )
        
        factors = []
        if result['breakdown'].get('air', 0) >= 60:
            factors.append("Air Pollution")
        if result['breakdown'].get('heat', 0) >= 60:
            factors.append("Temperature Stress")
        if uv_index and uv_index > 8:
            factors.append("High UV Radiation")
        if result.get('status') == "ANOMALY DETECTED":
            factors.append("Environmental Anomaly")
        result['dominant_factors'] = factors
        
        return result


# ─── Keep the old class name for backward compatibility ────────────
ExerciseDangerPredictor = ExerciseDangerMathModel