# ui/desktop/widgets/user_profile_widget.py

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import QFont, QColor, QIcon, QPixmap
from database.db import get_user
import os


class UserProfileWidget(QWidget):
    edit_clicked = Signal()

    def __init__(self, main_container=None):
        super().__init__()
        self.main_container = main_container
        self.user_data = None
        self.setup_ui()
        self.load_user_data()

    def setup_ui(self):
        self.setStyleSheet("""
            QWidget {
                background: #f8fafc;
            }
        """)

        # Main Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # =========================================================
        # HEADER
        # =========================================================
        header_container = QWidget()
        header_container.setStyleSheet("""
            QWidget {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 18px;
            }
        """)

        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(20, 18, 20, 18)
        header_layout.setSpacing(16)

        # Profile Picture
        profile_pic = self.create_profile_picture()
        header_layout.addWidget(profile_pic)

        # User Title Area (with username)
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        title = QLabel("Your Profile")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("""
            color: #0f172a;
            background: transparent;
            border: none;
        """)

        # USERNAME LABEL
        self.username_label = QLabel("")
        self.username_label.setFont(QFont("Segoe UI", 11))
        self.username_label.setStyleSheet("""
            color: #667eea;
            background: transparent;
            border: none;
            font-weight: 600;
        """)

        subtitle = QLabel("Personal fitness information")
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setStyleSheet("""
            color: #64748b;
            background: transparent;
            border: none;
        """)

        title_layout.addWidget(title)
        title_layout.addWidget(self.username_label)
        title_layout.addWidget(subtitle)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        # Edit Button
        edit_btn = QPushButton("Edit Profile")
        edit_btn.setFixedHeight(40)
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #6366f1,
                    stop:1 #8b5cf6
                );
                color: white;
                border: none;
                border-radius: 10px;
                padding: 0 18px;
                font-size: 12px;
                font-weight: 700;
            }

            QPushButton:hover {
                background: #5855eb;
            }

            QPushButton:pressed {
                background: #4f46e5;
            }
        """)
        edit_btn.clicked.connect(self.edit_clicked.emit)

        header_layout.addWidget(edit_btn)

        layout.addWidget(header_container)

        # =========================================================
        # PROFILE CARD
        # =========================================================
        card = QWidget()
        card.setStyleSheet("""
            QWidget {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 20px;
            }
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 22, 22, 22)
        card_layout.setSpacing(14)

        # Labels
        self.age_label = QLabel("--")
        self.health_label = QLabel("--")
        self.city_label = QLabel("--")
        self.fitness_label = QLabel("--")
        self.bio_label = QLabel("")  # ← NEW bio label

        # Rows
        card_layout.addWidget(
            self.create_info_card("🎂", "Age", self.age_label)
        )

        card_layout.addWidget(
            self.create_info_card("❤️", "Health Condition", self.health_label)
        )

        card_layout.addWidget(
            self.create_info_card("🌍", "City", self.city_label)
        )

        card_layout.addWidget(
            self.create_info_card("💪", "Fitness Level", self.fitness_label)
        )

        # ─── NEW: Bio row ──────────────────────────────────────────
        bio_container = self.create_info_card("📝", "About Me", self.bio_label)
        bio_container.setMinimumHeight(100)  # More room for text
        # Override the value widget style for multiline
        self.bio_label.setWordWrap(True)
        self.bio_label.setStyleSheet("""
            color: #0f172a;
            background: transparent;
            border: none;
            font-size: 12px;
            font-weight: 400;
            line-height: 1.5;
        """)
        card_layout.addWidget(bio_container)

        layout.addWidget(card)

        # IMPORTANT:
        # Removed layout.addStretch()
        # so widget no longer stretches vertically
        layout.setAlignment(Qt.AlignTop)

    # =============================================================
    # INFO CARD
    # =============================================================
    def create_info_card(self, emoji, label_text, value_widget):
        container = QWidget()
        container.setMinimumHeight(72)

        container.setStyleSheet("""
            QWidget {
                background: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 14px;
            }

            QWidget:hover {
                border: 1px solid #cbd5e1;
                background: #f1f5f9;
            }
        """)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(14)

        # Emoji Circle
        icon_container = QLabel(emoji)
        icon_container.setFixedSize(42, 42)
        icon_container.setAlignment(Qt.AlignCenter)

        icon_container.setStyleSheet("""
            QLabel {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 21px;
                font-size: 18px;
            }
        """)

        layout.addWidget(icon_container)

        # Texts
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        label = QLabel(label_text)
        label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        label.setStyleSheet("""
            color: #64748b;
            background: transparent;
            border: none;
        """)

        # For bio, we use the provided widget directly (QLabel)
        value_widget.setFont(QFont("Segoe UI", 12, QFont.Bold))
        value_widget.setStyleSheet("""
            color: #0f172a;
            background: transparent;
            border: none;
        """)

        text_layout.addWidget(label)
        text_layout.addWidget(value_widget)

        layout.addLayout(text_layout)
        layout.addStretch()

        return container

    # =============================================================
    # LOAD USER DATA
    # =============================================================
    def load_user_data(self):
        """Load user data from database and update UI"""
        try:
            from database.auth import get_user_by_id
            from database.db import get_user

            # Get current user from main container
            if self.main_container and self.main_container.current_user:
                user_id = self.main_container.current_user.get("id")
                if user_id:
                    user = get_user_by_id(user_id)
                    if user:
                        self.username_label.setText(user.get("username", "Guest User"))
                        self.age_label.setText(str(user.get("age", "Not set")))
                        self.health_label.setText(user.get("health_condition", "Not set"))
                        self.fitness_label.setText(user.get("fitness_level", "Not set"))
                        city = user.get("city_name") or user.get("city") or "Not set"
                        self.city_label.setText(city)
                        self.bio_label.setText(user.get("bio", "No bio provided."))
                        return

            # Fallback: try to get any user
            user = get_user()
            if user:
                self.username_label.setText(user.get("username", "Guest User"))
                self.age_label.setText(str(user.get("age", "Not set")))
                self.health_label.setText(user.get("health_condition", "Not set"))
                self.fitness_label.setText(user.get("fitness_level", "Not set"))
                city = user.get("city_name") or user.get("city") or "Not set"
                self.city_label.setText(city)
                self.bio_label.setText(user.get("bio", "No bio provided."))
            else:
                self.set_default_values()
        except Exception as e:
            print(f"Error loading user data: {e}")
            self.set_default_values()

    def set_default_values(self):
        """Set default values when no user data exists"""
        self.username_label.setText("Guest User")
        self.age_label.setText("Not set")
        self.health_label.setText("Not set")
        self.city_label.setText("Not set")
        self.fitness_label.setText("Not set")
        self.bio_label.setText("No bio provided.")

    def refresh(self):
        """Refresh profile data from database"""
        self.load_user_data()

    # =============================================================
    # PROFILE PICTURE
    # =============================================================
    def create_profile_picture(self):
        pic_widget = QLabel()
        pic_widget.setFixedSize(60, 60)

        pic_widget.setStyleSheet("""
            QLabel {
                background: qlineargradient(
                    x1:0,y1:0,x2:1,y2:1,
                    stop:0 #4f46e5,
                    stop:1 #9333ea
                );

                border-radius: 30px;
                color: white;
                font-weight: bold;
                font-size: 24px;
                border: 3px solid #eef2ff;
            }
        """)

        pic_widget.setAlignment(Qt.AlignCenter)

        # Try loading image
        resources_dir = os.path.join(
            os.path.dirname(__file__),
            "..",
            "resources"
        )

        pic_path = os.path.join(resources_dir, "profile.png")

        if os.path.exists(pic_path):
            pixmap = QPixmap(pic_path)

            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    60,
                    60,
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation
                )

                pic_widget.setPixmap(scaled_pixmap)
                return pic_widget

        # Fallback Emoji
        pic_widget.setText("👤")

        return pic_widget

    # =============================================================
    # SET USER DATA
    # =============================================================
    def set_user_data(self, age, health, city, fitness):
        self.age_label.setText(str(age))
        self.health_label.setText(health)
        self.city_label.setText(city)
        self.fitness_label.setText(fitness)

        self.load_user_data()