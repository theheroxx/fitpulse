# ui/desktop/workers/rag_worker.py
from PySide6.QtCore import QThread, Signal
import subprocess
import json
import os


class RAGWorker(QThread):
    context_ready = Signal(str)
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, query, health_condition, activity_type):
        super().__init__()
        self.query = query
        self.health = health_condition
        self.activity = activity_type

    def run(self):
        proc = None
        try:
            self.progress.emit("🔍 Starting RAG server...")
            
            rag_server = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                "rag", "rag_server.py"
            )
            
            proc = subprocess.Popen(
                ["python", rag_server],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for ready signal
            ready_line = proc.stdout.readline().strip()
            print(f"[RAGWorker] Server: {ready_line}")
            
            if "RAG_SERVER_READY" not in ready_line:
                stderr = proc.stderr.read()
                print(f"[RAGWorker] Stderr: {stderr}")
                self.error.emit(f"RAG server failed to start")
                proc.terminate()
                return
            
            self.progress.emit("🔍 Searching knowledge base...")
            
            # Send query
            search_query = f"{self.query} {self.health} {self.activity} fitness safety"
            request = json.dumps({'query': search_query}) + "\n"
            proc.stdin.write(request)
            proc.stdin.flush()
            
            # Read response
            response_line = proc.stdout.readline().strip()
            print(f"[RAGWorker] Response: {response_line[:200]}")
            
            if not response_line:
                stderr = proc.stderr.read()
                print(f"[RAGWorker] Stderr: {stderr}")
                self.context_ready.emit("")
            else:
                result = json.loads(response_line)
                docs = result.get('documents', [])
                
                if docs:
                    context = "\n\n---\n📚 **Medical Context:**\n" + "\n".join(docs[:8]) + "\n---\n"
                    self.context_ready.emit(context)
                else:
                    self.context_ready.emit("")
            
            proc.terminate()
            proc.wait(timeout=5)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
        finally:
            if proc and proc.poll() is None:
                proc.kill()