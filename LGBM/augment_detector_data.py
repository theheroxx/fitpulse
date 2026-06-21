# augment_detector_data.py

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ed_calculator.ed_engine import ExerciseDangerMathModel
import pandas as pd
from ed_calculator.ed_engine import ExerciseDangerMathModel

# Load your detector dataset (14k rows)
df = pd.read_csv(r"D:\ED\LGBM\45.csv")  # adjust path
# After loading df, print the column names
print("Columns in your dataset:")
print(df.columns.tolist())
# Initialize ED model
ed_model = ExerciseDangerMathModel()

# Store augmented features
augmented = []
for idx, row in df.iterrows():
    res = ed_model.calculate_danger_score(
        PL=row['PM2.5'],
        WD=row['Temperature'],
        humidity=row.get('Humidity'),
        wind_speed=row.get('Wind'),
        uv_index=row.get('UV')
    )
    augmented.append({
        **row.to_dict(),
        'temp_score': res['temperature_score'],
        'pollution_score': res['pollution_score'],
        'interaction_score': res['interaction_score'],
        'wind_modifier': res['wind_modifier'],
        'uv_modifier': res['uv_modifier'],
        'ed_score': res['ED']
    })

aug_df = pd.DataFrame(augmented)
aug_df.to_csv("detector_dataset_augmented.csv", index=False)
print("Augmented dataset saved.")