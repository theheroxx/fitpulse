# ui/desktop/widgets/env_calculator.py
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import *
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from core.orchestrator import calculate_detailed_environmental_risk, get_risk_recommendation

class EnvCalculatorPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Title Section
        title_widget = self.create_title_section()
        main_layout.addWidget(title_widget)
        
        # Input Section (Weather + Air Quality side by side)
        input_widget = self.create_input_section()
        main_layout.addWidget(input_widget)
        
        # Sensitive Checkbox
        self.sensitive = QCheckBox("🩺 Sensitive (Asthma/Elderly)")
        self.sensitive.setStyleSheet("""
            QCheckBox {
                padding: 12px;
                background-color: #fff3cd;
                border-radius: 10px;
                color: #856404;
                font-weight: bold;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox:hover {
                background-color: #ffeaa7;
            }
        """)
        main_layout.addWidget(self.sensitive)
        
        # Calculate Button
        self.calc_btn = QPushButton("🌡️ Calculate Risk Score")
        self.calc_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
                color: white;
                border: none;
                padding: 15px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #5a67d8, stop:1 #6b46a0);
            }
            QPushButton:pressed {

            }
        """)
        self.calc_btn.clicked.connect(self.calculate)
        main_layout.addWidget(self.calc_btn)
        
        # Results Section (initially hidden)
        self.results_widget = QFrame()
        self.results_widget.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 15px;
                padding: 20px;
            }
        """)
        self.results_layout = QVBoxLayout(self.results_widget)
        self.results_label = QLabel("Click 'Calculate' to see results")
        self.results_label.setAlignment(Qt.AlignCenter)
        self.results_label.setStyleSheet("color: #999; font-size: 14px; padding: 40px;")
        self.results_layout.addWidget(self.results_label)
        self.results_widget.hide()
        main_layout.addWidget(self.results_widget)
        
        main_layout.addStretch()
    
    def create_title_section(self):
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 15px;
                padding: 20px;
            }
        """)
        layout = QVBoxLayout(widget)
        
        title = QLabel("🌡️ Detailed Environmental Risk Calculator")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        layout.addWidget(title)
        
        description = QLabel(
            "This calculator uses advanced machine learning to assess environmental risks "
            "based on weather conditions and air quality."
        )
        description.setStyleSheet("color: rgba(255,255,255,0.9); font-size: 13px;")
        description.setWordWrap(True)
        layout.addWidget(description)
        
        return widget
    
    def create_input_section(self):
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 15px;
                padding: 20px;
            }
        """)
        layout = QHBoxLayout(widget)
        layout.setSpacing(20)
        
        # Weather Column
        weather_card = self.create_weather_card()
        layout.addWidget(weather_card)
        
        # Air Quality Column
        air_card = self.create_air_quality_card()
        layout.addWidget(air_card)
        
        return widget
    
    def create_weather_card(self):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #f0f4f8;
                border-radius: 12px;
                padding: 15px;
            }
        """)
        layout = QVBoxLayout(card)
        
        # Header
        header = QLabel("☁️ Weather Conditions")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50; margin-bottom: 15px;")
        layout.addWidget(header)
        
        # Temperature
        temp_widget = self.create_input_row("🌡️ Temperature (°C)", "temp")
        layout.addWidget(temp_widget)
        
        # Humidity
        humid_widget = self.create_slider_row("💧 Humidity (%)", "humid", 0, 100, 45, "%")
        layout.addWidget(humid_widget)
        
        # Wind
        wind_widget = self.create_slider_row("💨 Wind (kph)", "wind", 0, 100, 10, "kph")
        layout.addWidget(wind_widget)
        
        # UV Index
        uv_widget = self.create_slider_row("☀️ UV Index", "uv", 0, 15, 3, "")
        layout.addWidget(uv_widget)
        
        layout.addStretch()
        return card
    
    def create_air_quality_card(self):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #f0f4f8;
                border-radius: 12px;
                padding: 15px;
            }
        """)
        layout = QVBoxLayout(card)
        
        # Header
        header = QLabel("🌫️ Air Quality")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50; margin-bottom: 15px;")
        layout.addWidget(header)
        
        # PM2.5
        pm25_widget = self.create_input_row("🫁 PM2.5", "pm25")
        layout.addWidget(pm25_widget)
        
        # PM10
        pm10_widget = self.create_input_row("🏭 PM10", "pm10")
        layout.addWidget(pm10_widget)
        
        # O3
        o3_widget = self.create_input_row("💨 O3", "o3")
        layout.addWidget(o3_widget)
        
        # NO2
        no2_widget = self.create_input_row("🚗 NO2", "no2")
        layout.addWidget(no2_widget)
        
        # SO2
        so2_widget = self.create_input_row("🏭 SO2", "so2")
        layout.addWidget(so2_widget)
        
        # CO
        co_widget = self.create_input_row("🚙 CO", "co")
        layout.addWidget(co_widget)
        
        layout.addStretch()
        return card
    
    def create_input_row(self, label_text, attr_name):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 5, 0, 5)
        
        label = QLabel(label_text)
        label.setStyleSheet("font-weight: bold; color: #2c3e50; min-width: 100px;")
        layout.addWidget(label)
        
        spinbox = QDoubleSpinBox()
        spinbox.setStyleSheet("""
            QDoubleSpinBox {
                padding: 6px;
                border: 1px solid #d0d5dc;
                border-radius: 6px;
                background-color: white;
            }
            QDoubleSpinBox:focus {
                border: 2px solid #667eea;
            }
        """)
        
        # Set ranges based on attribute
        if attr_name == "pm25":
            spinbox.setRange(0, 500)
            spinbox.setValue(25)
            spinbox.setSuffix(" μg/m³")
        elif attr_name == "pm10":
            spinbox.setRange(0, 500)
            spinbox.setValue(45)
            spinbox.setSuffix(" μg/m³")
        elif attr_name == "o3":
            spinbox.setRange(0, 300)
            spinbox.setValue(40)
            spinbox.setSuffix(" μg/m³")
        elif attr_name == "no2":
            spinbox.setRange(0, 300)
            spinbox.setValue(10)
            spinbox.setSuffix(" μg/m³")
        elif attr_name == "so2":
            spinbox.setRange(0, 300)
            spinbox.setValue(5)
            spinbox.setSuffix(" μg/m³")
        elif attr_name == "co":
            spinbox.setRange(0, 5000)
            spinbox.setValue(200)
            spinbox.setSuffix(" μg/m³")
        elif attr_name == "temp":
            spinbox.setRange(-50, 60)
            spinbox.setValue(22)
            spinbox.setSuffix(" °C")
        
        setattr(self, attr_name, spinbox)
        layout.addWidget(spinbox)
        layout.addStretch()
        
        return widget
    
    def create_slider_row(self, label_text, attr_name, min_val, max_val, default_val, suffix):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 5, 0, 5)
        
        label_layout = QHBoxLayout()
        label = QLabel(label_text)
        label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        label_layout.addWidget(label)
        
        value_label = QLabel(f"{default_val}{suffix}")
        value_label.setStyleSheet("color: #667eea; font-weight: bold; min-width: 50px;")
        label_layout.addStretch()
        label_layout.addWidget(value_label)
        layout.addLayout(label_layout)
        
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: #e0e0e0;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 3px;
            }
        """)
        slider.valueChanged.connect(lambda v: value_label.setText(f"{v}{suffix}"))
        
        setattr(self, attr_name, slider)
        layout.addWidget(slider)
        
        return widget
    
    def calculate(self):
        # Get weather data
        weather_data = {
            "temp": self.temp.value(),
            "humid": self.humid.value(),
            "wind": self.wind.value(),
            "uv": self.uv.value()
        }
        
        # Get air quality data
        air_data = {
            "pm25": self.pm25.value(),
            "pm10": self.pm10.value(),
            "co": self.co.value(),
            "o3": self.o3.value(),
            "no2": self.no2.value(),
            "so2": self.so2.value()
        }
        
        try:
            # Calculate risk
            result = calculate_detailed_environmental_risk(weather_data, air_data)
            score = result["FINAL_SCORE"]
            
            if self.sensitive.isChecked():
                score = min(100, score + 15)
            
            # Show results widget
            self.results_widget.show()
            
            # Clear previous results
            self.clear_results()
            
            # Create results display
            self.display_results(result, score)
            
        except Exception as e:
            self.results_widget.show()
            self.clear_results()
            error_label = QLabel(f"Error: {str(e)}")
            error_label.setStyleSheet("color: #dc3545; padding: 20px;")
            error_label.setAlignment(Qt.AlignCenter)
            self.results_layout.addWidget(error_label)
    
    def clear_results(self):
        # Clear all widgets from results layout
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def display_results(self, result, score):
        # Score Grid
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)
        
        # Risk Score Card
        score_card = self.create_result_card(
            "Risk Score",
            f"{score:.1f}",
            f"Bias: {result.get('BIAS', 0)}",
            score
        )
        grid_layout.addWidget(score_card, 0, 0)
        
        # Status Card
        status_card = self.create_status_card(result['STATUS'], score)
        grid_layout.addWidget(status_card, 0, 1)
        
        # Range Card
        range_card = self.create_result_card(
            "Risk Range",
            result.get('RANGE', 'N/A'),
            "Confidence interval",
            score
        )
        grid_layout.addWidget(range_card, 0, 2)
        
        self.results_layout.addLayout(grid_layout)
        
        # Progress Bar
        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(int(min(score, 100)))
        progress.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 8px;
                text-align: center;
                height: 25px;
                background-color: #e0e0e0;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #28a745, stop:0.5 #ffc107, stop:1 #dc3545);
                border-radius: 8px;
            }
        """)
        self.results_layout.addWidget(progress)
        
        # Recommendation
        recommendation, severity = get_risk_recommendation(score)
        rec_widget = self.create_recommendation_widget(recommendation, severity)
        self.results_layout.addWidget(rec_widget)
        
        # Detailed Breakdown
        expand_btn = QPushButton("📊 Show Detailed Breakdown")
        expand_btn.setCheckable(True)
        expand_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #d0d5dc;
                border-radius: 8px;
                padding: 10px;
                text-align: left;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        expand_btn.clicked.connect(lambda: self.toggle_details(result, expand_btn))
        self.results_layout.addWidget(expand_btn)
    
    def create_result_card(self, title, value, subtitle, score):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                padding: 15px;
            }
        """)
        layout = QVBoxLayout(card)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setStyleSheet("font-size: 28px; font-weight: bold;")
        
        # Color based on score
        if score < 30:
            value_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #28a745;")
        elif score < 50:
            value_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #ffc107;")
        elif score < 70:
            value_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #fd7e14;")
        else:
            value_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #dc3545;")
        
        layout.addWidget(value_label)
        
        subtitle_label = QLabel(subtitle)
        subtitle_label.setStyleSheet("color: #999; font-size: 11px;")
        layout.addWidget(subtitle_label)
        
        return card
    
    def create_status_card(self, status, score):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                padding: 15px;
            }
        """)
        layout = QVBoxLayout(card)
        
        title_label = QLabel("Status")
        title_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(title_label)
        
        status_label = QLabel(status)
        if score < 30:
            status_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #28a745;")
        elif score < 50:
            status_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffc107;")
        elif score < 70:
            status_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #fd7e14;")
        else:
            status_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #dc3545;")
        
        layout.addWidget(status_label)
        
        return card
    
    def create_recommendation_widget(self, recommendation, severity):
        widget = QFrame()
        if severity == "danger":
            widget.setStyleSheet("""
                QFrame {
                    background-color: #f8d7da;
                    border-radius: 10px;
                    padding: 15px;
                    margin-top: 10px;
                }
            """)
        elif severity in ["high", "moderate"]:
            widget.setStyleSheet("""
                QFrame {
                    background-color: #fff3cd;
                    border-radius: 10px;
                    padding: 15px;
                    margin-top: 10px;
                }
            """)
        else:
            widget.setStyleSheet("""
                QFrame {
                    background-color: #d4edda;
                    border-radius: 10px;
                    padding: 15px;
                    margin-top: 10px;
                }
            """)
        
        layout = QVBoxLayout(widget)
        
        label = QLabel(recommendation)
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 13px; font-weight: bold;")
        layout.addWidget(label)
        
        return widget
    
    def toggle_details(self, result, button):
        if button.isChecked():
            import json
            details = QTextEdit()
            details.setText(json.dumps(result, indent=2))
            details.setReadOnly(True)
            details.setMaximumHeight(300)
            details.setStyleSheet("""
                QTextEdit {
                    background-color: #2c3e50;
                    color: #ecf0f1;
                    border-radius: 8px;
                    padding: 10px;
                    font-family: monospace;
                    font-size: 11px;
                }
            """)
            self.results_layout.addWidget(details)
            button.setText("📊 Hide Detailed Breakdown")
            button.details_widget = details
        else:
            if hasattr(button, 'details_widget'):
                button.details_widget.deleteLater()
            button.setText("📊 Show Detailed Breakdown")
