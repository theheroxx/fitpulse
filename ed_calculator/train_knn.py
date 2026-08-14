import pandas as pd
import numpy as np
import joblib
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import RobustScaler
from pathlib import Path
import os

BASE_PATH = Path(__file__).resolve().parent
GNN_DATA_PATH = BASE_PATH / "grid_features.csv"
MODEL_DIR = BASE_PATH / "models"
MODEL_PATH = MODEL_DIR / "knn_cluster_model.pkl"
SCALER_PATH = MODEL_DIR / "knn_scaler.pkl"

FEATURE_COLS = ['temperature_celsius', 'air_quality_PM2.5']

def train_knn():
    print("#" * 30)
    print("Training KNN for Cluster Matching")

    
    if not GNN_DATA_PATH.exists():
        raise FileNotFoundError(f"Data file not found: {GNN_DATA_PATH}")
    
    df = pd.read_csv(GNN_DATA_PATH)
    print(f"Loaded {len(df)} grid points")
    print(f"   Columns: {df.columns.tolist()}")
    
    # Rename columns if needed
    if 'temperature_celsius' not in df.columns and 'temp_mean' in df.columns:
        df['temperature_celsius'] = df['temp_mean']
        print("   Created 'temperature_celsius' from 'temp_mean'")
    
    if 'air_quality_PM2.5' not in df.columns and 'pm25_mean' in df.columns:
        df['air_quality_PM2.5'] = df['pm25_mean']
        print("   Created 'air_quality_PM2.5' from 'pm25_mean'")
    
    # Build cluster from epa_index
    if 'cluster' not in df.columns:
        if 'epa_index' in df.columns:
            df['cluster'] = df['epa_index'].apply(lambda x: min(5, max(0, int(x) - 1)))
            print("   Created 'cluster' from 'epa_index'")
        else:
            df['cluster'] = 0
            print("   No 'cluster' column found, using default (0)")
    
    X = df[FEATURE_COLS].copy()
    y = df['cluster'].copy()
    
    initial_count = len(X)
    X = X.dropna()
    y = y.loc[X.index]
    print(f"After dropping NaN: {len(X)} samples (removed {initial_count - len(X)})")
    print(f"Using features: {FEATURE_COLS}")
    
    # Scale
    scaler = RobustScaler()
    X_scaled = scaler.fit_transform(X)
    print("Data scaled with RobustScaler")
    
    # KNN
    knn = KNeighborsClassifier(n_neighbors=5, weights='distance')
    knn.fit(X_scaled, y)
    print(f"KNN trained with {len(X)} samples, {len(set(y))} clusters")
    
    # Save
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    
    joblib.dump(knn, MODEL_PATH)
    print(f"KNN model saved to: {MODEL_PATH}")
    
    joblib.dump(scaler, SCALER_PATH)
    print(f"Scaler saved to: {SCALER_PATH}")
    
    print("\nModel Info:")
    print(f"   - Training samples: {len(X)}")
    print(f"   - Number of clusters: {len(set(y))}")
    print(f"   - KNN neighbors: {knn.n_neighbors}")
    print(f"   - Feature names: {FEATURE_COLS}")
    print(f"   - Feature means: {X.mean().values}")
    
    return knn, scaler

def load_knn_model():
    if not MODEL_PATH.exists() or not SCALER_PATH.exists():
        print("Model files not found. Training new model...")
        return train_knn()
    
    knn = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    print(f"KNN model loaded from: {MODEL_PATH}")
    print(f"Scaler loaded from: {SCALER_PATH}")
    
    return knn, scaler

def predict_cluster(temp, pm25, knn=None, scaler=None):
    if knn is None or scaler is None:
        knn, scaler = load_knn_model()
    
    input_df = pd.DataFrame(
        [[temp, pm25]], 
        columns=FEATURE_COLS
    )
    input_scaled = scaler.transform(input_df)
    cluster = knn.predict(input_scaled)[0]
    return int(cluster)



if __name__ == "__main__":
    train_knn()


    # Test

    test_cluster = predict_cluster(30, 45)
    print(f"   Temp: 30C, PM2.5: 45 -> Cluster: {test_cluster}")
    
    print("\nMore tests:")
    print(f"   Temp: 15C, PM2.5: 10 -> Cluster: {predict_cluster(15, 10)}")
    print(f"   Temp: 25C, PM2.5: 30 -> Cluster: {predict_cluster(25, 30)}")
    print(f"   Temp: 35C, PM2.5: 80 -> Cluster: {predict_cluster(35, 80)}")