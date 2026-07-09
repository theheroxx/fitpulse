# ui/desktop/workers/ml_loader.py
from PySide6.QtCore import QThread, Signal
import pandas as pd
import numpy as np
import os
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import RobustScaler


class MLLoaderWorker(QThread):
    """Background worker for loading ML models without freezing the UI."""
    
    finished = Signal(dict)
    progress = Signal(str)
    error = Signal(str)

    def __init__(self, base_path: str):
        super().__init__()
        self.base_path = base_path

    def run(self):
        try:
            self.progress.emit("📊 Loading ML models...")
            
            csv_path = os.path.join(self.base_path, "FINAL_EXERCISE_DANGER_SCORES_R.csv")
            
            if not os.path.exists(csv_path):
                self.progress.emit("⚠️ ML CSV not found. Using rule-based only.")
                self.finished.emit({})
                return
            
            # Read CSV
            df = pd.read_csv(csv_path)
            available_cols = df.columns.tolist()
            self.progress.emit(f"📊 Found columns: {available_cols}")
            
            result = {
                'bias_map': {},
                'sigma_map': {},
                'scaler': None,
                'cluster_model': None,
                'is_ready': False
            }
            
            # ── Load GNN Bias Map ──────────────────────────────────
            required = ['cluster', 'gnn_bias', 'final_danger_score']
            missing = [col for col in required if col not in available_cols]
            
            if missing:
                self.progress.emit(f"⚠️ Missing columns: {missing}. ML disabled.")
                self.finished.emit(result)
                return
            
            # Build bias and sigma maps
            bias_map = df.groupby('cluster')['gnn_bias'].mean().to_dict()
            sigma_map = df.groupby('cluster')['final_danger_score'].std().fillna(3.0).to_dict()
            
            result['bias_map'] = bias_map
            result['sigma_map'] = sigma_map
            result['is_ready'] = True
            
            self.progress.emit(f"✅ GNN bias map loaded ({len(bias_map)} clusters).")
            
            # ── KNN Training (DISABLED – missing columns) ────────
            # To re-enable KNN:
            # 1. Ensure CSV has: 'temperature_celsius', 'humidity', 'air_quality_PM2.5'
            # 2. Uncomment the code below
            # 3. Remove the 'return' statement
            
            self.progress.emit("⚠️ KNN disabled: missing 'humidity' and 'air_quality_PM2.5' columns.")
            self.progress.emit("ℹ️ ED engine running in FALLBACK mode (math model + GNN bias only).")
            
            """
            # ── KNN TRAINING (COMMENTED OUT) ──────────────────────
            # Requires: temperature_celsius, humidity, air_quality_PM2.5
            
            required_cols = ['temperature_celsius', 'humidity', 'air_quality_PM2.5']
            if all(col in available_cols for col in required_cols):
                self.progress.emit("📊 Training KNN with full features...")
                
                df_knn = pd.read_csv(csv_path, usecols=['cluster'] + required_cols, nrows=10000)
                df_knn.columns = ['cluster'] + required_cols
                train_df = df_knn.dropna()
                
                if len(train_df) > 0:
                    X = train_df[required_cols]
                    scaler = RobustScaler().fit(X)
                    cluster_model = KNeighborsClassifier(n_neighbors=5).fit(
                        scaler.transform(X), train_df['cluster']
                    )
                    result['scaler'] = scaler
                    result['cluster_model'] = cluster_model
                    result['is_ready'] = True
                    self.progress.emit("✅ KNN trained successfully.")
                else:
                    self.progress.emit("⚠️ KNN training data empty.")
            else:
                missing_cols = [col for col in required_cols if col not in available_cols]
                self.progress.emit(f"⚠️ KNN skipped: missing columns: {missing_cols}")
            """
            
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(f"ML Load Error: {str(e)}")
            self.finished.emit({})