# train_lgbm_original_only.py
"""
Train on original 45.csv only (no augmentation) with clean features.
"""
import sys
import os
import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report
import joblib

# Load original data (14k rows)
df = pd.read_csv(r"D:\ED\LGBM\45.csv")  # original, not augmented
print(f"Loaded {len(df)} rows")

# Drop RuleExplanation
if 'RuleExplanation' in df.columns:
    df = df.drop(columns=['RuleExplanation'])

# Target
target = 'SafetyLabel'
if target not in df.columns:
    print("Creating SafetyLabel from ED...")
    def ed_to_label(ed):
        if ed >= 70: return 'Unsafe'
        elif ed >= 40: return 'Moderate'
        else: return 'Safe'
    df[target] = df['ED'].apply(ed_to_label)

label_encoder = LabelEncoder()
y = label_encoder.fit_transform(df[target])
print(f"Target distribution: {dict(zip(label_encoder.classes_, np.bincount(y)))}")

# Features: only those available at prediction time (no RiskScore, no derived categories)
clean_features = [
    'Age', 'DurationMins', 'ED', 'ED_raw',
    'HealthCondition', 'FitnessLevel', 'ActivityType', 'TimeOfDay'
]
clean_features = [f for f in clean_features if f in df.columns]
X = df[clean_features].copy()

# One-hot encode categoricals
cat_cols = ['HealthCondition', 'FitnessLevel', 'ActivityType', 'TimeOfDay']
X = pd.get_dummies(X, columns=cat_cols, drop_first=False)

print(f"Features: {X.columns.tolist()}")

# Train/Test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# LightGBM with conservative parameters
model = lgb.LGBMClassifier(
    n_estimators=200,
    max_depth=5,
    learning_rate=0.05,
    num_leaves=30,
    class_weight='balanced',
    random_state=42,
    verbose=-1
)
model.fit(X_train, y_train, eval_set=[(X_test, y_test)], callbacks=[lgb.early_stopping(20)])

# Evaluate
y_pred = model.predict(X_test)
print(f"\nTest Accuracy: {accuracy_score(y_test, y_pred):.4f}")
print(classification_report(y_test, y_pred, target_names=label_encoder.classes_))

# Save
joblib.dump(model, r"D:\ED\LGBM\detector_lgbm_original.pkl")
joblib.dump(X.columns.tolist(), r"D:\ED\LGBM\lgbm_features_original.pkl")
joblib.dump(label_encoder, r"D:\ED\LGBM\lgbm_label_encoder_original.pkl")
print("Model saved.")