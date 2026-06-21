# ui/desktop/widgets/register_widget.py
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import QFont


class RegisterWidget(QWidget):
    registration_successful = Signal()
    switch_to_login = Signal()
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("📝 Create Account")
        title.setFont(QFont("Segoe UI", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #1e293b;")
        layout.addWidget(title)
        
        subtitle = QLabel("Join AI Fitness Advisor today")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #64748b;")
        layout.addWidget(subtitle)
        
        layout.addSpacing(20)
        
        # Form
        form_widget = QWidget()
        form_widget.setMaximumWidth(450)
        form_layout = QFormLayout(form_widget)
        form_layout.setSpacing(16)
        form_layout.setLabelAlignment(Qt.AlignRight)
        
        # Username
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Choose a username")
        self.username_input.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border-radius: 10px;
                border: 1px solid #e2e8f0;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #4f46e5;
            }
        """)
        form_layout.addRow("Username*:", self.username_input)
        
        # Email
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("your@email.com")
        self.email_input.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border-radius: 10px;
                border: 1px solid #e2e8f0;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #4f46e5;
            }
        """)
        form_layout.addRow("Email:", self.email_input)
        
        # Password
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Create a password")
        self.password_input.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border-radius: 10px;
                border: 1px solid #e2e8f0;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #4f46e5;
            }
        """)
        form_layout.addRow("Password*:", self.password_input)
        
        # Confirm Password
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.setPlaceholderText("Confirm your password")
        self.confirm_input.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border-radius: 10px;
                border: 1px solid #e2e8f0;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #4f46e5;
            }
        """)
        form_layout.addRow("Confirm Password*:", self.confirm_input)
        
        # Age
        self.age_input = QSpinBox()
        self.age_input.setRange(10, 100)
        self.age_input.setValue(25)
        self.age_input.setStyleSheet("""
            QSpinBox {
                padding: 10px;
                border-radius: 10px;
                border: 1px solid #e2e8f0;
                font-size: 13px;
            }
            QSpinBox:focus {
                border: 2px solid #4f46e5;
            }
        """)
        form_layout.addRow("Age:", self.age_input)
        
        # Health Condition
        self.health_combo = QComboBox()
        self.health_combo.addItems(["Healthy", "Asthma", "Heart Condition", "Diabetes"])
        self.health_combo.setStyleSheet("""
            QComboBox {
                padding: 10px;
                border-radius: 10px;
                border: 1px solid #e2e8f0;
                font-size: 13px;
            }
            QComboBox:focus {
                border: 2px solid #4f46e5;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
        """)
        form_layout.addRow("Health Condition:", self.health_combo)
        
        # Fitness Level
        self.fitness_combo = QComboBox()
        self.fitness_combo.addItems(["Low", "Medium", "High"])
        self.fitness_combo.setStyleSheet("""
            QComboBox {
                padding: 10px;
                border-radius: 10px;
                border: 1px solid #e2e8f0;
                font-size: 13px;
            }
            QComboBox:focus {
                border: 2px solid #4f46e5;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
        """)
        form_layout.addRow("Fitness Level:", self.fitness_combo)
        
        # Register button
        self.register_btn = QPushButton("Create Account")
        self.register_btn.setFixedHeight(48)
        self.register_btn.setCursor(Qt.PointingHandCursor)
        self.register_btn.setStyleSheet("""
            QPushButton {
                background: #4f46e5;
                color: white;
                border: none;
                border-radius: 12px;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #4338ca;
            }
            QPushButton:pressed {
                background: #3730a3;
            }
        """)
        self.register_btn.clicked.connect(self.on_register)
        
        # Login link
        self.login_link = QPushButton("Already have an account? Sign In")
        self.login_link.setFlat(True)
        self.login_link.setCursor(Qt.PointingHandCursor)
        self.login_link.setStyleSheet("""
            QPushButton {
                color: #4f46e5;
                text-decoration: underline;
                background: transparent;
                font-size: 13px;
                padding: 8px;
            }
            QPushButton:hover {
                color: #4338ca;
            }
        """)
        self.login_link.clicked.connect(self.switch_to_login.emit)
        
        # Error message label
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #dc3545; font-size: 12px;")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setWordWrap(True)
        
        # Success message label
        self.success_label = QLabel("")
        self.success_label.setStyleSheet("color: #28a745; font-size: 12px;")
        self.success_label.setAlignment(Qt.AlignCenter)
        self.success_label.setVisible(False)
        
        # Center form
        center_layout = QHBoxLayout()
        center_layout.addStretch()
        center_layout.addWidget(form_widget)
        center_layout.addStretch()
        
        layout.addLayout(center_layout)
        layout.addWidget(self.register_btn)
        layout.addWidget(self.login_link)
        layout.addWidget(self.error_label)
        layout.addWidget(self.success_label)
        layout.addStretch()
    
    def on_register(self):
        """Handle registration"""
        username = self.username_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        confirm = self.confirm_input.text().strip()
        
        # Clear previous messages
        self.error_label.setText("")
        self.success_label.setVisible(False)
        
        # Validation
        if not username or not password:
            self.error_label.setText("Username and password are required")
            return
        
        if password != confirm:
            self.error_label.setText("Passwords do not match")
            return
        
        if len(password) < 4:
            self.error_label.setText("Password must be at least 4 characters")
            return
        
        from database.auth import create_user
        
        user_id, message = create_user(
            username=username,
            email=email if email else None,
            password=password,
            age=self.age_input.value(),
            health_condition=self.health_combo.currentText(),
            fitness_level=self.fitness_combo.currentText()
        )
        
        if user_id:
            self.success_label.setText("Account created successfully! Please sign in.")
            self.success_label.setVisible(True)
            self.error_label.setText("")
            
            # Clear form
            self.username_input.clear()
            self.email_input.clear()
            self.password_input.clear()
            self.confirm_input.clear()
            
            # Auto switch to login after 2 seconds
            QTimer.singleShot(2000, self.switch_to_login.emit)
        else:
            self.error_label.setText(message)
    
    def clear(self):
        """Clear all input fields"""
        self.username_input.clear()
        self.email_input.clear()
        self.password_input.clear()
        self.confirm_input.clear()
        self.age_input.setValue(25)
        self.health_combo.setCurrentIndex(0)
        self.fitness_combo.setCurrentIndex(1)
        self.error_label.setText("")
        self.success_label.setVisible(False)