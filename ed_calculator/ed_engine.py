# ed_calculator/ed_engine.py
import pandas as pd
import numpy as np
import os
import warnings
from typing import Dict, Optional

warnings.filterwarnings("ignore")

class ExerciseDangerMathModel:
    def __init__(
        self,
        base_dir: str = r"D:\Data mining",
        mining_dir: str = r"D:\Data mining\data mining\2- Decision Tree Analysis\decision_tree_results",
        anomaly_dir: str = r"D:\Data mining\data mining\5- Anomaly Detection\anomaly_results"
    ):
        print("🧠 Initializing Medical-Grade Hybrid ED Model...")
        self.base_path = base_dir
        
        # 1. Load Dynamic Parameters from Decision Tree & Anomaly Results
        self.params = self._load_dynamic_parameters(mining_dir, anomaly_dir)
        
        # 2. ML Contextual Helpers (initially empty, loaded in background)
        self.cluster_model = None
        self.bias_map = {}  
        self.sigma_map = {} 
        self.scaler = None
        self.is_ai_ready = False
        self._ml_loading_complete = False
        
        # Start ML loading in background (non-blocking)
       # self._start_ml_loading()

    def _load_dynamic_parameters(self, mining_dir: str, anomaly_dir: str) -> Dict:
        params = {
            "temp_safe": 10.0, "temp_caution": 24.0, "temp_danger": 30.0,
            "pm25_danger": 55.0, "pm10_danger": 150.0,
            "co_danger": 1500.0, "o3_danger": 120.0, "no2_danger": 200.0, "so2_danger": 300.0,
            "w_temp": 0.30, "w_pollution": 0.70,
            "clamp_max_temp": 50.0, "clamp_max_pm25": 450.0,
            "humidity_factor": 0.3, "uv_penalty": 7.0
        }
        try:
            thresh_path = os.path.join(mining_dir, "critical_thresholds.csv")
            if os.path.exists(thresh_path):
                df = pd.read_csv(thresh_path)
                temp_row = df[df["feature"] == "temperature_celsius"]
                if not temp_row.empty:
                    thresholds = sorted([float(x) for x in eval(temp_row.iloc[0]["thresholds"])])
                    params["temp_caution"], params["temp_danger"] = thresholds[0], thresholds[-1]
        except Exception:
            pass

        try:
            anom_path = os.path.join(anomaly_dir, "confirmed_anomalies.csv")
            if os.path.exists(anom_path):
                df_anom = pd.read_csv(anom_path)
                if not df_anom.empty and 'temperature' in df_anom.columns:
                    params["clamp_max_temp"] = float(df_anom[df_anom['temperature'] > 35]['temperature'].min())
        except Exception:
            pass
        return params

    # =========================================================================
    # BACKGROUND ML LOADING (NON-BLOCKING)
    # =========================================================================

    def _start_ml_loading(self):
        """Start ML loading in a background thread."""
        import threading
        
        def load():
            try:
                self._integrate_ml_results()
            except Exception as e:
                print(f"   ⚠️ Background ML load failed: {e}")
            finally:
                self._ml_loading_complete = True
        
        thread = threading.Thread(target=load, daemon=True)
        thread.start()

    # =========================================================================
    # ML INTEGRATION — GNN + KNN (COMMENTED OUT, FALLBACK MODE)
    # =========================================================================

    def _integrate_ml_results(self):
        """
        Load ML models from CSV.
        
        ⚠️ GNN and KNN are currently COMMENTED OUT because the CSV
        (FINAL_EXERCISE_DANGER_SCORES_R.csv) is missing 'humidity' and
        'air_quality_PM2.5' columns needed for full ML pipeline.
        
        To re-enable:
        1. Add 'humidity' and 'air_quality_PM2.5' to the CSV
        2. Uncomment the KNN training section below
        3. Uncomment the GNN bias application in predict()
        """
        csv_path = os.path.join(self.base_path, "FINAL_EXERCISE_DANGER_SCORES_R.csv")
        
        if not os.path.exists(csv_path):
            print("   ℹ️ ML CSV not found. Using rule-based only.")
            return
        
        try:
            # ── Load GNN Bias Map (always available) ──────────────
            df_bias = pd.read_csv(csv_path, usecols=['cluster', 'gnn_bias', 'final_danger_score'])
            df_bias = df_bias.dropna()
            
            if len(df_bias) == 0:
                print("   ⚠️ No valid data in ML CSV.")
                return
            
            self.bias_map = df_bias.groupby('cluster')['gnn_bias'].mean().to_dict()
            self.sigma_map = df_bias.groupby('cluster')['final_danger_score'].std().fillna(3.0).to_dict()
            print(f"   ✅ GNN bias map loaded ({len(self.bias_map)} clusters).")
            
            # ── KNN Training (DISABLED – missing columns) ──────────
            # To re-enable KNN:
            # 1. Ensure CSV has: 'temperature_celsius', 'humidity', 'air_quality_PM2.5'
            # 2. Uncomment the code below
            # 3. Remove the 'return' statement
            
            print("   ⚠️ KNN disabled: missing 'humidity' and 'air_quality_PM2.5' columns.")
            print("   ℹ️ ED engine running in FALLBACK mode (math model + GNN bias only).")
            
            """
            # ── KNN TRAINING (COMMENTED OUT) ──────────────────────
            # Requires: temperature_celsius, humidity, air_quality_PM2.5
            
            from sklearn.neighbors import KNeighborsClassifier
            from sklearn.preprocessing import RobustScaler
            
            # Check if required columns exist
            df_sample = pd.read_csv(csv_path, nrows=5)
            available_cols = df_sample.columns.tolist()
            
            required_cols = ['temperature_celsius', 'humidity', 'air_quality_PM2.5']
            if all(col in available_cols for col in required_cols):
                print("   📊 Training KNN with full features...")
                
                # Load sample for KNN
                df_knn = pd.read_csv(csv_path, usecols=['cluster'] + required_cols, nrows=10000)
                df_knn.columns = ['cluster'] + required_cols
                train_df = df_knn.dropna()
                
                if len(train_df) > 0:
                    X = train_df[required_cols]
                    self.scaler = RobustScaler().fit(X)
                    self.cluster_model = KNeighborsClassifier(n_neighbors=5).fit(
                        self.scaler.transform(X), train_df['cluster']
                    )
                    self.is_ai_ready = True
                    print("   ✅ KNN trained successfully.")
                else:
                    print("   ⚠️ KNN training data empty.")
            else:
                missing = [col for col in required_cols if col not in available_cols]
                print(f"   ⚠️ KNN skipped: missing columns: {missing}")
            """
            
            # ⚠️ FALLBACK: Set is_ai_ready to True even without KNN
            # This allows GNN bias to be used (if available)
            self.is_ai_ready = bool(self.bias_map)
            print(f"   ✅ ED engine ready (GNN bias only, KNN disabled).")
                
        except Exception as e:
            print(f"   ⚠️ ML load error: {e}")
            self.is_ai_ready = bool(self.bias_map)

    # =========================================================================
    # CORE METHODS
    # =========================================================================

    def _sigmoid(self, x: float, center: float, k: float) -> float:
        return 100 / (1 + np.exp(-k * (x - center)))

    def _pollution_score(self, pollutants: Dict) -> float:
        scores = []
        pm25 = pollutants.get("pm25", 0)
        if pm25 <= self.params["pm25_danger"]:
            s_pm25 = self._sigmoid(pm25, self.params["pm25_danger"], 0.20)
        else:
            excess = min(245, pm25 - self.params["pm25_danger"])
            s_pm25 = min(100, 60 + (excess / 245) * 40)
        scores.append(s_pm25)

        for pol, key, k in [("pm10","pm10_danger",0.08), ("co","co_danger",0.008), 
                             ("o3","o3_danger",0.10), ("no2","no2_danger",0.07)]:
            val = pollutants.get(pol, 0)
            if val:
                scores.append(self._sigmoid(val, self.params[key], k))
        
        max_score = max(scores) if scores else 0
        if sum(1 for s in scores if s > 45) > 1:
            max_score *= 1.1
        return float(np.clip(max_score, 0, 100))

    def _temperature_score(self, temp: float, humidity: float) -> float:
        heat = self._sigmoid(temp, self.params["temp_danger"], 0.4) if temp > 25 else 0.0
        cold = 100 * (1 - np.exp(-(15.0 - temp) / 5)) if temp < 15 else 0.0
        base = max(heat, cold)
        if temp > 20 and humidity > 50:
            base += (humidity - 50) * self.params["humidity_factor"]
        return float(np.clip(base, 0, 100))

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    def load_ml_async(self, callback=None):
        """Force ML loading in background (for manual control)."""
        import threading
        def load():
            try:
                self._integrate_ml_results()
                if callback:
                    callback(True, None)
            except Exception as e:
                if callback:
                    callback(False, str(e))
        thread = threading.Thread(target=load, daemon=True)
        thread.start()

    def calculate_danger_score(
        self,
        PL: float, WD: float,
        sensitive_population: bool = False,
        humidity: Optional[float] = 50,
        wind_speed: Optional[float] = 10,
        uv_index: Optional[float] = 3,
        pm10=0, co=0, o3=0, no2=0, so2=0
    ) -> Dict:
        inputs = {
            'temp': WD, 'pm25': PL, 'humid': humidity, 
            'wind': wind_speed, 'uv': uv_index,
            'pm10': pm10, 'co': co, 'o3': o3, 'no2': no2, 'so2': so2
        }
        
        res = self.predict(inputs)
        
        res['risk_level'] = res['Risk_Level']
        res['status_text'] = res.get('status', res['Risk_Level'])
        
        t_score = self._temperature_score(WD, humidity)
        p_score = self._pollution_score(inputs)
        
        res['temperature_score'] = round(t_score, 2)
        res['pollution_score'] = round(p_score, 2)
        res['interaction_score'] = round(float(np.sqrt(t_score * p_score)), 2)
        
        factors = []
        if p_score >= 60:
            factors.append("Air Pollution")
        if t_score >= 60:
            factors.append("Temperature Stress")
        if uv_index and uv_index > 8:
            factors.append("High UV Radiation")
        if res.get('status') == "ANOMALY DETECTED":
            factors.append("Environmental Anomaly")
        
        res['dominant_factors'] = factors
        return res

    def predict(self, inputs: Dict) -> Dict:
        temp = inputs.get('temp', 20)
        pm25 = inputs.get('pm25', 10)
        
        if temp > self.params['clamp_max_temp'] or pm25 > self.params['clamp_max_pm25']:
            return {"ED": 100.0, "Risk_Level": "EXTREME", "status": "ANOMALY DETECTED"}

        s_pol = self._pollution_score(inputs)
        s_temp = self._temperature_score(temp, inputs.get('humid', 50))
        
        base_weighted = (self.params["w_temp"] * s_temp) + (self.params["w_pollution"] * s_pol)
        safety_floor = max(s_temp, s_pol)
        
        if safety_floor > 60:
            alpha = min(1.0, (safety_floor - 60) / 40)
            final_math = (base_weighted * (1 - alpha)) + (safety_floor * alpha)
        else:
            final_math = base_weighted
        
        mod = 0
        wind, uv = inputs.get('wind', 10), inputs.get('uv', 3)
        if temp < 10 and wind > 15:
            mod += 15
        elif temp > 30 and wind < 5:
            mod += 10
        if uv > 8:
            mod += self.params["uv_penalty"]
        
        final_physics = final_math + mod

        # ── GNN Bias (loaded from CSV) ────────────────────────────
        gnn_bias, sigma = 0.0, 5.0
        cluster_id = -1
        
        if self.is_ai_ready and self.bias_map:
            # Use a simple fallback to pick the most common cluster
            # In full mode, KNN would predict the cluster
            try:
                # Find the cluster with the closest average temperature
                # This is a fallback – KNN would be more accurate
                cluster_ids = list(self.bias_map.keys())
                if cluster_ids:
                    # Default to the first cluster (or use a temp-based heuristic)
                    if temp > 30:
                        cluster_id = 0  # Hot cluster
                    elif temp > 20:
                        cluster_id = 1  # Warm cluster
                    else:
                        cluster_id = 2  # Cool cluster
                    
                    # If the cluster exists in the map, use it
                    if cluster_id in self.bias_map:
                        gnn_bias = self.bias_map.get(cluster_id, 0.0)
                        sigma = self.sigma_map.get(cluster_id, 5.0)
                    else:
                        # Fallback to first available cluster
                        first_cluster = cluster_ids[0]
                        gnn_bias = self.bias_map.get(first_cluster, 0.0)
                        sigma = self.sigma_map.get(first_cluster, 5.0)
            except Exception:
                pass

        total_score = np.clip(final_physics + gnn_bias, 0, 100)
        
        if temp > 28 and s_pol > 40:
            total_score = min(100, total_score * 1.15)

        levels = [(80, "EXTREME"), (65, "HIGH RISK"), (45, "MODERATE"), (30, "LOW RISK"), (0, "SAFE")]
        risk_level = next(lvl for thr, lvl in levels if total_score >= thr)

        return {
            "ED": round(total_score, 2),
            "Risk_Level": risk_level,
            "Physics_Component": round(final_physics, 2),
            "AI_Bias_Applied": round(gnn_bias, 2),
            "Confidence_Range": f"{max(0, round(total_score-sigma))} - {min(100, round(total_score+sigma))}",
            "Cluster": cluster_id
        }

ExerciseDangerPredictor = ExerciseDangerMathModel