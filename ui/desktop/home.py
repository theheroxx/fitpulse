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
    QGraphicsDropShadowEffect,
    QSpacerItem,
)
from PySide6.QtCore import (
    Qt,
    QPropertyAnimation,
    QEasingCurve,
    QTimer,
    QPointF,
)
from PySide6.QtGui import QColor, QFont

from database.db import get_user_records, save_experience_record


# ─────────────────────────────────────────────
# Design Tokens
# ─────────────────────────────────────────────
NAVY        = "#0D1B2A"
NAVY_LIGHT  = "#162536"
BLUE        = "#2979FF"
BLUE_DARK   = "#1A56DB"
MINT        = "#00E5A0"
MINT_DARK   = "#00C488"
WHITE       = "#FFFFFF"
BG          = "#F0F4FA"
CARD_BG     = "#FFFFFF"
BORDER      = "#E3EAF2"
TEXT_HEAD   = "#0D1B2A"
TEXT_BODY   = "#3D5166"
TEXT_MUTED  = "#8BA0B8"
SHADOW      = QColor(13, 27, 42, 22)


class ElevatedCard(QFrame):
    """Card with a subtle lift animation on hover (shadow only, no geometry shift)."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(20)
        self.shadow.setOffset(0, 4)
        self.shadow.setColor(SHADOW)
        self.setGraphicsEffect(self.shadow)

        self._blur_anim = QPropertyAnimation(self.shadow, b"blurRadius")
        self._blur_anim.setDuration(200)
        self._blur_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def enterEvent(self, event):
        self._blur_anim.stop()
        self._blur_anim.setEndValue(38)
        self._blur_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._blur_anim.stop()
        self._blur_anim.setEndValue(20)
        self._blur_anim.start()
        super().leaveEvent(event)


class LogoLabel(QLabel):
    """
    FitPulse logo rendered as rich text with two-tone lettering
    and a small SVG pulse-line icon.
    """

    LOGO_HTML = (
        '<span style="'
        'font-family: Inter, Helvetica Neue, Arial, sans-serif;'
        'font-size: 26px;'
        'font-weight: 800;'
        'letter-spacing: -0.5px;'
        '">'
        f'<span style="color: {NAVY};">FIT</span>'
        f'<span style="color: {BLUE};">PULSE</span>'
        '</span>'
        # Tiny pulse line encoded as Unicode approximation
        f'<span style="color:{MINT}; font-size:22px; font-weight:900;"> ⚡</span>'
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText(self.LOGO_HTML)
        self.setTextFormat(Qt.TextFormat.RichText)


class HomePage(QWidget):
    """Modern professional fitness dashboard homepage."""

    def __init__(self, main_container=None):
        super().__init__()
        self.main_container = main_container
        self.latest_experience = None
        self.setup_ui()
        self.load_dynamic_data()

    # =========================================================
    # UI SETUP
    # =========================================================

    def setup_ui(self):
        self.setObjectName("homePage")

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # ── LEFT MAIN AREA ────────────────────────────────────
        left_container = QWidget()
        left_container.setObjectName("leftContainer")

        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(32, 22, 32, 24)
        left_layout.setSpacing(0)

        # ── TOP NAV ───────────────────────────────────────────
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)

        logo = LogoLabel()
        top_bar.addWidget(logo)
        top_bar.addStretch()

        icon_layout = QHBoxLayout()
        icon_layout.setSpacing(10)

        for obj_name, icon in [("topIconBtn", "🔍"), ("topIconBtn", "👤")]:
            btn = QPushButton(icon)
            btn.setFixedSize(40, 40)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setObjectName(obj_name)
            icon_layout.addWidget(btn)

        self.menu_btn = QPushButton("☰")
        self.menu_btn.setFixedSize(40, 40)
        self.menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_btn.setObjectName("topIconBtn")
        # Use the main container's side menu toggle so there's a single menu
        if self.main_container and hasattr(self.main_container, "toggle_side_menu"):
            self.menu_btn.clicked.connect(self.main_container.toggle_side_menu)
        icon_layout.addWidget(self.menu_btn)

        top_bar.addLayout(icon_layout)
        left_layout.addLayout(top_bar)
        left_layout.addSpacing(8)

        # ── GREETING ─────────────────────────────────────────
        greeting = QLabel("Good morning 👋")
        greeting.setObjectName("greetingLabel")
        left_layout.addWidget(greeting)

        tagline = QLabel("Here's your fitness snapshot for today.")
        tagline.setObjectName("taglineLabel")
        left_layout.addWidget(tagline)
        left_layout.addSpacing(22)

        # ── DIVIDER ───────────────────────────────────────────
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setObjectName("divider")
        divider.setFixedHeight(1)
        left_layout.addWidget(divider)
        left_layout.addSpacing(22)

        # ── DASHBOARD GRID ────────────────────────────────────
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(20)

        self.latest_card = self.create_stat_card(
            accent=BLUE,
            tag="LATEST WORKOUT",
            main_text="Loading…",
            sub_text="",
            icon="🏋️",
        )

        self.rest_card = self.create_stat_card(
            accent=MINT,
            tag="RECOVERY ADVICE",
            main_text="Loading…",
            sub_text="",
            icon="🧠",
        )

        self.diet_card = self.create_interaction_card(
            accent=BLUE,
            tag="DIET CHECK-IN",
            subtitle="How did your eating go this week?",
            emojis=["😊", "😐", "☹️"],
        )

        record_card = self.create_interaction_card(
            accent=MINT,
            tag="NEW RECORD",
            subtitle="Log a personal best today",
            emojis=["🏆"],
        )

        grid.addWidget(self.latest_card, 0, 0)
        grid.addWidget(self.diet_card,   0, 1)
        grid.addWidget(self.rest_card,   1, 0)
        grid.addWidget(record_card,      1, 1)

        left_layout.addLayout(grid)
        left_layout.addStretch()

        # ── BOTTOM ACTION BAR ─────────────────────────────────
        left_layout.addSpacing(16)
        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()

        start_btn = QPushButton("🚀  Start Training")
        start_btn.setFixedSize(200, 52)
        start_btn.setObjectName("primaryBtn")
        start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        start_btn.clicked.connect(self.open_records_page)

        bottom_bar.addWidget(start_btn)
        bottom_bar.addStretch()
        left_layout.addLayout(bottom_bar)

        # ── ASSEMBLE ──────────────────────────────────────────
        # The application now uses the global side menu in MainContainer.
        self.main_layout.addWidget(left_container)

        self.apply_styles()

        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_dynamic_data)
        self.refresh_timer.start(4000)

    # =========================================================
    # CARD FACTORIES
    # =========================================================

    def create_stat_card(self, accent, tag, main_text, sub_text, icon):
        """Information card with left accent bar and large icon."""
        card = ElevatedCard()
        card.setObjectName("statCard")
        card.setMinimumHeight(210)

        outer = QHBoxLayout(card)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Left accent bar
        bar = QFrame()
        bar.setFixedWidth(5)
        bar.setObjectName("accentBar")
        bar.setStyleSheet(f"background: {accent}; border-radius: 3px;")
        outer.addWidget(bar)

        inner = QVBoxLayout()
        inner.setContentsMargins(22, 20, 22, 20)
        inner.setSpacing(6)

        tag_lbl = QLabel(tag)
        tag_lbl.setObjectName("cardTag")
        tag_lbl.setStyleSheet(f"color: {accent};")

        main_lbl = QLabel(main_text)
        main_lbl.setObjectName("cardMainText")
        main_lbl.setWordWrap(True)

        sub_lbl = QLabel(sub_text)
        sub_lbl.setObjectName("cardSubText")
        sub_lbl.setWordWrap(True)

        inner.addWidget(tag_lbl)
        inner.addSpacing(4)
        inner.addWidget(main_lbl)
        inner.addWidget(sub_lbl)
        inner.addStretch()

        outer.addLayout(inner, 1)

        # Large icon on right
        icon_lbl = QLabel(icon)
        icon_lbl.setObjectName("cardIcon")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setFixedWidth(72)
        outer.addWidget(icon_lbl)
        outer.addSpacing(12)

        card.main_lbl = main_lbl
        card.sub_lbl  = sub_lbl
        card.icon_lbl = icon_lbl
        # legacy attribute aliases used by load_dynamic_data
        card.title_label = main_lbl
        card.sub_label   = sub_lbl
        card.right_label = icon_lbl

        return card

    def create_interaction_card(self, accent, tag, subtitle, emojis):
        """Engagement card with emoji buttons."""
        card = ElevatedCard()
        card.setObjectName("interactionCard")
        card.setMinimumHeight(210)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        # Tag chip
        tag_row = QHBoxLayout()
        tag_chip = QLabel(tag)
        tag_chip.setObjectName("cardTagChip")
        tag_chip.setStyleSheet(
            f"background: {accent}; color: white;"
            f" border-radius: 10px; padding: 3px 12px;"
            f" font-size: 11px; font-weight: 700; letter-spacing: 0.8px;"
        )
        tag_chip.setFixedHeight(24)
        tag_row.addWidget(tag_chip)
        tag_row.addStretch()
        layout.addLayout(tag_row)

        sub_lbl = QLabel(subtitle)
        sub_lbl.setObjectName("cardSubText")
        sub_lbl.setWordWrap(True)

        layout.addWidget(sub_lbl)
        layout.addSpacing(6)

        emoji_row = QHBoxLayout()
        emoji_row.setSpacing(12)
        emoji_row.addStretch()

        emoji_buttons = []
        for emoji in emojis:
            btn = QPushButton(emoji)
            btn.setObjectName("emojiBtn")
            btn.setFixedSize(62, 62)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, e=emoji: self.on_experience_selected(e))
            emoji_row.addWidget(btn)
            emoji_buttons.append(btn)

        emoji_row.addStretch()
        layout.addLayout(emoji_row)
        layout.addStretch()

        card.emoji_buttons = emoji_buttons
        return card

    # =========================================================
    # EXPERIENCE HANDLER
    # =========================================================

    def on_experience_selected(self, emoji):
        self.latest_experience = emoji
        experience_map = {"😊": "good", "😐": "neutral", "☹️": "bad"}
        experience_value = experience_map.get(emoji, "neutral")

        record_id = None
        if self.main_container and hasattr(self.main_container, "current_user"):
            user_id = (self.main_container.current_user or {}).get("id")
            if user_id:
                try:
                    # save_experience_record returns the new row id (int) on success
                    record_id = save_experience_record(user_id, experience_value, emoji)
                except Exception as e:
                    print(f"❌ Failed to save experience: {e}")

        # ── Live-push to history tab (attribute is history_page in MainContainer) ──
        if self.main_container and hasattr(self.main_container, "history_page"):
            ht = self.main_container.history_page
            if ht is not None:
                try:
                    ht.push_experience(emoji, experience_value, record_id)
                except Exception as e:
                    print(f"⚠️ Could not push to history tab: {e}")

        self.update_emoji_feedback(emoji)

    def update_emoji_feedback(self, selected_emoji):
        for child in self.findChildren(ElevatedCard):
            if hasattr(child, "emoji_buttons"):
                for btn in child.emoji_buttons:
                    if btn.text() == selected_emoji:
                        btn.setStyleSheet(
                            f"QPushButton {{ background: #E8F0FE; border: 2px solid {BLUE};"
                            f" border-radius: 20px; font-size: 24px; }}"
                        )
                    else:
                        btn.setStyleSheet(
                            "QPushButton { background: #F6F9FF; border: 1px solid #E3EAF2;"
                            " border-radius: 20px; font-size: 24px; }"
                        )

    # =========================================================
    # ANIMATIONS & NAVIGATION
    # =========================================================

    def open_records_page(self):
        if self.main_container:
            self.main_container.go_to_records()

    # =========================================================
    # DYNAMIC DATA
    # =========================================================

    def load_records(self):
        if not self.main_container or not getattr(self.main_container, "current_user", None):
            return []
        try:
            user_id = self.main_container.current_user["id"]
            records = get_user_records(user_id)
            formatted = []
            for r in records:
                rec = dict(r)
                if "record_type" in rec:
                    rec["type"] = rec.pop("record_type")
                rec["is_done"] = bool(rec.get("is_done", 0))
                formatted.append(rec)
            return formatted
        except Exception as e:
            print(f"Error loading records: {e}")
            return []

    def load_dynamic_data(self):
        records = self.load_records()
        self.update_latest_work(records)
        self.update_rest_logic(records)

    def update_latest_work(self, records):
        if not records:
            self.latest_card.title_label.setText("Start your journey")
            self.latest_card.sub_label.setText("Create your first workout or diet record.")
            self.latest_card.right_label.setText("🚀")
            return

        latest = records[0]
        record_type = str(latest.get("type", "")).lower()

        if record_type == "workout":
            title = latest.get("exercise_name") or latest.get("title") or "Workout"
            intensity = latest.get("intensity", "Medium")
            duration = latest.get("duration")
            extra = f" · {duration} min" if duration else ""
            self.latest_card.title_label.setText(title)
            self.latest_card.sub_label.setText(f"{intensity} intensity{extra}")
            self.latest_card.right_label.setText("🏋️")

        elif record_type == "diet":
            meal = latest.get("meal_type", "Diet")
            calories = latest.get("calories")
            calorie_text = f" · {calories} kcal" if calories else ""
            self.latest_card.title_label.setText(latest.get("title", meal))
            self.latest_card.sub_label.setText(f"{meal}{calorie_text}")
            self.latest_card.right_label.setText("🍽️")

        else:
            self.latest_card.title_label.setText(latest.get("title", "New Record"))
            notes = latest.get("notes", "New activity added.")
            self.latest_card.sub_label.setText(notes[:85] + "…" if len(notes) > 85 else notes)
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
                self.rest_card.sub_label.setText("Avoid intense training. Focus on hydration and sleep.")
                self.rest_card.right_label.setText("🛌")
            elif intensity == "Medium":
                self.rest_card.title_label.setText("Light Activity")
                self.rest_card.sub_label.setText("Stretching or light cardio is ideal today.")
                self.rest_card.right_label.setText("🚶")
            else:
                self.rest_card.title_label.setText("You're Ready")
                self.rest_card.sub_label.setText("Low fatigue detected — train normally.")
                self.rest_card.right_label.setText("✅")
        elif days <= 3:
            self.rest_card.title_label.setText("Time to Train")
            self.rest_card.sub_label.setText("Your body should be sufficiently recovered.")
            self.rest_card.right_label.setText("🔥")
        else:
            self.rest_card.title_label.setText("Been a While")
            self.rest_card.sub_label.setText("Restart with a moderate workout today.")
            self.rest_card.right_label.setText("⚡")

    # =========================================================
    # STYLESHEET
    # =========================================================

    def apply_styles(self):
        self.setStyleSheet(f"""

        /* ── Page Background ── */
        QWidget#homePage {{
            background: {BG};
        }}
        QWidget#leftContainer {{
            background: transparent;
        }}

        /* ── Greeting ── */
        QLabel#greetingLabel {{
            font-size: 20px;
            font-weight: 700;
            color: {TEXT_HEAD};
            margin-top: 18px;
        }}
        QLabel#taglineLabel {{
            font-size: 13px;
            color: {TEXT_MUTED};
            font-weight: 400;
            margin-top: 2px;
        }}

        /* ── Divider ── */
        QFrame#divider {{
            background: {BORDER};
            border: none;
        }}

        /* ── Top Nav Icon Buttons ── */
        QPushButton#topIconBtn {{
            background: {WHITE};
            border: 1px solid {BORDER};
            border-radius: 12px;
            font-size: 16px;
            color: {TEXT_HEAD};
        }}
        QPushButton#topIconBtn:hover {{
            background: {WHITE};
            border: 1px solid {BLUE};
        }}
        QPushButton#topIconBtn:pressed {{
            background: #E8F0FE;
        }}

        /* ── Stat Card ── */
        QFrame#statCard {{
            background: {CARD_BG};
            border-radius: 18px;
            border: 1px solid {BORDER};
        }}
        QFrame#statCard:hover {{
            border: 1px solid #A8C4FF;
        }}
        QLabel#cardTag {{
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1px;
            text-transform: uppercase;
        }}
        QLabel#cardMainText {{
            color: {TEXT_HEAD};
            font-size: 22px;
            font-weight: 700;
            line-height: 30px;
        }}
        QLabel#cardSubText {{
            color: {TEXT_BODY};
            font-size: 13px;
            font-weight: 400;
            line-height: 20px;
        }}
        QLabel#cardIcon {{
            font-size: 38px;
        }}

        /* ── Interaction Card ── */
        QFrame#interactionCard {{
            background: {CARD_BG};
            border-radius: 18px;
            border: 1px solid {BORDER};
        }}
        QFrame#interactionCard:hover {{
            border: 1px solid #A8C4FF;
        }}

        /* ── Emoji Buttons ── */
        QPushButton#emojiBtn {{
            background: #F6F9FF;
            border: 1px solid {BORDER};
            border-radius: 20px;
            font-size: 24px;
        }}
        QPushButton#emojiBtn:hover {{
            background: #EBF2FF;
            border: 1px solid {BLUE};
        }}
        QPushButton#emojiBtn:pressed {{
            background: #D6E4FF;
        }}

        /* ── Primary CTA Button ── */
        QPushButton#primaryBtn {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {BLUE}, stop:1 #5C6BC0);
            border: none;
            border-radius: 16px;
            color: white;
            font-size: 15px;
            font-weight: 700;
            letter-spacing: 0.3px;
        }}
        QPushButton#primaryBtn:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {BLUE_DARK}, stop:1 #4A5BB8);
        }}
        QPushButton#primaryBtn:pressed {{
            background: {BLUE_DARK};
        }}

        /* ── Sidebar ── */
        QFrame#sidebar {{
            background: {NAVY};
            border-top-left-radius: 28px;
            border-bottom-left-radius: 28px;
            margin-top: 10px;
            margin-bottom: 10px;
        }}
        QLabel#sidebarHeader {{
            color: {TEXT_MUTED};
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 2px;
            padding-left: 8px;
        }}
        QLabel#sidebarVersion {{
            color: #2D4055;
            font-size: 11px;
            font-weight: 500;
        }}
        QPushButton#sidebarButton {{
            background: transparent;
            border: none;
            border-radius: 14px;
            color: #C8D8E8;
            text-align: left;
            padding-left: 14px;
            font-size: 14px;
            font-weight: 500;
        }}
        QPushButton#sidebarButton:hover {{
            background: rgba(255,255,255,0.07);
            color: white;
            padding-left: 18px;
        }}
        QPushButton#sidebarButton:pressed {{
            background: rgba(255,255,255,0.12);
        }}

        /* ── Tooltip ── */
        QToolTip {{
            background: {WHITE};
            color: {TEXT_HEAD};
            border: 1px solid {BORDER};
            padding: 6px 10px;
            border-radius: 8px;
            font-size: 12px;
        }}

        """)