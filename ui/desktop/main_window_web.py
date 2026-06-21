# ui/desktop/main_window_web.py
# ========== ADD THIS FIRST - BEFORE ANY OTHER IMPORTS ==========
import os
import sys

# Add QtWebEngine binaries to PATH
pyside_path = os.path.join(sys.prefix, "Lib", "site-packages", "PySide6")
qt_bin_path = os.path.join(pyside_path, "Qt", "bin")
if os.path.exists(qt_bin_path):
    os.environ["PATH"] = qt_bin_path + os.pathsep + os.environ.get("PATH", "")
# ================================================================

# Now your regular imports
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

from ui.desktop.widgets.input_panel import InputPanel
from ui.desktop.workers.analysis_worker import AnalysisWorker
from core.orchestrator import PipelineCache
import ollama
import json


class Bridge(QObject):
    """Bridge for Python-JavaScript communication"""
    def __init__(self):
        super().__init__()
        self.callback = None
        self.view = None
    
    @Slot(str)
    def fromJS(self, message):
        if self.callback:
            self.callback(message)
    
    def sendToJS(self, data):
        if self.view:
            self.view.page().runJavaScript(f"window.receiveFromPython({json.dumps(data)})")


class MainWindowWeb(QMainWindow):  # ← CLASS NAME MUST MATCH
    def __init__(self):
        super().__init__()
        QApplication.setFont(QFont("Segoe UI", 9))
        
        self.setWindowTitle("AI Fitness Advisor")
        self.setMinimumSize(1300, 850)
        self.resize(1400, 880)
        
        self.chat_model = "gemma3:4b"
        self.worker = None
        self.current_user_data = None
        
        # Get web base path
        self.web_base_path = os.path.join(os.path.dirname(__file__), "web")
        
        self.init_models()
        self.setup_ui()
        self.apply_styles()
    
    def init_models(self):
        try:
            PipelineCache.get_ed_predictor()
            print("✅ Models loaded")
        except Exception as e:
            print(f"⚠️ Model warning: {e}")
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create tabs
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background: #f1f5f9; }
            QTabBar::tab { padding: 12px 24px; font-size: 13px; font-weight: 500; }
            QTabBar::tab:selected { background: white; color: #4f46e5; }
        """)
        
        # Tab 1: Analysis
        analysis_tab = self.create_analysis_tab()
        tabs.addTab(analysis_tab, "🏃 Analysis")
        
        # Tab 2: Chat
        chat_tab = self.create_chat_tab()
        tabs.addTab(chat_tab, "💬 Chat")
        
        layout.addWidget(tabs)
    
    def create_analysis_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # LEFT: Native Qt input
        self.input_panel = InputPanel()
        self.input_panel.analyze_clicked.connect(self.on_analyze)
        
        # RIGHT: Web results
        self.web_results = QWebEngineView()
        results_path = os.path.join(self.web_base_path, "templates", "results.html")
        if os.path.exists(results_path):
            self.web_results.setUrl(QUrl.fromLocalFile(results_path))
        else:
            self.web_results.setHtml("<h1>Results page not found</h1>")
        
        # Setup bridge
        self.results_bridge = Bridge()
        channel = QWebChannel()
        channel.registerObject("bridge", self.results_bridge)
        self.web_results.page().setWebChannel(channel)
        self.results_bridge.view = self.web_results
        
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.input_panel)
        splitter.addWidget(self.web_results)
        splitter.setSizes([450, 750])
        
        layout.addWidget(splitter)
        return widget
    
    def create_chat_tab(self):
        web_chat = QWebEngineView()
        chat_path = os.path.join(self.web_base_path, "templates", "chat.html")
        if os.path.exists(chat_path):
            web_chat.setUrl(QUrl.fromLocalFile(chat_path))
        else:
            web_chat.setHtml("<h1>Chat page not found</h1>")
        
        # Setup bridge for chat
        self.chat_bridge = Bridge()
        channel = QWebChannel()
        channel.registerObject("bridge", self.chat_bridge)
        web_chat.page().setWebChannel(channel)
        self.chat_bridge.view = web_chat
        self.chat_bridge.callback = self.on_chat_message
        
        return web_chat
    
    def on_analyze(self, user_data):
        self.current_user_data = user_data
        self.input_panel.analyze_btn.setEnabled(False)
        self.input_panel.analyze_btn.setText("⏳ Analyzing...")
        
        self.worker = AnalysisWorker(user_data)
        self.worker.analysis_finished.connect(self.on_analysis_finished)
        self.worker.error.connect(self.on_analysis_error)
        self.worker.start()
    
    def on_analysis_finished(self, result):
        result['user_data'] = self.current_user_data
        
        web_data = {
            "ed": result.get("ED", 0),
            "status": result.get("detector", {}).get("label", "Unknown"),
            "confidence": result.get("detector", {}).get("confidence", 0),
            "pollution": result.get("ml_result", {}).get("components", {}).get("pollution", 0),
            "weather": result.get("ml_result", {}).get("components", {}).get("heat", 0),
            "recommendations": result.get("ed_recommendations", [])
        }
        
        self.results_bridge.sendToJS(web_data)
        
        self.input_panel.analyze_btn.setEnabled(True)
        self.input_panel.analyze_btn.setText("🚀 Analyze")
    
    def on_analysis_error(self, err):
        self.input_panel.analyze_btn.setEnabled(True)
        self.input_panel.analyze_btn.setText("🚀 Analyze")
    
    def on_chat_message(self, message):
        try:
            client = ollama.Client()
            response = client.generate(
                model=self.chat_model,
                prompt=message,
                options={'temperature': 0.7, 'max_tokens': 500}
            )
            self.chat_bridge.sendToJS(response['response'].strip())
        except Exception as e:
            self.chat_bridge.sendToJS(f"Error: {e}")
    
    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f1f5f9;
            }
            QSplitter::handle {
                background-color: #e2e8f0;
                margin: 20px 0;
            }
        """)