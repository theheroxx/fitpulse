# ui/desktop/widgets/input_panel.py

from PySide6.QtWidgets import *
from PySide6.QtCore import (
    Qt,
    Signal,
    QTimer,
    QPropertyAnimation,
    QParallelAnimationGroup,
    QEasingCurve,
)
from PySide6.QtGui import QFont, QColor

from database.city import get_all_cities, get_city_weather
from api.weather_api import get_weather_with_fallback

# =================================================================
# DESIGN TOKENS  (shared visual language with results_panel.py)
# =================================================================

BRAND_START = "#2563eb"
BRAND_END = "#7c3aed"
SUCCESS = "#059669"


class InputPanel(QWidget):
    analyze_clicked = Signal(dict)

    def __init__(self):
        super().__init__()
        self.sections = []  # Keep track of cards for the entrance animation
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
        header_row = QHBoxLayout(header_container)
        header_row.setContentsMargins(0, 0, 0, 10)
        header_row.setSpacing(16)

        header_badge = QLabel("🎯")
        header_badge.setObjectName("header_badge")
        header_badge.setFixedSize(48, 48)
        header_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_row.addWidget(header_badge)

        header_text = QVBoxLayout()
        header_text.setSpacing(2)

        title = QLabel("AI Activity Setup")
        title.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #0f172a;")

        subtitle = QLabel("Configure your profile and environmental metrics.")
        subtitle.setStyleSheet("color: #64748b; font-size: 13px;")

        header_text.addWidget(title)
        header_text.addWidget(subtitle)
        header_row.addLayout(header_text)
        header_row.addStretch()

        self.main_layout.addWidget(header_container)

        # --- SECTIONS ---
        self.add_animated_section(self.city_section())
        self.add_animated_section(self.personal_section())
        self.add_animated_section(self.weather_section())
        self.add_animated_section(self.air_section())

        # --- SENSITIVE FLAG ---
        self.sensitive = QCheckBox("⚠️ Sensitive User (Respiratory / High Risk)")
        self.sensitive.setObjectName("sensitive_checkbox")
        self.sensitive.setCursor(Qt.CursorShape.PointingHandCursor)
        self.main_layout.addWidget(self.sensitive)

        # --- ACTION BUTTON ---
        self.analyze_btn = QPushButton("🚀 Start AI Analysis")
        self.analyze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.analyze_btn.setFixedHeight(56)
        self.analyze_btn.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        self.analyze_btn.setObjectName("analyzeBtn")
        self.analyze_btn.clicked.connect(self.on_analyze)

        btn_shadow = QGraphicsDropShadowEffect()
        btn_shadow.setBlurRadius(30)
        btn_shadow.setOffset(0, 8)
        btn_shadow.setColor(QColor(37, 99, 235, 90))
        self.analyze_btn.setGraphicsEffect(btn_shadow)

        self.main_layout.addWidget(self.analyze_btn)
        self.main_layout.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self.apply_styles()

    def add_animated_section(self, widget):
        # pyrefly: ignore [unexpected-keyword]
        widget.setGraphicsEffect(QGraphicsOpacityEffect(opacity=0))
        self.sections.append(widget)
        self.main_layout.addWidget(widget)

    def animate_entrance(self):
        """Cascading slide-up + fade-in for each section card."""
        self._entrance_groups = []

        for i, widget in enumerate(self.sections):
            opacity_effect = widget.graphicsEffect()
            opacity_anim = QPropertyAnimation(opacity_effect, b"opacity")
            opacity_anim.setDuration(420)
            opacity_anim.setStartValue(0)
            opacity_anim.setEndValue(1)
            opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

            start_pos = widget.pos()
            widget.move(start_pos.x(), start_pos.y() + 18)
            pos_anim = QPropertyAnimation(widget, b"pos")
            pos_anim.setDuration(480)
            pos_anim.setStartValue(widget.pos())
            pos_anim.setEndValue(start_pos)
            pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

            group = QParallelAnimationGroup()
            group.addAnimation(opacity_anim)
            group.addAnimation(pos_anim)
            self._entrance_groups.append(group)

            QTimer.singleShot(i * 70, group.start)

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
        self.apply_weather_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
        self.age.setSuffix(" yrs")
        self.health = QComboBox(); self.health.addItems(["Healthy", "Asthma", "Heart Condition", "Diabetes"])
        self.fitness = QComboBox(); self.fitness.addItems(["Low", "Medium", "High"])
        self.activity = QComboBox(); self.activity.addItems(["Low Cardio", "Mid Cardio", "High Cardio", "Strength"])
        self.duration = QSpinBox(); self.duration.setRange(5, 600); self.duration.setValue(30)
        self.duration.setSuffix(" min")
        self.time = QComboBox(); self.time.addItems(["Morning", "Afternoon", "Evening", "Night"])

        for combo in (self.health, self.fitness, self.activity, self.time):
            combo.setCursor(Qt.CursorShape.PointingHandCursor)

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
        unit = " µg/m³"
        self.pm25 = self.create_double(0, 500, 25, unit)
        self.pm10 = self.create_double(0, 500, 25, unit)
        self.o3 = self.create_double(0, 500, 25, unit)
        self.no2 = self.create_double(0, 500, 25, unit)
        self.so2 = self.create_double(0, 500, 25, unit)
        self.co = self.create_double(0, 5000, 200, unit)

        form.addRow("PM 2.5", self.pm25); form.addRow("PM 10", self.pm10)
        form.addRow("Ozone (O3)", self.o3); form.addRow("Nitrogen (NO2)", self.no2)
        form.addRow("Sulfur (SO2)", self.so2); form.addRow("Carbon (CO)", self.co)
        return card

    # --- Helpers & Logic ---

    def create_card(self, title):
        """Build a section card with an icon badge + title header and a form body.

        `title` is expected as "<emoji> <label>" (e.g. "📍 Location Control");
        the emoji becomes the badge icon and the remainder becomes the heading.
        """
        icon, _, label_text = title.partition(" ")
        if not label_text:
            icon, label_text = "•", title

        card = QFrame()
        card.setObjectName("section_card")

        outer = QVBoxLayout(card)
        outer.setContentsMargins(24, 20, 24, 22)
        outer.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(12)

        badge = QLabel(icon)
        badge.setObjectName("section_badge")
        badge.setFixedSize(34, 34)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(badge)

        heading = QLabel(label_text)
        heading.setObjectName("section_card_title")
        header.addWidget(heading)
        header.addStretch()

        outer.addLayout(header)

        form = QFormLayout()
        form.setSpacing(16)
        form.setContentsMargins(0, 0, 0, 0)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        outer.addLayout(form)

        return card, form

    def create_double(self, min_val=0, max_val=500, default=25, suffix=""):
        spin = QDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        spin.setDecimals(1)
        spin.setFixedHeight(40)
        if suffix:
            spin.setSuffix(suffix)
        return spin

    def create_slider(self, min_val, max_val, default, suffix):
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default)

        label = QLabel(f"{default}{suffix}")
        label.setObjectName("slider_value")
        label.setMinimumWidth(64)
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        slider.valueChanged.connect(lambda v: label.setText(f"{v}{suffix}"))

        return slider, label

    def wrap_slider(self, slider, label):
        container = QWidget()
        outer = QVBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 2)
        outer.setSpacing(4)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        row.addWidget(slider, 1)
        row.addWidget(label)
        outer.addLayout(row)

        hint_row = QHBoxLayout()
        hint_row.setContentsMargins(0, 0, 0, 0)
        min_label = QLabel(str(slider.minimum()))
        min_label.setObjectName("range_hint")
        max_label = QLabel(str(slider.maximum()))
        max_label.setObjectName("range_hint")
        hint_row.addWidget(min_label)
        hint_row.addStretch()
        hint_row.addWidget(max_label)
        outer.addLayout(hint_row)

        return container

    def load_cities(self):
        self.city_combo.addItem("📍 Manual Entry", None)
        try:
            cities = get_all_cities()
            for city in cities:
                self.city_combo.addItem(f"{city['name']}", city['id'])
        except Exception as e:
            print(e)

    def on_city_selected(self):
        self.apply_weather_btn.setEnabled(self.city_combo.currentData() is not None)

    def apply_city_weather(self):
        city_name = self.city_combo.currentText()
        # Skip if it's the manual entry placeholder
        if city_name.startswith("📍") or not city_name.strip():
            QMessageBox.information(self, "No City", "Please select a city from the list.")
            return

        # Attempt to fetch live weather
        try:
            weather = get_weather_with_fallback(city_name)
            # On success, populate fields
            self.temp.setValue(int(weather["temperature"]))
            self.humid.setValue(int(weather["humidity"]))
            self.wind.setValue(int(weather["wind_kph"]))
            self.uv.setValue(int(weather["uv"]))
            self.pm25.setValue(float(weather["pm25"]))
            self.pm10.setValue(float(weather["pm10"]))
            self.co.setValue(float(weather["co"]))
            self.o3.setValue(float(weather["o3"]))
            self.no2.setValue(float(weather["no2"]))
            self.so2.setValue(float(weather["so2"]))
            self.apply_weather_btn.setText("✅ Synced")
            self._set_sync_state(True)
            QTimer.singleShot(2000, self._reset_sync_button)
        except Exception as e:
            # Fallback already handled inside get_weather_with_fallback
            QMessageBox.warning(
                self,
                "API Error",
                f"Could not fetch weather for '{city_name}'.\n"
                "Using default values (22°C, 45% humidity, etc.).\n\n"
                f"Error: {e}"
            )
            # The fallback values are already set by the function, but we reset to defaults anyway
            self._set_default_weather()
            self.apply_weather_btn.setText("⚠️ Fallback")
            QTimer.singleShot(2000, self._reset_sync_button)

    def _set_default_weather(self):
        """Set all fields to sensible default values."""
        self.temp.setValue(22)
        self.humid.setValue(45)
        self.wind.setValue(10)
        self.uv.setValue(3)
        self.pm25.setValue(25)
        self.pm10.setValue(45)
        self.co.setValue(200)
        self.o3.setValue(40)
        self.no2.setValue(10)
        self.so2.setValue(5)

    def _reset_sync_button(self):
        self.apply_weather_btn.setText("🌍 Sync Data")
        self._set_sync_state(False)

    def _set_sync_state(self, synced: bool):
        self.apply_weather_btn.setProperty("state", "synced" if synced else "")
        self.apply_weather_btn.style().unpolish(self.apply_weather_btn)
        self.apply_weather_btn.style().polish(self.apply_weather_btn)

    def on_analyze(self):
        # Get city data
        city_id = self.city_combo.currentData()
        city_text = self.city_combo.currentText()
        
        # If no city selected or it's the placeholder, use "Manual Entry"
        if city_id is None or city_text.startswith("📍"):
            city_name = "Manual Entry"
        else:
            city_name = city_text

        # Clamp values to ensure they stay within valid ranges
        temp = max(-10, min(45, self.temp.value()))
        humid = max(0, min(100, self.humid.value()))
        wind = max(0, min(100, self.wind.value()))
        uv = max(0, min(15, self.uv.value()))
        
        # PM values clamped to 0-500 (or 0-5000 for CO)
        pm25 = max(0, min(500, self.pm25.value()))
        pm10 = max(0, min(500, self.pm10.value()))
        o3 = max(0, min(500, self.o3.value()))
        no2 = max(0, min(500, self.no2.value()))
        so2 = max(0, min(500, self.so2.value()))
        co = max(0, min(5000, self.co.value()))

        data = {
            "Age": self.age.value(),
            "HealthCondition": self.health.currentText(),
            "FitnessLevel": self.fitness.currentText(),
            "ActivityType": self.activity.currentText(),
            "DurationMins": self.duration.value(),
            "TimeOfDay": self.time.currentText(),
            "Temperature": temp,
            "Humidity": humid,
            "Wind": wind,
            "UV": uv,
            "PM25": pm25,
            "PM10": pm10,
            "O3": o3,
            "NO2": no2,
            "SO2": so2,
            "CO": co,
            "sensitive": self.sensitive.isChecked(),
            "city_id": city_id,
            "city_name": city_name
        }
        self.analyze_clicked.emit(data)

    def apply_styles(self):
        self.setStyleSheet(f"""
            QWidget {{
                font-family: "Segoe UI", "SF Pro Display", "Helvetica Neue", Arial, sans-serif;
            }}

            QWidget#content {{ background: #f8fafc; }}

            /* ============================================
               HEADER
            ============================================ */

            QLabel#header_badge {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {BRAND_START}, stop:1 {BRAND_END});
                border-radius: 24px;
                font-size: 20px;
                color: white;
            }}

            /* ============================================
               SECTION CARDS
            ============================================ */

            QFrame#section_card {{
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 20px;
            }}

            QFrame#section_card:hover {{
                border: 1px solid #c7d2fe;
            }}

            QLabel#section_badge {{
                background: #eef2ff;
                border-radius: 17px;
                font-size: 15px;
            }}

            QLabel#section_card_title {{
                font-weight: 800;
                font-size: 14px;
                color: #1e293b;
            }}

            QLabel {{ color: #475569; font-weight: 500; }}

            /* ============================================
               INPUTS
            ============================================ */

            QComboBox, QSpinBox, QDoubleSpinBox {{
                background: #f1f5f9;
                border: 2px solid transparent;
                border-radius: 10px;
                padding: 8px 12px;
                color: #0f172a;
            }}

            QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{ background: #e2e8f0; }}

            QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
                background: white;
                border: 2px solid {BRAND_START};
            }}

            QComboBox::drop-down {{
                border: none;
                width: 26px;
            }}

            QComboBox QAbstractItemView {{
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                selection-background-color: #eef2ff;
                selection-color: {BRAND_START};
                padding: 4px;
            }}

            /* ============================================
               SLIDERS
            ============================================ */

            QLabel#slider_value {{
                color: {BRAND_START};
                font-weight: 800;
                font-family: 'Roboto Mono', 'Consolas', monospace;
            }}

            QLabel#range_hint {{
                color: #94a3b8;
                font-size: 11px;
                font-weight: 600;
            }}

            QSlider::groove:horizontal {{
                height: 8px;
                background: #e2e8f0;
                border-radius: 4px;
            }}

            QSlider::sub-page:horizontal {{
                height: 8px;
                border-radius: 4px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {BRAND_START}, stop:1 {BRAND_END});
            }}

            QSlider::handle:horizontal {{
                background: white;
                border: 2px solid {BRAND_START};
                width: 18px;
                height: 18px;
                margin: -6px 0;
                border-radius: 9px;
            }}

            QSlider::handle:horizontal:hover {{
                border: 2px solid {BRAND_END};
            }}

            /* ============================================
               SENSITIVE FLAG
            ============================================ */

            QCheckBox#sensitive_checkbox {{
                background: #fff7ed;
                border: 2px solid #ffedd5;
                border-radius: 14px;
                padding: 16px;
                color: #9a3412;
                font-weight: 600;
                font-size: 13px;
            }}

            QCheckBox#sensitive_checkbox::indicator {{
                width: 22px;
                height: 22px;
                border-radius: 6px;
            }}

            QCheckBox#sensitive_checkbox:hover {{
                border: 2px solid #fdba74;
                background: #fffaf5;
            }}

            /* ============================================
               BUTTONS
            ============================================ */

            QPushButton#syncBtn {{
                background: {BRAND_START};
                color: white;
                border: none;
                border-radius: 10px;
                font-weight: 700;
            }}

            QPushButton#syncBtn:hover {{ background: {BRAND_END}; }}
            QPushButton#syncBtn:disabled {{ background: #cbd5e1; }}
            QPushButton#syncBtn[state="synced"] {{ background: {SUCCESS}; }}

            QPushButton#analyzeBtn {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {BRAND_START}, stop:1 {BRAND_END});
                color: white;
                border: none;
                border-radius: 16px;
                margin-top: 10px;
            }}

            QPushButton#analyzeBtn:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1d4ed8, stop:1 #6d28d9);
            }}

            QPushButton#analyzeBtn:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1e40af, stop:1 #5b21b6);
            }}
        """)