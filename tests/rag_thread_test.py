# tests/test_rag_thread.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['CHROMA_TELEMETRY'] = 'False'

import time
from PySide6.QtCore import QThread, Signal, QCoreApplication

class TestRAGWorker(QThread):
    done = Signal(str)
    
    def run(self):
        try:
            print("QThread: Importing retriever...")
            from rag.retriever import retrieve_context
            print("QThread: Searching...")
            result = retrieve_context("asthma running safety")
            docs = result.get('documents', [[]])[0]
            print(f"QThread: Found {len(docs)} docs")
            self.done.emit(f"Success: {len(docs)} docs")
        except Exception as e:
            print(f"QThread: ERROR: {e}")
            import traceback
            traceback.print_exc()
            self.done.emit(f"Error: {e}")

# MUST have QApplication before QThread
app = QCoreApplication(sys.argv)

print("Main thread: Starting worker...")
worker = TestRAGWorker()
worker.done.connect(lambda msg: print(f"Signal: {msg}"))
worker.done.connect(app.quit)
worker.start()

print("Main thread: Waiting...")
app.exec()
print("Main thread: Done")