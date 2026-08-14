# ui/desktop/workers/rag_worker.py
from PySide6.QtCore import QThread, Signal
import subprocess
import json
import os
import re


class RAGWorker(QThread):
    context_ready = Signal(str)
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, query, health_condition, activity_type):
        super().__init__()
        self.query = query
        self.health = health_condition
        self.activity = activity_type

    def _truncate_doc(self, doc: str, max_chars: int = 400) -> str:
        """Truncate a single document to max_chars at sentence boundary"""
        if len(doc) <= max_chars:
            return doc
        
        truncated = doc[:max_chars]
        last_period = truncated.rfind('.')
        
        if last_period > max_chars * 0.5:
            return truncated[:last_period + 1] + "..."
        else:
            return truncated + "..."

    def _limit_context(self, docs: list, max_docs: int = 3, max_total_chars: int = 2000) -> str:
        """Build limited context from documents"""
        if not docs:
            return ""
        
        # Take only top N documents
        limited_docs = []
        current_length = 0
        
        for doc in docs[:max_docs]:
            # Truncate each document
            truncated = self._truncate_doc(doc, max_chars=400)
            
            # Check if adding this exceeds total limit
            if current_length + len(truncated) > max_total_chars:
                break
            
            limited_docs.append(truncated)
            current_length += len(truncated)
        
        if not limited_docs:
            return ""
        
        context = "\n\n---\n📚 **Medical Context:**\n"
        for i, doc in enumerate(limited_docs, 1):
            context += f"\n[Ref {i}] {doc}\n"
        context += "\n---\n"
        
        return context

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
            
            # Send query (simplified)
            search_query = f"{self.query} {self.activity} {self.health}".strip()
            request = json.dumps({'query': search_query}) + "\n"
            proc.stdin.write(request)
            proc.stdin.flush()
            
            # Read response
            response_line = proc.stdout.readline().strip()
            print(f"[RAGWorker] Response received: {len(response_line)} chars")
            
            if not response_line:
                stderr = proc.stderr.read()
                print(f"[RAGWorker] Stderr: {stderr}")
                self.context_ready.emit("")
            else:
                result = json.loads(response_line)
                docs = result.get('documents', [])
                
                if docs:
                    # LIMIT: max 3 docs, each 400 chars, total 2000 chars
                    context = self._limit_context(docs, max_docs=3, max_total_chars=2000)
                    
                    print(f"[RAGWorker] Context created: {len(context)} chars")
                    print(f"[RAGWorker] Context preview: {context[:200]}...")
                    
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