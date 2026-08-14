"""
Predicts cluster_id for new locations based on temperature and PM2.5.
"""
import pandas as pd
import numpy as np
import joblib
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import RobustScaler
from pathlib import Path

BASE_PATH = Path(__file__).resolve().parent
GNN_DATA_PATH = BASE_PATH / "grid_features.csv"
MODEL_DIR = BASE_PATH / "models"
MODEL_PATH = MODEL_DIR / "knn_cluster_model.pkl"
SCALER_PATH = MODEL_DIR / "knn_scaler.pkl"

FEATURE_COLS = ['temperature_celsius', 'air_quality_PM2.5']


def train_knn():
    """Train KNN model for climate cluster matching"""
    print("=" * 60)
    print("Training KNN for Cluster Matching")
    print("=" * 60)
    
    if not GNN_DATA_PATH.exists():
        raise FileNotFoundError(f"Data file not found: {GNN_DATA_PATH}")
    
    df = pd.read_csv(GNN_DATA_PATH)
    print(f"Loaded {len(df)} grid points")
    
    # Rename columns if needed
    if 'temperature_celsius' not in df.columns and 'temp_mean' in df.columns:
        df['temperature_celsius'] = df['temp_mean']
    
    if 'air_quality_PM2.5' not in df.columns and 'pm25_mean' in df.columns:
        df['air_quality_PM2.5'] = df['pm25_mean']
    
    # Build cluster from epa_index
    if 'cluster' not in df.columns:
        if 'epa_index' in df.columns:
            df['cluster'] = df['epa_index'].apply(lambda x: min(5, max(0, int(x) - 1)))
        else:
            df['cluster'] = 0
    
    # Only 2 features
    X = df[FEATURE_COLS].copy()
    y = df['cluster'].copy()
    
    X = X.dropna()
    y = y.loc[X.index]
    
    # Scale
    scaler = RobustScaler()
    X_scaled = scaler.fit_transform(X)
    
    # KNN
    knn = KNeighborsClassifier(n_neighbors=5, weights='distance')
    knn.fit(X_scaled, y)
    
    # Save
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(knn, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    
    print(f"KNN trained with {len(X)} samples, {len(set(y))} clusters")
    return knn, scaler


def load_knn_model():
    """Load KNN model and scaler from file"""
    if not MODEL_PATH.exists() or not SCALER_PATH.exists():
        print("Model files not found. Training new model...")
        return train_knn()
    
    knn = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    return knn, scaler


def predict_cluster(temp, pm25, knn=None, scaler=None):
    """Predict cluster for a sample"""
    if knn is None or scaler is None:
        knn, scaler = load_knn_model()
    
    input_df = pd.DataFrame([[temp, pm25]], columns=FEATURE_COLS)
    input_scaled = scaler.transform(input_df)
    cluster = knn.predict(input_scaled)[0]
    return int(cluster)