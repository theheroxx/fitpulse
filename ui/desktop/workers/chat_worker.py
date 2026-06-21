# ui/desktop/workers/chat_worker.py
from PySide6.QtCore import QThread, Signal
import ollama

class ChatWorker(QThread):
    response_ready = Signal(str)
    error = Signal(str)
    
    def __init__(self, prompt, model):
        super().__init__()
        self.prompt = prompt
        self.model = model
    
    def run(self):
        try:
            client = ollama.Client(host='http://127.0.0.1:11434')
            response = client.generate(
                model=self.model,
                prompt=self.prompt,
                options={'temperature': 0.7, 'max_tokens': 500}
            )
            self.response_ready.emit(response['response'].strip())
        except Exception as e:
            self.error.emit(str(e))