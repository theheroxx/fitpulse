# ui/desktop/widgets/login_widget.py

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *


class LoginWidget(QWidget):

    # =====================================================
    # Signals
    # =====================================================
    login_successful = Signal(dict)
    switch_to_register = Signal()

    def __init__(self):
        super().__init__()

        self.setup_ui()
        self.setup_connections()

    # =====================================================
    # UI
    # =====================================================
    def setup_ui(self):

        self.setObjectName("mainWidget")

        self.setStyleSheet("""
            QWidget#mainWidget {
                background: qlineargradient(
                    x1:0, y1:0,
                    x2:1, y2:1,
                    stop:0 #f8fafc,
                    stop:1 #eef2ff
                );
            }
        """)

        # =================================================
        # Main Layout
        # =================================================
        main_layout = QVBoxLayout(self)

        main_layout.setContentsMargins(
            24,
            24,
            24,
            24
        )

        main_layout.addStretch()

        # =================================================
        # Card
        # =================================================
        self.card = QFrame()

        self.card.setMinimumWidth(380)
        self.card.setMaximumWidth(480)

        self.card.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.96);

                border: 1px solid #e2e8f0;

                border-radius: 30px;
            }
        """)

        shadow = QGraphicsDropShadowEffect()

        shadow.setBlurRadius(60)
        shadow.setOffset(0, 14)

        shadow.setColor(
            QColor(99, 102, 241, 40)
        )

        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)

        card_layout.setContentsMargins(
            42,
            42,
            42,
            38
        )

        card_layout.setSpacing(14)

        # =================================================
        # Logo
        # =================================================
        logo_container = QWidget()

        logo_layout = QHBoxLayout(logo_container)

        logo_layout.setContentsMargins(0, 0, 0, 0)

        self.logo = QLabel("🔐")

        self.logo.setFixedSize(84, 84)

        self.logo.setAlignment(Qt.AlignCenter)

        self.logo.setStyleSheet("""
            QLabel {
                background: qlineargradient(
                    x1:0, y1:0,
                    x2:1, y2:1,
                    stop:0 #6366f1,
                    stop:1 #8b5cf6
                );

                border-radius: 42px;

                font-size: 34px;

                color: white;
            }
        """)

        logo_layout.addStretch()
        logo_layout.addWidget(self.logo)
        logo_layout.addStretch()

        card_layout.addWidget(logo_container)

        card_layout.addSpacing(6)

        # =================================================
        # Title
        # =================================================
        title = QLabel("Welcome Back")

        title.setAlignment(Qt.AlignCenter)

        title.setFont(
            QFont(
                "Segoe UI",
                24,
                QFont.Bold
            )
        )

        title.setStyleSheet("""
            color: #0f172a;
            background: transparent;
            border: none;
        """)

        card_layout.addWidget(title)

        # =================================================
        # Subtitle
        # =================================================
        subtitle = QLabel(
            "Sign in to continue to AI Fitness Advisor"
        )

        subtitle.setAlignment(Qt.AlignCenter)

        subtitle.setWordWrap(True)

        subtitle.setStyleSheet("""
            color: #64748b;
            font-size: 13px;
            background: transparent;
            border: none;
            padding-bottom: 8px;
        """)

        card_layout.addWidget(subtitle)

        card_layout.addSpacing(10)

        # =================================================
        # Username
        # =================================================
        username_label = QLabel(
            "Username or Email"
        )

        username_label.setStyleSheet("""
            color: #334155;
            font-size: 13px;
            font-weight: 700;
            border: none;
            background: transparent;
        """)

        card_layout.addWidget(username_label)

        self.username_input = QLineEdit()

        self.username_input.setPlaceholderText(
            "Enter your username or email"
        )

        self.username_input.setMinimumHeight(56)

        self.username_input.setClearButtonEnabled(True)

        self.username_input.setStyleSheet("""
            QLineEdit {
                background: #f8fafc;

                border: 2px solid #e2e8f0;

                border-radius: 18px;

                padding-left: 18px;
                padding-right: 18px;

                color: #0f172a;

                font-size: 14px;
                font-weight: 500;
            }

            QLineEdit:focus {
                background: white;

                border: 2px solid #818cf8;
            }
        """)

        card_layout.addWidget(
            self.username_input
        )

        # =================================================
        # Password
        # =================================================
        password_label = QLabel("Password")

        password_label.setStyleSheet("""
            color: #334155;
            font-size: 13px;
            font-weight: 700;
            border: none;
            background: transparent;
        """)

        card_layout.addWidget(
            password_label
        )

        # =================================================
        # Password Container
        # =================================================
        password_container = QFrame()

        password_container.setStyleSheet("""
            QFrame {
                background: #f8fafc;

                border: 2px solid #e2e8f0;

                border-radius: 18px;
            }

            QFrame:focus-within {
                background: white;
                border: 2px solid #818cf8;
            }
        """)

        password_layout = QHBoxLayout(password_container)

        password_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        password_layout.setSpacing(0)

        self.password_input = QLineEdit()

        self.password_input.setEchoMode(
            QLineEdit.Password
        )

        self.password_input.setPlaceholderText(
            "Enter your password"
        )

        self.password_input.setMinimumHeight(56)

        self.password_input.setStyleSheet("""
            QLineEdit {
                background: transparent;

                border: none;

                padding-left: 18px;

                color: #0f172a;

                font-size: 14px;
                font-weight: 500;
            }
        """)

        # =================================================
        # Show Password Button
        # =================================================
        self.show_password_btn = QPushButton("👁")

        self.show_password_btn.setCursor(
            Qt.PointingHandCursor
        )

        self.show_password_btn.setCheckable(True)

        self.show_password_btn.setFixedSize(48, 48)

        self.show_password_btn.setStyleSheet("""
            QPushButton {
                background: transparent;

                border: none;

                font-size: 16px;
            }

            QPushButton:hover {
                background: #eef2ff;

                border-radius: 14px;
            }
        """)

        password_layout.addWidget(
            self.password_input
        )

        password_layout.addWidget(
            self.show_password_btn
        )

        card_layout.addWidget(
            password_container
        )

        card_layout.addSpacing(6)

        # =================================================
        # Error Label
        # =================================================
        self.error_label = QLabel("")

        self.error_label.setAlignment(
            Qt.AlignCenter
        )

        self.error_label.setWordWrap(True)

        self.error_label.setVisible(False)

        self.error_label.setStyleSheet("""
            QLabel {
                background: #fef2f2;

                color: #dc2626;

                border: 1px solid #fecaca;

                border-radius: 12px;

                padding: 10px;

                font-size: 12px;

                font-weight: 600;
            }
        """)

        card_layout.addWidget(
            self.error_label
        )

        card_layout.addSpacing(10)

        # =================================================
        # Login Button
        # =================================================
        self.login_btn = QPushButton(
            "Sign In"
        )

        self.login_btn.setMinimumHeight(54)

        self.login_btn.setCursor(
            Qt.PointingHandCursor
        )

        self.login_btn.setDefault(True)

        self.login_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1:0, y1:0,
                    x2:1, y2:1,
                    stop:0 #6366f1,
                    stop:1 #8b5cf6
                );

                color: white;

                border: none;

                border-radius: 18px;

                font-size: 15px;

                font-weight: 700;
            }

            QPushButton:hover {
                background: #5855eb;
            }

            QPushButton:pressed {
                padding-top: 2px;
            }

            QPushButton:disabled {
                background: #cbd5e1;
                color: white;
            }
        """)

        card_layout.addWidget(
            self.login_btn
        )

        card_layout.addSpacing(18)

        # =================================================
        # Divider
        # =================================================
        divider_layout = QHBoxLayout()

        left_line = QFrame()
        left_line.setFrameShape(QFrame.HLine)

        right_line = QFrame()
        right_line.setFrameShape(QFrame.HLine)

        left_line.setStyleSheet("""
            color: #e2e8f0;
        """)

        right_line.setStyleSheet("""
            color: #e2e8f0;
        """)

        or_label = QLabel("OR")

        or_label.setStyleSheet("""
            color: #94a3b8;
            font-size: 11px;
            font-weight: 700;
            padding-left: 10px;
            padding-right: 10px;
            border: none;
            background: transparent;
        """)

        divider_layout.addWidget(left_line)
        divider_layout.addWidget(or_label)
        divider_layout.addWidget(right_line)

        card_layout.addLayout(divider_layout)

        card_layout.addSpacing(8)

        # =================================================
        # Create Account Button
        # =================================================
        self.register_link = QPushButton(
            "Create New Account"
        )

        self.register_link.setMinimumHeight(50)

        self.register_link.setCursor(
            Qt.PointingHandCursor
        )

        self.register_link.setStyleSheet("""
            QPushButton {
                background: transparent;

                color: #6366f1;

                border: 2px solid #c7d2fe;

                border-radius: 16px;

                font-size: 13px;

                font-weight: 700;
            }

            QPushButton:hover {
                background: #eef2ff;

                border: 2px solid #a5b4fc;
            }

            QPushButton:pressed {
                background: #e0e7ff;
            }
        """)

        card_layout.addWidget(
            self.register_link
        )

        # =================================================
        # Center Card
        # =================================================
        center_layout = QHBoxLayout()

        center_layout.addStretch()
        center_layout.addWidget(self.card)
        center_layout.addStretch()

        main_layout.addLayout(
            center_layout
        )

        main_layout.addStretch()

    # =====================================================
    # Connections
    # =====================================================
    def setup_connections(self):

        # Login button
        self.login_btn.clicked.connect(
            self.on_login
        )

        # Enter key login
        self.username_input.returnPressed.connect(
            self.on_login
        )

        self.password_input.returnPressed.connect(
            self.on_login
        )

        # Switch to register
        self.register_link.clicked.connect(
            self.switch_to_register.emit
        )

        # Show/Hide password
        self.show_password_btn.toggled.connect(
            self.toggle_password_visibility
        )

        # Clear error while typing
        self.username_input.textChanged.connect(
            self.clear_error
        )

        self.password_input.textChanged.connect(
            self.clear_error
        )

    # =====================================================
    # Toggle Password Visibility
    # =====================================================
    def toggle_password_visibility(self, checked):

        if checked:

            self.password_input.setEchoMode(
                QLineEdit.Normal
            )

            self.show_password_btn.setText("🙈")

        else:

            self.password_input.setEchoMode(
                QLineEdit.Password
            )

            self.show_password_btn.setText("👁")

    # =====================================================
    # Show Error
    # =====================================================
    def show_error(self, text):

        self.error_label.setText(text)

        self.error_label.setVisible(True)

    # =====================================================
    # Clear Error
    # =====================================================
    def clear_error(self):

        self.error_label.clear()

        self.error_label.setVisible(False)

    # =====================================================
    # Login
    # =====================================================
    def on_login(self):

        username = (
            self.username_input.text().strip()
        )

        password = (
            self.password_input.text().strip()
        )

        if not username or not password:

            self.show_error(
                "Please enter username and password"
            )

            return

        self.login_btn.setEnabled(False)
        self.login_btn.setText("Signing In...")

        QApplication.processEvents()

        from database.auth import authenticate_user

        user, message = authenticate_user(
            username,
            password
        )

        self.login_btn.setEnabled(True)
        self.login_btn.setText("Sign In")

        if user:

            self.clear()

            self.login_successful.emit(user)

        else:

            self.show_error(message)

    # =====================================================
    # Clear
    # =====================================================
    def clear(self):

        self.username_input.clear()

        self.password_input.clear()

        self.clear_error()

        self.password_input.setEchoMode(
            QLineEdit.Password
        )

        self.show_password_btn.setChecked(False)

        self.username_input.setFocus()