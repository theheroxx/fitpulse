# ui/desktop/workers/chat_worker.py
from PySide6.QtCore import QThread, Signal
from transformer.recommender import generate_recommendation, generate_recommendation_with_rag

class ChatWorker(QThread):
    response_ready = Signal(str)
    error = Signal(str)

    def __init__(self, user_data, detector_output, query, detailed_mode=False, rag_context=None):
        """
        Parameters:
            user_data: dict with user profile (Age, HealthCondition, FitnessLevel, etc.)
            detector_output: dict with detector results (label, confidence, etc.)
            query: str – user's question or request
            detailed_mode: bool – if True, use RAG context
            rag_context: str – optional medical context from RAG
        """
        super().__init__()
        self.user_data = user_data
        self.detector_output = detector_output
        self.query = query
        self.detailed_mode = detailed_mode
        self.rag_context = rag_context

    def run(self):
        try:
            if self.detailed_mode and self.rag_context:
                result = generate_recommendation_with_rag(
                    user=self.user_data,
                    detector_output=self.detector_output,
                    query=self.query,
                    rag_context=self.rag_context
                )
            else:
                # Standard mode – no RAG
                result = generate_recommendation(
                    user=self.user_data,
                    detector_output=self.detector_output,
                    query=self.query
                )
            self.response_ready.emit(result)
        except Exception as e:
            self.error.emit(str(e))