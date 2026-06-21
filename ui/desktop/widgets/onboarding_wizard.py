# ui/desktop/widgets/onboarding_wizard.py
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import QFont, QColor


class OnboardingWizard(QDialog):
    finished = Signal(dict)

    def __init__(self, edit_mode=False):
        super().__init__()

        self.setWindowTitle("Edit Profile" if edit_mode else "Welcome")
        self.setFixedSize(520, 460)

        self.edit_mode = edit_mode
        self.data = {}
        self.step_index = 0

        self.stack = QStackedWidget()

        self.steps = [
            self.step_age(),
            self.step_health(),
            self.step_city(),
            self.step_fitness(),
            self.step_done()
        ]

        for s in self.steps:
            self.stack.addWidget(s)

        # Load existing profile if in edit mode
        if edit_mode:
            self.load_existing_profile()

        # === Layout ===
        main = QVBoxLayout(self)

        self.progress = QLabel("Step 1 of 5")
        self.progress.setAlignment(Qt.AlignCenter)
        self.progress.setObjectName("progress")

        main.addWidget(self.progress)
        main.addWidget(self.stack)

        # nav
        nav = QHBoxLayout()

        self.back_btn = QPushButton("← Back")
        self.next_btn = QPushButton("Next →")

        self.back_btn.clicked.connect(self.prev_step)
        self.next_btn.clicked.connect(self.next_step)

        nav.addWidget(self.back_btn)
        nav.addStretch()
        nav.addWidget(self.next_btn)

        main.addLayout(nav)

        self.update_ui()
        self.apply_styles()

    # ================= Load Existing Profile =================

    def load_existing_profile(self):
        """Load existing user data for edit mode"""
        try:
            from database.db import load_profile
            profile = load_profile()
            
            if profile:
                self.existing_data = profile
                # Pre-fill values (will be applied when reaching each step)
                self.has_existing = True
            else:
                self.has_existing = False
        except Exception as e:
            print(f"Error loading profile: {e}")
            self.has_existing = False

    # ================= Steps =================

    def step_age(self):
        self.age = QSpinBox()
        self.age.setRange(10, 100)
        self.age.setValue(25)
        self.age.setAlignment(Qt.AlignCenter)
        return self.build_step("How old are you?", self.age)

    def step_health(self):
        self.health = QComboBox()
        self.health.addItems(["Healthy", "Asthma", "Heart Condition", "Diabetes"])
        return self.build_step("Any health conditions?", self.health)

    def step_city(self):
        self.city = QComboBox()
        
        # Load cities from database
        try:
            from database.city import get_all_cities
            
            cities = get_all_cities()
            
            # Store city data (name -> id) for later retrieval
            self.city_data = {}  # name -> id
            for city in cities:
                city_name = city["name"]
                city_id = city["id"]
                self.city_data[city_name] = city_id
                self.city.addItem(city_name)
        except Exception as e:
            print(f"Error loading cities: {e}")
            # Fallback cities
            fallback_cities = ["Tehran", "Mashhad", "Isfahan", "Shiraz", "Tabriz", "Karaj", "Yazd"]
            self.city_data = {city: i+1 for i, city in enumerate(fallback_cities)}
            self.city.addItems(fallback_cities)
        
        self.city.setCurrentIndex(0)
        
        # Pre-select city if in edit mode and city exists
        if hasattr(self, 'has_existing') and self.has_existing:
            city_name = self.existing_data.get("City")
            if city_name:
                index = self.city.findText(city_name)
                if index >= 0:
                    self.city.setCurrentIndex(index)
        
        return self.build_step("Which city are you in?", self.city)

    def step_fitness(self):
        self.fitness = QComboBox()
        self.fitness.addItems(["Low", "Medium", "High"])
        return self.build_step("Your fitness level?", self.fitness)

    def step_done(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        title_text = "🎉 Profile Updated!" if self.edit_mode else "🎉 You're ready!"
        title = QLabel(title_text)
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))

        btn_text = "Start Using App" if not self.edit_mode else "Save Changes"
        btn = QPushButton(btn_text)
        btn.clicked.connect(self.finish)

        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(btn)
        layout.addStretch()

        return w

    # ================= Step Builder =================

    def build_step(self, title, widget):
        w = QWidget()
        layout = QVBoxLayout(w)

        title_lbl = QLabel(title)
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setFont(QFont("Segoe UI", 14, QFont.Bold))

        layout.addStretch()
        layout.addWidget(title_lbl)
        layout.addSpacing(20)
        layout.addWidget(widget)
        layout.addStretch()

        return w

    # ================= Navigation =================

    def next_step(self):
        self.collect_data()

        if self.step_index < len(self.steps) - 1:
            self.step_index += 1
            self.stack.setCurrentIndex(self.step_index)
            self.update_ui()

            # Apply pre-filled values when entering a step
            self.apply_prefilled_values()

    def prev_step(self):
        if self.step_index > 0:
            self.step_index -= 1
            self.stack.setCurrentIndex(self.step_index)
            self.update_ui()

    def update_ui(self):
        total = len(self.steps)
        self.progress.setText(f"Step {self.step_index + 1} of {total}")

        self.back_btn.setVisible(self.step_index > 0)
        self.next_btn.setVisible(self.step_index < total - 1)

    # ================= Apply Pre-filled Values =================

    def apply_prefilled_values(self):
        """Apply existing profile data when entering a step"""
        if not hasattr(self, 'has_existing') or not self.has_existing:
            return

        if self.step_index == 0:  # Age step
            age = self.existing_data.get("Age")
            if age:
                self.age.setValue(age)
        elif self.step_index == 1:  # Health step
            health = self.existing_data.get("HealthCondition")
            if health:
                index = self.health.findText(health)
                if index >= 0:
                    self.health.setCurrentIndex(index)
        elif self.step_index == 2:  # City step (already handled in step creation)
            pass
        elif self.step_index == 3:  # Fitness step
            fitness = self.existing_data.get("FitnessLevel")
            if fitness:
                index = self.fitness.findText(fitness)
                if index >= 0:
                    self.fitness.setCurrentIndex(index)

    # ================= Data =================

    def collect_data(self):
        if self.step_index == 0:
            self.data["Age"] = self.age.value()
        elif self.step_index == 1:
            self.data["HealthCondition"] = self.health.currentText()
        elif self.step_index == 2:
            # Store city_id for database
            city_name = self.city.currentText()
            if hasattr(self, 'city_data') and city_name in self.city_data:
                self.data["city_id"] = self.city_data[city_name]
                self.data["City"] = city_name
        elif self.step_index == 3:
            self.data["FitnessLevel"] = self.fitness.currentText()

    def finish(self):
        # Save to database
        try:
            if self.edit_mode:
                from core.user_profile import update_profile
                update_profile(self.data)
                print("✅ Profile updated successfully")
            else:
                from core.user_profile import save_profile
                save_profile(self.data)
                print("✅ Profile saved successfully")
        except Exception as e:
            print(f"Error saving profile: {e}")
        
        self.finished.emit(self.data)
        self.close()

    # ================= Style =================

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background: white;
            }

            QLabel {
                color: #0f172a;
            }

            QLabel#progress {
                font-size: 12px;
                color: #64748b;
                font-weight: 500;
            }

            QPushButton {
                background: #667eea;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                font-size: 12px;
            }

            QPushButton:hover {
                background: #5a67d8;
            }

            QPushButton:pressed {
                background: #4c51bf;
            }

            QPushButton:disabled {
                background: #cbd5e1;
                color: #94a3b8;
            }

            QComboBox, QSpinBox {
                padding: 12px;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                font-size: 13px;
                background: white;
                color: #0f172a;
                selection-background-color: #667eea;
            }

            QComboBox:focus, QSpinBox:focus {
                border: 2px solid #667eea;
            }

            QComboBox QAbstractItemView {
                background: white;
                border: 1px solid #e2e8f0;
                selection-background-color: #667eea;
                padding: 4px;
                border-radius: 4px;
            }
        """)