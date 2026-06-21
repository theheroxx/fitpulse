# ui/desktop/widgets/input_panel.py

from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QSequentialAnimationGroup
from PySide6.QtGui import QFont, QColor, QIcon

from database.city import get_all_cities, get_city_weather

class InputPanel(QWidget):
    analyze_clicked = Signal(dict)

    def __init__(self):
        super().__init__()
        self.sections = [] # Keep track of cards for animation
        self.setup_ui()
        
        # Trigger entrance animation after a short delay
        QTimer.singleShot(100, self.animate_entrance)

    def setup_ui(self):
        # --- SCROLL AREA SETUP ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: #f8fafc; }
            QScrollBar:vertical { width: 10px; background: transparent; margin: 0px; }
            QScrollBar::handle:vertical { 
                background: #cbd5e1; border-radius: 5px; min-height: 40px; margin: 2px;
            }
            QScrollBar::handle:vertical:hover { background: #94a3b8; }
            QScrollBar::add-line, QScrollBar::sub-line { height: 0px; }
        """)

        content = QWidget()
        content.setObjectName("content")
        self.main_layout = QVBoxLayout(content)
        self.main_layout.setContentsMargins(32, 32, 32, 32)
        self.main_layout.setSpacing(24)

        # --- HEADER ---
        header_container = QWidget()
        header_vbox = QVBoxLayout(header_container)
        header_vbox.setContentsMargins(0, 0, 0, 10)
        
        title = QLabel("🎯 AI Activity Setup")
        title.setFont(QFont("Inter", 22, QFont.Bold))
        title.setStyleSheet("color: #0f172a;")

        subtitle = QLabel("Configure your profile and environmental metrics.")
        subtitle.setStyleSheet("color: #64748b; font-size: 14px;")

        header_vbox.addWidget(title)
        header_vbox.addWidget(subtitle)
        self.main_layout.addWidget(header_container)

        # --- SECTIONS ---
        self.add_animated_section(self.city_section())
        self.add_animated_section(self.personal_section())
        self.add_animated_section(self.weather_section())
        self.add_animated_section(self.air_section())

        # --- SENSITIVE FLAG ---
        self.sensitive = QCheckBox("⚠️ Sensitive User (Respiratory / High Risk)")
        self.sensitive.setCursor(Qt.PointingHandCursor)
        self.sensitive.setStyleSheet("""
            QCheckBox {
                background: #fff7ed;
                border: 2px solid #ffedd5;
                border-radius: 14px;
                padding: 16px;
                color: #9a3412;
                font-weight: 600;
                font-size: 13px;
            }
            QCheckBox::indicator { width: 22px; height: 22px; border-radius: 6px; }
            QCheckBox:hover { border: 2px solid #fdba74; background: #fffaf5; }
        """)
        self.main_layout.addWidget(self.sensitive)

        # --- ACTION BUTTON ---
        self.analyze_btn = QPushButton("🚀 Start AI Analysis")
        self.analyze_btn.setCursor(Qt.PointingHandCursor)
        self.analyze_btn.setFixedHeight(56)
        self.analyze_btn.setFont(QFont("Inter", 12, QFont.Bold))
        self.analyze_btn.setObjectName("analyzeBtn")
        self.analyze_btn.clicked.connect(self.on_analyze)
        
        self.main_layout.addWidget(self.analyze_btn)
        self.main_layout.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self.apply_styles()

    def add_animated_section(self, widget):
        widget.setGraphicsEffect(QGraphicsOpacityEffect(opacity=0))
        self.sections.append(widget)
        self.main_layout.addWidget(widget)

    def animate_entrance(self):
        """Creates a cascading slide-up and fade-in effect"""
        self.anim_group = QSequentialAnimationGroup()
        
        for i, widget in enumerate(self.sections):
            # Opacity Animation
            opacity_effect = widget.graphicsEffect()
            opacity_anim = QPropertyAnimation(opacity_effect, b"opacity")
            opacity_anim.setDuration(400)
            opacity_anim.setStartValue(0)
            opacity_anim.setEndValue(1)
            opacity_anim.setEasingCurve(QEasingCurve.OutCubic)

            # Slide Animation
            pos_anim = QPropertyAnimation(widget, b"pos")
            pos_anim.setDuration(500)
            start_pos = widget.pos()
            widget.move(start_pos.x(), start_pos.y() + 20)
            pos_anim.setStartValue(widget.pos())
            pos_anim.setEndValue(start_pos)
            pos_anim.setEasingCurve(QEasingCurve.OutBack)
            
            self.anim_group.addAnimation(opacity_anim)
            # We overlap them slightly by adding animations to parallel groups if needed, 
            # but sequential with short durations looks very clean.

        self.anim_group.start()

    # --- UI Components (City, Personal, etc.) ---

    def city_section(self):
        card, layout = self.create_card("📍 Location Control")
        row = QHBoxLayout()
        
        self.city_combo = QComboBox()
        self.city_combo.setFixedHeight(44)
        self.city_combo.currentIndexChanged.connect(self.on_city_selected)

        self.apply_weather_btn = QPushButton("🌍 Sync Data")
        self.apply_weather_btn.setObjectName("syncBtn")
        self.apply_weather_btn.setFixedWidth(120)
        self.apply_weather_btn.setFixedHeight(44)
        self.apply_weather_btn.clicked.connect(self.apply_city_weather)
        self.apply_weather_btn.setEnabled(False)

        row.addWidget(self.city_combo, 1)
        row.addWidget(self.apply_weather_btn)
        layout.addRow(row)
        self.load_cities()
        return card

    def personal_section(self):
        card, form = self.create_card("👤 User Profile")
        self.age = QSpinBox(); self.age.setRange(10, 100); self.age.setValue(25)
        self.health = QComboBox(); self.health.addItems(["Healthy", "Asthma", "Heart Condition", "Diabetes"])
        self.fitness = QComboBox(); self.fitness.addItems(["Low", "Medium", "High"])
        self.activity = QComboBox(); self.activity.addItems(["Low Cardio", "Mid Cardio", "High Cardio", "Strength"])
        self.duration = QSpinBox(); self.duration.setRange(5, 600); self.duration.setValue(30)
        self.time = QComboBox(); self.time.addItems(["Morning", "Afternoon", "Evening", "Night"])

        form.addRow("Age", self.age)
        form.addRow("Health Status", self.health)
        form.addRow("Fitness Level", self.fitness)
        form.addRow("Activity Type", self.activity)
        form.addRow("Duration (min)", self.duration)
        form.addRow("Time of Day", self.time)
        return card

    def weather_section(self):
        card, form = self.create_card("🌤 Atmosphere")
        self.temp, self.temp_label = self.create_slider(-10, 45, 22, "°C")
        self.humid, self.humid_label = self.create_slider(0, 100, 45, "%")
        self.wind, self.wind_label = self.create_slider(0, 100, 10, " km/h")
        self.uv, self.uv_label = self.create_slider(0, 15, 3, " UV")

        form.addRow("Temperature", self.wrap_slider(self.temp, self.temp_label))
        form.addRow("Humidity", self.wrap_slider(self.humid, self.humid_label))
        form.addRow("Wind Speed", self.wrap_slider(self.wind, self.wind_label))
        form.addRow("UV Index", self.wrap_slider(self.uv, self.uv_label))
        return card

    def air_section(self):
        card, form = self.create_card("🌫 Air Quality (AQI)")
        self.pm25 = self.create_double(); self.pm10 = self.create_double()
        self.o3 = self.create_double(); self.no2 = self.create_double()
        self.so2 = self.create_double(); self.co = self.create_double(0, 5000, 200)

        form.addRow("PM 2.5", self.pm25); form.addRow("PM 10", self.pm10)
        form.addRow("Ozone (O3)", self.o3); form.addRow("Nitrogen (NO2)", self.no2)
        form.addRow("Sulfur (SO2)", self.so2); form.addRow("Carbon (CO)", self.co)
        return card

    # --- Helpers & Logic ---

    def create_card(self, title):
        box = QGroupBox(title)
        form = QFormLayout()
        form.setSpacing(18)
        form.setContentsMargins(5, 10, 5, 5)
        form.setLabelAlignment(Qt.AlignLeft)
        box.setLayout(form)
        return box, form

    def create_double(self, min_val=0, max_val=500, default=25):
        spin = QDoubleSpinBox()
        spin.setRange(min_val, max_val); spin.setValue(default); spin.setDecimals(1)
        spin.setFixedHeight(40)
        return spin

    def create_slider(self, min_val, max_val, default, suffix):
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_val, max_val); slider.setValue(default)
        label = QLabel(f"{default}{suffix}")
        label.setMinimumWidth(60)
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label.setStyleSheet("color: #4f46e5; font-weight: 800; font-family: 'Roboto Mono';")
        slider.valueChanged.connect(lambda v: label.setText(f"{v}{suffix}"))
        return slider, label

    def wrap_slider(self, slider, label):
        w = QWidget(); l = QHBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0); l.setSpacing(12)
        l.addWidget(slider); l.addWidget(label)
        return w

    def load_cities(self):
        self.city_combo.addItem("📍 Manual Entry", None)
        try:
            cities = get_all_cities()
            for city in cities: self.city_combo.addItem(f"{city['name']}", city['id'])
        except Exception as e: print(e)

    def on_city_selected(self):
        self.apply_weather_btn.setEnabled(self.city_combo.currentData() is not None)

    def apply_city_weather(self):
        city_id = self.city_combo.currentData()
        if not city_id: return
        try:
            weather = get_city_weather(city_id)
            if weather:
                # Update logic unchanged
                self.temp.setValue(int(weather['temp']))
                self.humid.setValue(int(weather['humidity']))
                self.wind.setValue(int(weather['wind']))
                self.uv.setValue(int(weather['uv']))
                self.pm25.setValue(weather['pm25']); self.pm10.setValue(weather['pm10'])
                self.co.setValue(weather['co']); self.o3.setValue(weather['o3'])
                self.no2.setValue(weather['no2']); self.so2.setValue(weather['so2'])
                
                self.apply_weather_btn.setText("✨ Synced")
                QTimer.singleShot(2000, lambda: self.apply_weather_btn.setText("🌍 Sync Data"))
        except Exception as e: print(e)

    def on_analyze(self):
        data = {
            "Age": self.age.value(),
            "HealthCondition": self.health.currentText(),
            "FitnessLevel": self.fitness.currentText(),
            "ActivityType": self.activity.currentText(),
            "DurationMins": self.duration.value(),
            "TimeOfDay": self.time.currentText(),
            "Temperature": self.temp.value(),
            "Humidity": self.humid.value(),
            "Wind": self.wind.value(),
            "UV": self.uv.value(),
            "PM25": self.pm25.value(),
            "PM10": self.pm10.value(),
            "O3": self.o3.value(),
            "NO2": self.no2.value(),
            "SO2": self.so2.value(),
            "CO": self.co.value(),
            "sensitive": self.sensitive.isChecked(),
            "city_id": self.city_combo.currentData(),
            "city_name": self.city_combo.currentText()
        }
        self.analyze_clicked.emit(data)

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget#content { background: #f8fafc; }
            
            QGroupBox {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 20px;
                padding: 24px;
                margin-top: 20px;
                font-weight: 800;
                color: #1e293b;
                font-size: 14px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 0 10px;
                color: #6366f1;
            }

            QLabel { color: #475569; font-weight: 500; }

            QComboBox, QSpinBox, QDoubleSpinBox {
                background: #f1f5f9;
                border: 2px solid transparent;
                border-radius: 10px;
                padding: 8px 12px;
                color: #0f172a;
            }

            QComboBox:hover, QSpinBox:hover { background: #e2e8f0; }
            QComboBox:focus, QSpinBox:focus { 
                background: white; 
                border: 2px solid #6366f1; 
            }

            QPushButton#syncBtn {
                background: #6366f1;
                color: white;
                border-radius: 10px;
                font-weight: 700;
            }
            
            QPushButton#syncBtn:hover { background: #4f46e5; }
            QPushButton#syncBtn:disabled { background: #cbd5e1; }

            QPushButton#analyzeBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6366f1, stop:1 #a855f7);
                color: white;
                border-radius: 16px;
                margin-top: 10px;
            }
            
            QPushButton#analyzeBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4f46e5, stop:1 #9333ea);
            }

            QSlider::groove:horizontal {
                height: 8px;
                background: #e2e8f0;
                border-radius: 4px;
            }
            
            QSlider::handle:horizontal {
                background: white;
                border: 2px solid #6366f1;
                width: 18px;
                height: 18px;
                margin: -6px 0;
                border-radius: 9px;
            }
        """)