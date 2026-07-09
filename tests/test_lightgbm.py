# test_lgbm.py
import joblib
import os

model_path = r"D:\ED\LGBM\detector_lgbm.pkl"

if os.path.exists(model_path):
    model = joblib.load(model_path)
    print("✅ LightGBM model loaded successfully")
    print(f"   Model type: {type(model)}")
else:
    print(f"❌ Model not found at {model_path}")
    print("   Check the path or train the model first.")