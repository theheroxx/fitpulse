# clear_vector_db.py
import shutil
import os

chroma_path = "D:\ED\data\chroma_db"

if os.path.exists(chroma_path):
    shutil.rmtree(chroma_path)
    print(f"✅ Deleted {chroma_path}")
else:
    print(f"⚠️ Chroma DB not found at {chroma_path}")