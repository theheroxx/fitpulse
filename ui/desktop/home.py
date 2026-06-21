# ui/desktop/home.py

from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, 
    QHBoxLayout, 
    QVBoxLayout, 
    QLabel, 
    QPushButton, 
    QGridLayout, 
    QFrame, 
    QSizePolicy,
    QGraphicsDropShadowEffect
)
from PySide6.QtCore import (
    Qt, 
    QPropertyAnimation, 
    QEasingCurve, 
    QTimer
)
from PySide6.QtGui import QColor

from database.db import get_user_records, save_experience_record


class ElevatedCard(QFrame):
    """
    Custom frame that handles its own micro-interactions cleanly, 
    preventing geometry layout thrashing.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Setup modern premium drop shadow
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(25)
        self.shadow.setOffset(0, 6)
        self.shadow.setColor(QColor(15, 23, 42, 30))
        self.setGraphicsEffect(self.shadow)

        # Drop shadow lifting animation
        self.anim = QPropertyAnimation(self.shadow, b"blurRadius")
        self.anim.setDuration(180)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.offset_anim = QPropertyAnimation(self.shadow, b"offset")
        self.offset_anim.setDuration(180)
        self.offset_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def enterEvent(self, event):
        self.anim.stop()
        self.offset_anim.stop()
        
        self.anim.setEndValue(40)
        self.offset_anim.setEndValue(Qt.core.QPointF(0, 12) if hasattr(Qt, 'core') else (0, 12)) 
        
        self.anim.start()
        self.offset_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim.stop()
        self.offset_anim.stop()
        
        self.anim.setEndValue(25)
        self.offset_anim.setEndValue(Qt.core.QPointF(0, 6) if hasattr(Qt, 'core') else (0, 6))
        
        self.anim.start()
        self.offset_anim.start()
        super().leaveEvent(event)


class HomePage(QWidget):
    """
    Modern animated premium homepage UI core
    """
    def __init__(self, main_container=None):
        super().__init__()
        self.main_container = main_container
        self.sidebar_visible = False
        
        # Store the latest experience emoji
        self.latest_experience = None

        self.setup_ui()
        self.setup_animations()
        self.load_dynamic_data()

    # =========================================================
    # UI SETUP
    # =========================================================

    def setup_ui(self):
        self.setObjectName("homePage")

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # -----------------------------------------------------
        # LEFT MAIN AREA
        # -----------------------------------------------------
        left_container = QWidget()
        left_container.setObjectName("leftContainer")

        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(28, 20, 28, 20)
        left_layout.setSpacing(20)

        # Top Nav Bar
        top_bar = QHBoxLayout()
        logo = QLabel("FITPULSE")
        logo.setObjectName("logo")
        top_bar.addWidget(logo)
        top_bar.addStretch()

        icon_layout = QHBoxLayout()
        icon_layout.setSpacing(14)

        search_btn = QPushButton("🔍")
        profile_btn = QPushButton("👤")
        self.menu_btn = QPushButton("☰")

        self.menu_btn.setFixedSize(42, 42)
        self.menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_btn.setObjectName("topIconBtn")
        self.menu_btn.clicked.connect(self.toggle_sidebar)

        for btn in [search_btn, profile_btn]:
            btn.setFixedSize(42, 42)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setObjectName("topIconBtn")
            icon_layout.addWidget(btn)

        icon_layout.addWidget(self.menu_btn)
        top_bar.addLayout(icon_layout)
        left_layout.addLayout(top_bar)

        # -----------------------------------------------------
        # DASHBOARD GRID
        # -----------------------------------------------------
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(24)

        self.latest_card = self.create_card(
            title="YOUR LATEST WORK",
            title_color="#10b981",
            main_text="Loading...",
            sub_text="",
            right_text="🏋"
        )

        self.rest_card = self.create_card(
            title="TO DO & AVOID TODAY",
            title_color="#3b82f6",
            main_text="Loading...",
            sub_text="",
            right_text="🧠"
        )

        # Pass reference to self for emoji handling
        self.diet_card = self.create_interaction_card(
            title="HOW WAS YOUR DIET?",
            subtitle="Share your last week's experience",
            emojis=["😊", "😐", "☹️"]
        )

        record_card = self.create_interaction_card(
            title="SET NEW RECORDS!",
            subtitle="Track your improvements",
            emojis=["🏆"]
        )

        grid.addWidget(self.latest_card, 0, 0)
        grid.addWidget(self.diet_card, 0, 1)
        grid.addWidget(self.rest_card, 1, 0)
        grid.addWidget(record_card, 1, 1)

        left_layout.addLayout(grid)
        left_layout.addStretch()

        # Bottom Action Bar
        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()

        start_btn = QPushButton("🚀 Start Training")
        start_btn.setFixedSize(190, 58)
        start_btn.setObjectName("bottomHomeBtn")
        start_btn.clicked.connect(self.open_records_page)

        bottom_bar.addWidget(start_btn)
        bottom_bar.addStretch()
        left_layout.addLayout(bottom_bar)

        # -----------------------------------------------------
        # SIDEBAR PANEL
        # -----------------------------------------------------
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setMaximumWidth(0)
        self.sidebar.setMinimumWidth(0)

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(16, 24, 16, 24)
        sidebar_layout.setSpacing(12)

        sidebar_items = [
            "📋 Records",
            "🍽 Diet",
            "🏋 Exercise Plan",
            "⛅ Weather",
            "🦴 Body Posture",
        ]

        for index, item in enumerate(sidebar_items):
            btn = QPushButton(item)
            btn.setMinimumHeight(58)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setObjectName("sidebarButton")
            sidebar_layout.addWidget(btn)

            if index == 0:
                btn.clicked.connect(self.open_records_page)

        sidebar_layout.addStretch()

        # Assembly
        self.main_layout.addWidget(left_container)
        self.main_layout.addWidget(self.sidebar)

        self.apply_styles()

        # Active poll dynamic updates
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_dynamic_data)
        self.refresh_timer.start(4000)

    # =========================================================
    # COMPONENT CREATION (COMPACT ENGINE)
    # =========================================================

    def create_card(self, title, title_color, main_text, sub_text, right_text):
        card = ElevatedCard()
        card.setObjectName("dashboardCard")
        card.setMinimumHeight(260)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel(title)
        header.setObjectName("cardHeader")
        header.setStyleSheet(f"""
            QLabel#cardHeader {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                            stop:0 {title_color}, stop:1 rgba(255,255,255,0.12));
            }}
        """)
        header.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setFixedHeight(52)
        layout.addWidget(header)

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(28, 28, 28, 28)
        body_layout.setSpacing(20)

        left_vbox = QVBoxLayout()
        left_vbox.setSpacing(12)

        title_label = QLabel(main_text)
        title_label.setObjectName("cardMainText")
        title_label.setWordWrap(True)
        title_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        title_label.setMinimumHeight(80)
        title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        sub_label = QLabel(sub_text)
        sub_label.setObjectName("cardSubText")
        sub_label.setWordWrap(True)
        sub_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        sub_label.setMinimumHeight(50)
        sub_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        left_vbox.addWidget(title_label)
        left_vbox.addWidget(sub_label)
        left_vbox.addStretch()

        right_label = QLabel(right_text)
        right_label.setObjectName("cardRightText")
        right_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_label.setMinimumWidth(70)

        body_layout.addLayout(left_vbox, 1)
        body_layout.addWidget(right_label)
        layout.addWidget(body)

        # Keep safe runtime handles to layout children 
        card.title_label = title_label
        card.sub_label = sub_label
        card.right_label = right_label

        return card

    def create_interaction_card(self, title, subtitle, emojis):
        card = ElevatedCard()
        card.setObjectName("interactionCard")
        card.setMinimumHeight(210)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        bubble = QLabel(title)
        bubble.setObjectName("bubbleTitle")
        bubble.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bubble.setFixedHeight(70)

        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("bubbleSubtitle")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setWordWrap(True)

        emoji_row = QHBoxLayout()
        emoji_row.setSpacing(16)
        emoji_row.addStretch()

        # Store buttons for later access
        emoji_buttons = []
        
        for emoji in emojis:
            btn = QPushButton(emoji)
            btn.setObjectName("emojiBtn")
            btn.setFixedSize(68, 68)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # FIXED: No 'checked' parameter for QPushButton
            btn.clicked.connect(lambda checked=False, e=emoji: self.on_experience_selected(e))
            
            emoji_row.addWidget(btn)
            emoji_buttons.append(btn)

        emoji_row.addStretch()

        layout.addWidget(bubble)
        layout.addWidget(subtitle_label)
        layout.addSpacing(6)
        layout.addLayout(emoji_row)
        layout.addStretch()

        # Store reference to emoji buttons for UI feedback
        card.emoji_buttons = emoji_buttons

        return card

    # =========================================================
    # EXPERIENCE HANDLER
    # =========================================================

    def on_experience_selected(self, emoji):
        """
        Handle emoji selection from the experience card.
        Saves the experience to database and updates UI feedback.
        """
        print(f"📊 Experience selected: {emoji}")
        
        # Store the latest experience
        self.latest_experience = emoji
        
        # Map emoji to experience value
        experience_map = {
            "😊": "good",
            "😐": "neutral",
            "☹️": "bad"
        }
        experience_value = experience_map.get(emoji, "neutral")
        
        # Save to database (if user is logged in)
        if self.main_container and hasattr(self.main_container, 'current_user'):
            user_id = self.main_container.current_user.get('id')
            if user_id:
                try:
                    save_experience_record(user_id, experience_value, emoji)
                    print(f"✅ Experience saved: {experience_value} ({emoji})")
                except Exception as e:
                    print(f"❌ Failed to save experience: {e}")
            else:
                print("⚠️ No user ID found, experience not saved")
        else:
            print("⚠️ No user context, experience not saved")
        
        # Update UI feedback - highlight selected emoji
        self.update_emoji_feedback(emoji)

    def update_emoji_feedback(self, selected_emoji):
        """Visually highlight the selected emoji button"""
        # Find the diet card and its emoji buttons
        for child in self.findChildren(ElevatedCard):
            if hasattr(child, 'emoji_buttons'):
                for btn in child.emoji_buttons:
                    if btn.text() == selected_emoji:
                        btn.setStyleSheet("""
                            QPushButton {
                                background: #dbeafe;
                                border: 2px solid #2563eb;
                                border-radius: 22px;
                                font-size: 26px;
                            }
                        """)
                    else:
                        btn.setStyleSheet("""
                            QPushButton {
                                background: white;
                                border: 1px solid #e2e8f0;
                                border-radius: 22px;
                                font-size: 26px;
                            }
                        """)

    # =========================================================
    # ANIMATIONS & NAVIGATION
    # =========================================================

    def setup_animations(self):
        self.sidebar_animation = QPropertyAnimation(self.sidebar, b"maximumWidth")
        self.sidebar_animation.setDuration(350)
        self.sidebar_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def toggle_sidebar(self):
        self.sidebar_animation.stop()
        self.sidebar_animation.setStartValue(self.sidebar.width())
        
        if self.sidebar_visible:
            self.sidebar_animation.setEndValue(0)
            self.sidebar_visible = False
        else:
            self.sidebar_animation.setEndValue(240)
            self.sidebar_visible = True
            
        self.sidebar_animation.start()

    def open_records_page(self):
        if self.main_container:
            self.main_container.go_to_records()

    # =========================================================
    # DYNAMIC DATA CONTROLLERS
    # =========================================================

    def load_records(self):
        if not self.main_container or not getattr(self.main_container, 'current_user', None):
            return []
        try:
            user_id = self.main_container.current_user['id']
            records = get_user_records(user_id)
            formatted_records = []

            for record in records:
                formatted_record = dict(record)
                if "record_type" in formatted_record:
                    formatted_record["type"] = formatted_record.pop("record_type")
                formatted_record["is_done"] = bool(formatted_record.get("is_done", 0))
                formatted_records.append(formatted_record)

            return formatted_records
        except Exception as e:
            print(f"Error loading records securely: {e}")
            return []

    def load_dynamic_data(self):
        records = self.load_records()
        self.update_latest_work(records)
        self.update_rest_logic(records)

    def update_latest_work(self, records):
        if not records:
            self.latest_card.title_label.setText("Start your workout journey")
            self.latest_card.sub_label.setText("Create your first workout or diet record now.")
            self.latest_card.right_label.setText("🚀")
            return

        latest = records[0]
        record_type = str(latest.get("type", "")).lower()

        if record_type == "workout":
            title = latest.get("exercise_name") or latest.get("title") or "Workout"
            intensity = latest.get("intensity", "Medium")
            duration = latest.get("duration")
            extra = f" • {duration} min" if duration else ""

            self.latest_card.title_label.setText(title)
            self.latest_card.sub_label.setText(f"{intensity} intensity workout{extra}")
            self.latest_card.right_label.setText("🏋")

        elif record_type == "diet":
            meal = latest.get("meal_type", "Diet")
            calories = latest.get("calories")
            calorie_text = f" • {calories} kcal" if calories else ""

            self.latest_card.title_label.setText(latest.get("title", meal))
            self.latest_card.sub_label.setText(f"{meal}{calorie_text}")
            self.latest_card.right_label.setText("🍽")

        else:
            self.latest_card.title_label.setText(latest.get("title", "New Record"))
            notes = latest.get("notes", "New activity added.")
            if len(notes) > 85:
                notes = notes[:85] + "..."
            self.latest_card.sub_label.setText(notes)
            self.latest_card.right_label.setText("📋")

    def update_rest_logic(self, records):
        completed = [r for r in records if r.get("is_done") is True]

        if not completed:
            self.rest_card.title_label.setText("No completed workouts yet")
            self.rest_card.sub_label.setText("Complete workouts to receive recovery advice.")
            self.rest_card.right_label.setText("📋")
            return

        latest_done = completed[0]
        try:
            record_date = datetime.strptime(latest_done["due_date"], "%b %d, %Y")
            days = (datetime.now() - record_date).days
        except (ValueError, KeyError, TypeError):
            days = 0

        intensity = latest_done.get("intensity", "Medium")

        if days <= 1:
            if intensity == "High":
                self.rest_card.title_label.setText("Recovery Day")
                self.rest_card.sub_label.setText("Avoid intense training today. Focus on hydration and sleep.")
                self.rest_card.right_label.setText("🛌")
            elif intensity == "Medium":
                self.rest_card.title_label.setText("Light Activity Recommended")
                self.rest_card.sub_label.setText("Stretching, walking, or light cardio is ideal today.")
                self.rest_card.right_label.setText("🚶")
            else:
                self.rest_card.title_label.setText("You're Ready")
                self.rest_card.sub_label.setText("Low fatigue detected. You can train normally.")
                self.rest_card.right_label.setText("✅")
        elif days <= 3:
            self.rest_card.title_label.setText("Time To Train Again")
            self.rest_card.sub_label.setText("Your body should be sufficiently recovered.")
            self.rest_card.right_label.setText("🔥")
        else:
            self.rest_card.title_label.setText("You've Been Inactive")
            self.rest_card.sub_label.setText("Try restarting with a moderate workout today.")
            self.rest_card.right_label.setText("⚡")

    # =========================================================
    # GLOBAL STYLESHEET APPLICATION
    # =========================================================

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget#homePage {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #eef4ff, stop:1 #f8fbff);
            }
            QWidget#leftContainer {
                background: transparent;
            }
            QLabel#logo {
                font-size: 38px;
                font-weight: 900;
                color: #2563eb;
                letter-spacing: 3px;
            }
            QPushButton#topIconBtn {
                background: rgba(255,255,255,0.85);
                border: 1px solid rgba(255,255,255,0.6);
                border-radius: 16px;
                font-size: 18px;
                color: #0f172a;
            }
            QPushButton#topIconBtn:hover {
                background: white;
                border: 1px solid #93c5fd;
                padding-bottom: 2px;
            }
            QPushButton#topIconBtn:pressed {
                background: #dbeafe;
            }
            QFrame#dashboardCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                            stop:0 rgba(255,255,255,0.98), stop:1 rgba(248,250,252,0.95));
                border-radius: 30px;
                border: 1px solid rgba(226,232,240,0.9);
            }
            QFrame#dashboardCard:hover {
                border: 1px solid #bfdbfe;
                background: white;
            }
            QLabel#cardHeader {
                color: white;
                padding-left: 22px;
                font-size: 14px;
                font-weight: 900;
                letter-spacing: 1px;
                border-top-left-radius: 30px;
                border-top-right-radius: 30px;
            }
            QLabel#cardMainText {
                color: #0f172a;
                font-size: 28px;
                font-weight: 800;
                line-height: 36px;
            }
            QLabel#cardSubText {
                color: #64748b;
                font-size: 15px;
                line-height: 24px;
                font-weight: 500;
            }
            QLabel#cardRightText {
                color: #0f172a;
                font-size: 42px;
                font-weight: 700;
                padding-left: 12px;
            }
            QFrame#interactionCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                            stop:0 rgba(255,255,255,0.95), stop:1 rgba(245,248,255,0.92));
                border-radius: 30px;
                border: 1px solid rgba(226,232,240,0.8);
            }
            QFrame#interactionCard:hover {
                border: 1px solid #c7d2fe;
            }
            QLabel#bubbleTitle {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #4f46e5);
                border: none;
                border-radius: 24px;
                color: white;
                font-size: 22px;
                font-weight: 800;
                padding-left: 14px;
                padding-right: 14px;
            }
            QLabel#bubbleSubtitle {
                color: #475569;
                font-size: 15px;
                font-weight: 500;
                padding-left: 6px;
                padding-right: 6px;
            }
            QPushButton#emojiBtn {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 22px;
                font-size: 26px;
            }
            QPushButton#emojiBtn:hover {
                background: #f8fbff;
                border: 1px solid #60a5fa;
                margin-top: -2px;
            }
            QPushButton#emojiBtn:pressed {
                background: #dbeafe;
            }
            QFrame#sidebar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0f172a, stop:1 #111827);
                border-top-left-radius: 34px;
                border-bottom-left-radius: 34px;
                margin-top: 12px;
                margin-bottom: 12px;
            }
            QPushButton#sidebarButton {
                background: transparent;
                border: none;
                border-radius: 20px;
                color: #e2e8f0;
                text-align: left;
                padding-left: 22px;
                font-size: 16px;
                font-weight: 600;
            }
            QPushButton#sidebarButton:hover {
                background: rgba(255,255,255,0.08);
                padding-left: 28px;
            }
            QPushButton#sidebarButton:pressed {
                background: rgba(255,255,255,0.12);
            }
            QPushButton#bottomHomeBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #4f46e5);
                border: none;
                border-radius: 24px;
                color: white;
                font-size: 18px;
                font-weight: 800;
                padding-left: 18px;
                padding-right: 18px;
            }
            QPushButton#bottomHomeBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #4338ca);
                margin-top: -2px;
            }
            QPushButton#bottomHomeBtn:pressed {
                background: #1e40af;
            }
            QTooltip {
                background: white;
                color: #0f172a;
                border: 1px solid #dbeafe;
                padding: 8px 12px;
                border-radius: 10px;
            }
        """)