# quick_start.py
import subprocess
import sys
import os
import time

print("=" * 50)
print("🏃 AI Fitness Advisor - Quick Launcher")
print("=" * 50)

# Pre-load models in background
print("\n📦 Pre-loading models (first run may take 20-30 seconds)...")
print("   Subsequent runs will be faster...")
print("")

start_time = time.time()

# Launch app from the new entry point (run.py or main_container)
os.chdir(os.path.dirname(__file__))

# Option 1: Launch using run.py (recommended)
subprocess.run([sys.executable, "run.py"])

# Option 2: Launch using main_container directly (alternative)
# subprocess.run([sys.executable, "-m", "ui.desktop.main_container"])

# Option 3: Launch using home.py directly (for testing only)
#subprocess.run([sys.executable, "-m", "ui.desktop.home"])

print(f"\n✅ App closed. Total time: {time.time() - start_time:.1f} seconds")