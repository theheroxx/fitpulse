# quick_start.py
import subprocess
import sys
import os
import time

# Enforce thread environment locks at entry launcher
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

print("=" * 50)
print("🏃 AI Fitness Advisor - Quick Launcher")
print("=" * 50)

print("\n📦 Initializing system (first run may take 20-30 seconds)...")
print("   Subsequent runs will be faster...\n")

start_time = time.time()

# Ensure relative paths resolve relative to this file
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir:
    os.chdir(script_dir)

try:
    # Option 1: Launch using run.py (recommended)
    subprocess.run([sys.executable, "run.py"])
except KeyboardInterrupt:
    print("\n🛑 App terminated by user.")

print(f"\n✅ App closed. Total session time: {time.time() - start_time:.1f} seconds")