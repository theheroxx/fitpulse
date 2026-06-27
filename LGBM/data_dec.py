"""
Synthetic Data Generator for Detector Training
---------------------------------------------
Reads existing 45.csv, handles missing values, generates 50k synthetic rows,
and appends them. Uses CTGAN (or fallback) and preserves correlations.
"""

import pandas as pd
import numpy as np
import os
from sklearn.preprocessing import LabelEncoder
import warnings
warnings.filterwarnings("ignore")

# ============================================================
# 1. LOAD DATA
# ============================================================
input_csv = r"D:\ED\LGBM\45.csv"
output_csv = r"D:\ED\LGBM\45_augmented.csv"

df = pd.read_csv(input_csv)
print(f"Original shape: {df.shape}")

# Drop the 'RuleExplanation' column if present (free text, not useful for ML)
if 'RuleExplanation' in df.columns:
    df = df.drop(columns=['RuleExplanation'])
    print("Dropped 'RuleExplanation' column.")

# Check for missing values
null_counts = df.isnull().sum()
if null_counts.sum() > 0:
    print("Missing values found:")
    print(null_counts[null_counts > 0])
    # Drop rows with any missing values (simplest)
    df = df.dropna()
    print(f"Shape after dropping nulls: {df.shape}")

# Separate features and target (target is 'SafetyLabel')
# We'll treat all columns as features for synthetic generation,
# but we keep SafetyLabel as categorical.

categorical_cols = []
numerical_cols = []
target_col = 'SafetyLabel'

for col in df.columns:
    if df[col].dtype == 'object' or df[col].nunique() < 10:
        categorical_cols.append(col)
    else:
        numerical_cols.append(col)

# Ensure 'SafetyLabel' is categorical
if target_col not in categorical_cols:
    categorical_cols.append(target_col)

print(f"Categorical columns: {categorical_cols}")
print(f"Numerical columns: {numerical_cols}")

# ============================================================
# 2. GENERATE SYNTHETIC DATA
# ============================================================
n_synthetic = 50000

try:
    # ---- Method 1: CTGAN (best) ----
    from ctgan import CTGAN
    print("Using CTGAN for synthetic data generation...")
    
    # Encode categorical columns to integers for CTGAN
    encoders = {}
    df_encoded = df.copy()
    for col in categorical_cols:
        le = LabelEncoder()
        df_encoded[col] = le.fit_transform(df_encoded[col].astype(str))
        encoders[col] = le
    
    # Train CTGAN
    ctgan = CTGAN(epochs=100, batch_size=500, verbose=True)
    ctgan.fit(df_encoded, categorical_cols)
    
    # Generate synthetic samples
    synthetic_encoded = ctgan.sample(n_synthetic)
    
    # Decode categorical columns back to original strings
    for col in categorical_cols:
        synthetic_encoded[col] = encoders[col].inverse_transform(synthetic_encoded[col].astype(int))
    
    synthetic_df = synthetic_encoded
    print("CTGAN generation complete.")
    
except Exception as e:
    print(f"CTGAN failed: {e}")
    print("Falling back to resample+noise method.")
    
    # ---- Method 2: Resample + Gaussian noise (simple) ----
    # Resample rows with replacement
    synthetic_df = df.sample(n=n_synthetic, replace=True, random_state=42).reset_index(drop=True)
    
    # Add small Gaussian noise to numerical columns
    for col in numerical_cols:
        std = df[col].std()
        if std > 0:
            noise = np.random.normal(0, 0.05 * std, size=n_synthetic)   # 5% of std
            synthetic_df[col] = synthetic_df[col] + noise
            # Clip to min/max to keep within original range
            synthetic_df[col] = synthetic_df[col].clip(df[col].min(), df[col].max())
    
    # For categorical columns, randomly flip some values (optional)
    for col in categorical_cols:
        # Keep 95% same, flip 5% randomly (based on original distribution)
        flip_mask = np.random.random(n_synthetic) < 0.05
        if flip_mask.any():
            orig_vals = synthetic_df[col].values
            unique_vals = df[col].unique()
            for i in np.where(flip_mask)[0]:
                choices = [v for v in unique_vals if v != orig_vals[i]]
                if choices:
                    synthetic_df.loc[i, col] = np.random.choice(choices)
    
    print("Resample+noise generation complete.")

# ============================================================
# 3. COMBINE ORIGINAL + SYNTHETIC
# ============================================================
combined = pd.concat([df, synthetic_df], ignore_index=True)
print(f"Combined shape: {combined.shape}")

# ============================================================
# 4. SAVE
# ============================================================
combined.to_csv(output_csv, index=False)
print(f"Saved to {output_csv}")