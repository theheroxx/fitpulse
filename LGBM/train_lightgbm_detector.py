# train_lgbm_detector.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import joblib

# Load your detector dataset
df = pd.read_csv(r"D:\ED\LGBM\45.csv")

print("Columns in your dataset:")
print(df.columns.tolist())
print(f"\nTotal rows: {len(df)}")
print(f"ED value range: {df['ED'].min():.1f} - {df['ED'].max():.1f}")

# ============================================================================
# STEP 1: Convert ED float to risk categories
# ============================================================================

def ed_to_risk_category(ed_score):
    """Convert ED float score to risk category"""
    if ed_score >= 80:
        return "Extreme Danger"
    elif ed_score >= 65:
        return "Dangerous"
    elif ed_score >= 45:
        return "Moderate Risk"
    elif ed_score >= 30:
        return "Moderate Safe"
    else:
        return "Safe"

def ed_to_risk_numeric(ed_score):
    """Convert ED to numeric risk level (0-4)"""
    if ed_score >= 80:
        return 4  # Extreme Danger
    elif ed_score >= 65:
        return 3  # Dangerous
    elif ed_score >= 45:
        return 2  # Moderate Risk
    elif ed_score >= 30:
        return 1  # Moderate Safe
    else:
        return 0  # Safe

# Add risk category columns
df['ED_Risk_Category'] = df['ED'].apply(ed_to_risk_category)
df['ED_Risk_Level'] = df['ED'].apply(ed_to_risk_numeric)

print("\nED Risk Category distribution:")
print(df['ED_Risk_Category'].value_counts())

# ============================================================================
# STEP 2: Prepare features for LightGBM
# ============================================================================

# Features to use (all available columns except target and identifiers)
feature_cols = [
    'Age', 
    'DurationMins', 
    'ED',                    # Original ED score
    'ED_raw',                # Raw ED (if available)
    'RiskScore',             # Risk score
    'ED_Risk_Level',         # Categorical ED (0-4)
    'HealthCondition',
    'FitnessLevel', 
    'ActivityType', 
    'TimeOfDay'
]

# Remove any columns that don't exist
feature_cols = [col for col in feature_cols if col in df.columns]

# Target: Use SafetyLabel if available
if 'SafetyLabel' in df.columns:
    y = df['SafetyLabel']
    print(f"\nTarget distribution (SafetyLabel):")
    print(y.value_counts())
else:
    # If no SafetyLabel, create from ED_Risk_Category
    print("\n⚠️ 'SafetyLabel' column not found. Creating from ED_Risk_Category...")
    y = df['ED_Risk_Category']
    print("Target distribution (from ED):")
    print(y.value_counts())

X = df[feature_cols].copy()

# One-hot encode categorical features
categorical_cols = ['HealthCondition', 'FitnessLevel', 'ActivityType', 'TimeOfDay']
existing_cats = [col for col in categorical_cols if col in X.columns]

X = pd.get_dummies(X, columns=existing_cats, drop_first=False)

print(f"\nFinal feature count: {len(X.columns)}")
print(f"Features: {X.columns.tolist()}")

# ============================================================================
# STEP 3: Train LightGBM model
# ============================================================================

# Encode target labels to numeric
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)

# Split data
X_train, X_val, y_train, y_val = train_test_split(
    X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
)

print(f"\nTraining set: {len(X_train)} rows")
print(f"Validation set: {len(X_val)} rows")

# Train LightGBM
model = lgb.LGBMClassifier(
    n_estimators=200,
    max_depth=5,
    learning_rate=0.05,
    class_weight='balanced',
    random_state=42,
    verbose=-1
)

model.fit(
    X_train, y_train,
    eval_set=[(X_val, y_val)],
    eval_metric='multi_logloss',
    callbacks=[lgb.early_stopping(20), lgb.log_evaluation(50)]
)

# ============================================================================
# STEP 4: Save model and artifacts
# ============================================================================

# Save model
joblib.dump(model, r"D:\ED\LGBM\detector_lgbm.pkl")

# Save feature names
joblib.dump(X.columns.tolist(), r"D:\ED\LGBM\lgbm_features.pkl")

# Save label encoder
joblib.dump(label_encoder, r"D:\ED\LGBM\lgbm_label_encoder.pkl")

# Save training metadata
metadata = {
    'feature_cols': feature_cols,
    'categorical_cols': existing_cats,
    'n_features': len(X.columns),
    'n_classes': len(label_encoder.classes_),
    'classes': label_encoder.classes_.tolist()
}
joblib.dump(metadata, r"D:\ED\LGBM\lgbm_metadata.pkl")

print("\n✅ Model saved to D:\ED\LGBM\detector_lgbm.pkl")
print(f"   Classes: {label_encoder.classes_.tolist()}")

# ============================================================================
# STEP 5: Quick validation
# ============================================================================
from sklearn.metrics import classification_report, accuracy_score

y_pred = model.predict(X_val)
y_pred_proba = model.predict_proba(X_val)

print("\n" + "="*50)
print("VALIDATION RESULTS")
print("="*50)
print(f"Accuracy: {accuracy_score(y_val, y_pred):.3f}")
print("\nClassification Report:")
print(classification_report(y_val, y_pred, target_names=label_encoder.classes_))