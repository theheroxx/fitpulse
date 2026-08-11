# ui/desktop/workers/chat_worker.py
from PySide6.QtCore import QThread, Signal
from transformer.recommender import generate_recommendation, generate_recommendation_with_rag

class ChatWorker(QThread):
    response_ready = Signal(str)
    error = Signal(str)

    def __init__(self, user_data, detector_output, query, detailed_mode=False, rag_context=None, include_history=False, chat_history=None):
        super().__init__()
        self.user_data = user_data
        self.detector_output = detector_output
        self.query = query
        self.detailed_mode = detailed_mode
        self.rag_context = rag_context
        self.include_history = include_history
        self.chat_history = chat_history or []  # ← List of recent messages

    def run(self):
        try:
            if self.detailed_mode:
                result = generate_recommendation_with_rag(
                    user=self.user_data,
                    detector_output=self.detector_output,
                    query=self.query,
                    rag_context=self.rag_context,
                    include_history=self.include_history,
                    chat_history=self.chat_history  # ← Pass to recommender
                )
            else:
                result = generate_recommendation(
                    user=self.user_data,
                    detector_output=self.detector_output,
                    query=self.query,
                    include_history=self.include_history,
                    chat_history=self.chat_history  # ← Pass to recommender
                )
            self.response_ready.emit(result)
        except Exception as e:
            self.error.emit(str(e))