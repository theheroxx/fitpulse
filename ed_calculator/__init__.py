# ed_calculator/__init__.py
"""
ED Calculator Module for FitPulse.

Exports:
    - ExerciseDangerPredictor: Main class for ED prediction (compatible with old interface)
    - compute_ed_baseline: Core scoring function
    - All pollution conversion functions
"""

# Import the new math model
from .math_model import ExerciseDangerMathModel
ExerciseDangerPredictor = ExerciseDangerMathModel

# Also expose the baseline and pollution functions
from .ed_baseline import compute_ed_baseline
from .pollution import *

__all__ = [
    "ExerciseDangerPredictor",     # ← Same name as before
    "ExerciseDangerMathModel",     # ← Also available if needed
    "compute_ed_baseline",
]