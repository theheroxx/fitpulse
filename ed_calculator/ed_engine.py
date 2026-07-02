import pandas as pd
import numpy as np
import os
import warnings
from typing import Dict, Optional
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import RobustScaler

warnings.filterwarnings("ignore")

class UltimateExerciseDangerModel:
    def __init__(
        self,
        base_dir: str = r"D:\Data mining",
        mining_dir: str = r"D:\Data mining\data mining\2- Decision Tree Analysis\decision_tree_results",
        anomaly_dir: str = r"D:\Data mining\data mining\5- Anomaly Detection\anomaly_results"
    ):
        print("🧠 Initializing Ultimate Hybrid ED Model...")
        self.base_path = base_dir
        
        # 1. Load Parameters from Decision Tree (Step 2) & Anomaly Detection (Step 5)
        self.params = self._load_dynamic_parameters(mining_dir, anomaly_dir)
        
        # 2. Load ML Inference Helpers (KNN / GNN Bias from Code 3)
        self.cluster_model = None
        self.bias_map = None  
        self.sigma_map = None 
        self.scaler = None
        self.is_ai_ready = False
        
        self._integrate_ml_results()

    # =========================================================================
    # PARAMETER LOADING (FROM CODE 2 & 1)
    # =========================================================================
    def _load_dynamic_parameters(self, mining_dir: str, anomaly_dir: str) -> Dict:
        # Default Medical Baselines (Code 1)
        params = {
            "temp_safe": 10.0, "temp_caution": 24.0, "temp_danger": 30.0,
            "pm25_danger": 55.0, "pm10_danger": 150.0,
            "co_danger": 1500.0, "o3_danger": 120.0, "no2_danger": 200.0, "so2_danger": 300.0,
            "w_temp": 0.30, "w_pollution": 0.70, # CODE 1 WEIGHTS (Pollution priority)
            "clamp_max_temp": 50.0, "clamp_max_pm25": 450.0,
            "humidity_factor": 0.3, "uv_penalty": 7.0
        }

        # Load Decision Tree Thresholds (Code 2 Logic)
        try:
            thresh_path = os.path.join(mining_dir, "critical_thresholds.csv")
            if os.path.exists(thresh_path):
                df = pd.read_csv(thresh_path)
                temp_row = df[df["feature"] == "temperature_celsius"]
                if not temp_row.empty:
                    thresholds = sorted([float(x) for x in eval(temp_row.iloc[0]["thresholds"])])
                    params["temp_caution"], params["temp_danger"] = thresholds[0], thresholds[-1]
        except Exception: pass

        # Load Anomaly Clamps (Code 2 Logic)
        try:
            anom_path = os.path.join(anomaly_dir, "confirmed_anomalies.csv")
            if os.path.exists(anom_path):
                df_anom = pd.read_csv(anom_path)
                if not df_anom.empty and 'temperature' in df_anom.columns:
                    params["clamp_max_temp"] = float(df_anom[df_anom['temperature'] > 35]['temperature'].min())
        except Exception: pass

        return params

    # =========================================================================
    # ML INTEGRATION (FROM CODE 3)
    # =========================================================================
    def _integrate_ml_results(self):
        csv_path = os.path.join(self.base_path, "FINAL_EXERCISE_DANGER_SCORES_R.csv")
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path, usecols=['cluster', 'gnn_bias', 'final_danger_score', 
                                                   'temperature_celsius', 'humidity', 'air_quality_PM2.5'])
                self.bias_map = df.groupby('cluster')['gnn_bias'].mean().to_dict()
                self.sigma_map = df.groupby('cluster')['final_danger_score'].std().fillna(3.0).to_dict()

                # Train KNN to map live input to Climate Clusters
                train_df = df.dropna().sample(min(len(df), 50000), random_state=42)
                X = train_df[['temperature_celsius', 'humidity', 'air_quality_PM2.5']]
                self.scaler = RobustScaler().fit(X)
                self.cluster_model = KNeighborsClassifier(n_neighbors=5).fit(self.scaler.transform(X), train_df['cluster'])
                self.is_ai_ready = True
                print("   ✅ GNN Bias & Cluster Logic Integrated.")
            except Exception as e: print(f"   ⚠️ ML Integration Failed: {e}")

    # =========================================================================
    # MATH ENGINE (CODE 1 IMPROVED)
    # =========================================================================
    def _sigmoid(self, x: float, center: float, k: float) -> float:
        return 100 / (1 + np.exp(-k * (x - center)))

    def _pollution_score(self, pollutants: Dict) -> float:
        scores = []
        # PM2.5 Hybrid (Code 1: Linear above danger threshold)
        pm25 = pollutants.get("pm25", 0)
        if pm25 <= self.params["pm25_danger"]:
            s_pm25 = self._sigmoid(pm25, self.params["pm25_danger"], 0.20)
        else:
            excess = min(245, pm25 - self.params["pm25_danger"])
            s_pm25 = min(100, 60 + (excess / 245) * 40)
        scores.append(s_pm25)

        # Other pollutants (Sigmoids)
        for pol, key, k in [("pm10","pm10_danger",0.08), ("co","co_danger",0.008), 
                             ("o3","o3_danger",0.10), ("no2","no2_danger",0.07)]:
            val = pollutants.get(pol, 0)
            if val: scores.append(self._sigmoid(val, self.params[key], k))

        max_score = max(scores)
        # Cocktail effect (Code 2/3)
        if sum(1 for s in scores if s > 45) > 1: max_score *= 1.1
        return float(np.clip(max_score, 0, 100))

    def _temperature_score(self, temp: float, humidity: float) -> float:
        # Heat (Sigmoid)
        heat = self._sigmoid(temp, self.params["temp_danger"], 0.4) if temp > 25 else 0.0
        # Cold (Code 1: Exponential - better than sigmoid for cold)
        cold = 100 * (1 - np.exp(-(15.0 - temp) / 5)) if temp < 15 else 0.0
        
        base = max(heat, cold)
        if temp > 20 and humidity > 50:
            base += (humidity - 50) * self.params["humidity_factor"]
        return float(np.clip(base, 0, 100))

    # =========================================================================
    # FINAL PREDICTION PIPELINE
    # =========================================================================
    def predict(self, inputs: Dict) -> Dict:
        temp = inputs.get('temp', 20)
        pm25 = inputs.get('pm25', 10)
        
        # 1. Anomaly Kill-Switch (Code 2 Logic)
        if temp > self.params['clamp_max_temp'] or pm25 > self.params['clamp_max_pm25']:
            return {"ED": 100.0, "status": "EXTREME DANGER (ANOMALY DETECTED)", "range": "99-100"}

        # 2. Physics Base (Code 1 Weights: 70% Pollution / 30% Temp)
        s_pol = self._pollution_score(inputs)
        s_temp = self._temperature_score(temp, inputs.get('humid', 50))
        
        weighted_score = (self.params["w_temp"] * s_temp) + (self.params["w_pollution"] * s_pol)
        
        # 3. Modifiers (Wind/UV)
        mod = 0
        wind, uv = inputs.get('wind', 10), inputs.get('uv', 3)
        if temp < 10 and wind > 15: mod += 15
        elif temp > 30 and wind < 5: mod += 10
        if uv > 8: mod += self.params["uv_penalty"]
        
        final_math = weighted_score + mod

        # 4. AI Residual/Bias (Code 3 Logic)
        gnn_bias, sigma = 0.0, 5.0
        cluster_id = -1
        if self.is_ai_ready:
            in_vec = self.scaler.transform([[temp, inputs.get('humid', 50), pm25]])
            cluster_id = int(self.cluster_model.predict(in_vec)[0])
            gnn_bias = self.bias_map.get(cluster_id, 0.0)
            sigma = self.sigma_map.get(cluster_id, 5.0)

        # 5. Final Integration
        total_score = np.clip(final_math + gnn_bias, 0, 100)
        
        # Heat-Pollution Synergy
        if temp > 28 and s_pol > 40: total_score = min(100, total_score * 1.15)

        # 6. Formatting Result
        levels = [(80, "EXTREME"), (65, "HIGH RISK"), (45, "MODERATE"), (30, "LOW RISK"), (0, "SAFE")]
        risk_level = next(lvl for thr, lvl in levels if total_score >= thr)

        return {
            "ED": round(total_score, 2),
            "Risk_Level": risk_level,
            "Physics_Component": round(final_math, 2),
            "AI_Bias_Applied": round(gnn_bias, 2),
            "Confidence_Range": f"{max(0, round(total_score-sigma))} - {min(100, round(total_score+sigma))}",
            "Cluster": cluster_id,
            "Dominant_Factors": [k for k, v in {"Heat": s_temp, "Pollution": s_pol} if v > 60]
        }

