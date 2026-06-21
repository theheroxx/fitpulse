# ui/desktop/widgets/analysis.py
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import QFont, QFontDatabase

from ui.desktop.widgets.onboarding_wizard import OnboardingWizard
from ui.desktop.widgets.input_panel import InputPanel
from ui.desktop.widgets.results_panel import ResultsPanel
from ui.desktop.workers.analysis_worker import AnalysisWorker

from core.orchestrator import PipelineCache
import ollama


class AnalysisWidget(QWidget):
    analysis_completed = Signal(dict)
    
    def __init__(self):
        super().__init__()
        
        # Set a cleaner base font (with fallback)
        font_families = QFontDatabase().families()
        if "Inter" in font_families:
            font = QFont("Inter", 10)
        elif "Segoe UI" in font_families:
            font = QFont("Segoe UI", 10)
        else:
            font = QFont("Arial", 10)
        QApplication.setFont(font)

        self.ollama_client = ollama.Client(host='http://127.0.0.1:11434')
        self.chat_model = "gemma3:4b"
        self.worker = None
        self.current_user_data = None

        self.init_models()
        self.setup_ui()
        self.apply_styles()
        self.check_onboarding()

    def init_models(self):
        try:
            PipelineCache.get_ed_predictor()
            print("✅ Models loaded successfully")
        except Exception as e:
            print(f"⚠️ Model warning: {e}")

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- HEADER BAR ---
        header = QFrame()
        header.setObjectName("headerBar")
        header.setFixedHeight(60)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 0, 24, 0)

        title_label = QLabel("Environmental Health Analysis")
        title_label.setStyleSheet("font-size: 18px; font-weight: 600; color: #1e293b;")
        
        self.profile_btn = QPushButton("👤 Edit Profile")
        self.profile_btn.setCursor(Qt.PointingHandCursor)
        self.profile_btn.setFixedWidth(120)
        self.profile_btn.clicked.connect(self.show_onboarding)
        self.profile_btn.setObjectName("profileButton")

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.profile_btn)
        main_layout.addWidget(header)

        # --- CONTENT AREA ---
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(20, 20, 20, 20)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(12)

        # Left: Input Panel
        self.input_panel = InputPanel()
        self.input_panel.analyze_clicked.connect(self.on_analyze)
        self.splitter.addWidget(self.input_panel)

        # Right: Results Panel
        self.results_panel = ResultsPanel()
        self.splitter.addWidget(self.results_panel)

        self.splitter.setSizes([450, 750])
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)
        
        content_layout.addWidget(self.splitter)
        main_layout.addWidget(content_container, 1)

        # --- FOOTER ---
        footer = QLabel("⚠️ For informational purposes only. Consult a professional medical expert.")
        footer.setObjectName("footer")
        footer.setAlignment(Qt.AlignCenter)
        footer.setFixedHeight(40)
        main_layout.addWidget(footer)

    def apply_styles(self):
        self.setStyleSheet("""
            AnalysisWidget {
                background-color: #f8fafc;
            }
            
            #headerBar {
                background-color: white;
                border-bottom: 1px solid #e2e8f0;
            }

            #profileButton {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 6px 12px;
                color: #64748b;
                font-weight: 500;
            }
            
            #profileButton:hover {
                background-color: #f1f5f9;
                color: #0f172a;
                border-color: #cbd5e1;
            }

            QSplitter::handle {
                background-color: transparent;
            }

            QSplitter::handle:horizontal {
                width: 1px;
                background-color: #e2e8f0;
                margin: 30px 5px;
            }

            #footer {
                background: #ffffff;
                color: #94a3b8;
                font-size: 11px;
                border-top: 1px solid #f1f5f9;
                letter-spacing: 0.5px;
            }
        """)

    # =========================================================
    # ONBOARDING METHODS
    # =========================================================
    
    def on_onboarding_done(self, data):
        """Handle onboarding completion - update input panel safely"""
        if hasattr(self, "input_panel"):
            try:
                # Safely update age
                if hasattr(self.input_panel, "age"):
                    self.input_panel.age.setValue(data.get("Age", 25))
                # Safely update health condition
                if hasattr(self.input_panel, "health"):
                    self.input_panel.health.setCurrentText(data.get("HealthCondition", "Healthy"))
                # Safely update fitness level
                if hasattr(self.input_panel, "fitness"):
                    self.input_panel.fitness.setCurrentText(data.get("FitnessLevel", "Medium"))
            except Exception as e:
                print(f"Error updating input panel: {e}")
        self.current_user_profile = data

    def show_onboarding(self):
        """Show onboarding wizard for editing profile"""
        self.wizard = OnboardingWizard(edit_mode=True)
        self.wizard.finished.connect(self.on_onboarding_done)
        self.wizard.setWindowModality(Qt.ApplicationModal)
        self.wizard.setParent(self, Qt.Window)
        self.wizard.exec()

    def check_onboarding(self):
        """Check if user profile exists, otherwise show onboarding"""
        try:
            from database.db import get_user
            profile = get_user()
        except Exception as e:
            print(f"Error loading profile: {e}")
            profile = None

        if profile:
            self.on_onboarding_done({
                "Age": profile.get("age", 25),
                "HealthCondition": profile.get("health_condition", "Healthy"),
                "FitnessLevel": profile.get("fitness_level", "Medium")
            })
        else:
            self.show_onboarding()

    # =========================================================
    # ANALYSIS METHODS
    # =========================================================
    
    def on_analyze(self, user_data):
        """Handle analyze button click - prepare data for worker"""
        self.current_user_data = user_data
        self.input_panel.analyze_btn.setEnabled(False)
        self.input_panel.analyze_btn.setText("⏳ Analyzing...")
        self.results_panel.show_loading()

        # Prepare worker data with fallbacks for both naming conventions
        worker_data = {
            # Personal info
            "Age": user_data.get("Age", 30),
            "HealthCondition": user_data.get("HealthCondition", "Healthy"),
            "FitnessLevel": user_data.get("FitnessLevel", "Medium"),
            "ActivityType": user_data.get("ActivityType", "Mid Cardio"),
            "DurationMins": user_data.get("DurationMins", 30),
            "TimeOfDay": user_data.get("TimeOfDay", "Morning"),
            "sensitive": user_data.get("sensitive", False),
            
            # Weather data (lowercase with uppercase fallbacks)
            "temp": user_data.get("temp", user_data.get("Temperature", 22)),
            "humid": user_data.get("humid", user_data.get("Humidity", 45)),
            "wind": user_data.get("wind", user_data.get("Wind", 10)),
            "uv": user_data.get("uv", user_data.get("UV", 3)),
            
            # Air quality data (lowercase with uppercase fallbacks)
            "pm25": user_data.get("pm25", user_data.get("PM25", 25)),
            "pm10": user_data.get("pm10", user_data.get("PM10", 45)),
            "co": user_data.get("co", user_data.get("CO", 200)),
            "o3": user_data.get("o3", user_data.get("O3", 40)),
            "no2": user_data.get("no2", user_data.get("NO2", 10)),
            "so2": user_data.get("so2", user_data.get("SO2", 5))
        }

        self.worker = AnalysisWorker(worker_data)
        self.worker.progress.connect(self.on_analysis_progress)
        self.worker.analysis_finished.connect(self.on_analysis_finished)
        self.worker.error.connect(self.on_analysis_error)
        self.worker.start()

        print(f"📥 INPUT PANEL DATA KEYS: {user_data.keys()}")
        print(f"📥 DurationMins = {user_data.get('DurationMins')}")

    def on_analysis_progress(self, msg):
        """Update progress in results panel"""
        self.results_panel.update_status(msg)

    def on_analysis_finished(self, result):
        """Handle analysis completion"""
        try:
            result['user_data'] = self.current_user_data
            self.results_panel.update_results(result)
            self.analysis_completed.emit(result)
        except Exception as e:
            print(f"❌ Error displaying results: {e}")
            import traceback
            traceback.print_exc()
            self.on_analysis_error(f"Display error: {str(e)}")
        finally:
            self.input_panel.analyze_btn.setEnabled(True)
            self.input_panel.analyze_btn.setText("🚀 Analyze")

    def on_analysis_error(self, err):
        """Handle analysis error"""
        self.results_panel.show_error(err)
        self.input_panel.analyze_btn.setEnabled(True)
        self.input_panel.analyze_btn.setText("🚀 Analyze")