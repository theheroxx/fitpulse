from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from ui.desktop.home import HomePage
from ui.desktop.widgets.analysis import AnalysisWidget
from ui.desktop.widgets.chat_tab import ChatTab
from ui.desktop.widgets.user_profile_widget import UserProfileWidget
from ui.desktop.widgets.onboarding_wizard import OnboardingWizard
from ui.desktop.widgets.records_page import RecordsPage
from ui.desktop.widgets.history_tab import HistoryTab
from ui.desktop.widgets.login_widget import LoginWidget
from ui.desktop.widgets.register_widget import RegisterWidget


class MainContainer(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("AI Fitness Advisor")
        self.setMinimumSize(1220, 820)
        self.resize(1360, 860)

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_NoSystemBackground, False)

        self.current_page = 0
        self.current_user = None
        self.is_dragging  = False
        self.drag_position = QPoint()
        self.rag_available = False

        # First, create the pages (or let setup_ui do it, but we need the references)
        self.setup_ui()  # This should instantiate self.records_page and self.history_page

        # Now connect the signal AFTER they are created
        # Assuming records_page and history_page are created inside setup_ui
        if hasattr(self, 'records_page') and hasattr(self, 'history_page'):
            self.records_page.records_changed.connect(self.history_page.refresh_records)

        self.apply_static_styles()
        self.showFullScreen()
        self.update_window_state_ui()

    # =========================================================
    # RAG STATUS
    # =========================================================

    def set_rag_status(self, available: bool):
        self.rag_available = available
        if hasattr(self, "chat_page"):
            self.chat_page.set_rag_status(available)

    # =========================================================
    # UI INIT
    # =========================================================

    def setup_ui(self):
        central = QWidget()
        central.setObjectName("main_container")
        self.setCentralWidget(central)

        self.outer_layout = QVBoxLayout(central)
        self.outer_layout.setSpacing(0)
        self.outer_layout.setContentsMargins(16, 16, 16, 16)

        self.content_widget = QFrame()
        self.content_widget.setObjectName("content_widget")
        self.content_widget.setProperty("filled", "false")

        self.shadow_effect = QGraphicsDropShadowEffect()
        self.shadow_effect.setBlurRadius(35)
        self.shadow_effect.setOffset(0, 8)
        self.shadow_effect.setColor(QColor(15, 23, 42, 45))
        self.content_widget.setGraphicsEffect(self.shadow_effect)

        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.title_bar = self._create_title_bar()
        content_layout.addWidget(self.title_bar)

        self.tab_bar = self._create_tab_bar()
        self.tab_bar.setVisible(False)
        content_layout.addWidget(self.tab_bar)

        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setObjectName("stacked_widget")

        # ── Pages ─────────────────────────────────────────────

        # 0 — Login
        self.login_page = LoginWidget()
        self.login_page.login_successful.connect(self.on_login_success)
        self.login_page.switch_to_register.connect(lambda: self.switch_to_page(1))
        self.stacked_widget.addWidget(self.login_page)

        # 1 — Register
        self.register_page = RegisterWidget()
        self.register_page.switch_to_login.connect(lambda: self.switch_to_page(0))
        self.register_page.registration_successful.connect(lambda: self.switch_to_page(0))
        self.stacked_widget.addWidget(self.register_page)

        # 2 — Home  (pass self so home.py can reach history_page)
        self.home_page = HomePage(self)
        self.stacked_widget.addWidget(self.home_page)

        # 3 — Analysis
        self.analysis_page = AnalysisWidget()
        self.analysis_page.analysis_completed.connect(self.on_analysis_completed)
        self.stacked_widget.addWidget(self.analysis_page)

        # 4 — Chat
        self.chat_page = ChatTab()
        self.stacked_widget.addWidget(self.chat_page)

        # 5 — Profile
        self.profile_page = UserProfileWidget()
        self.profile_page.edit_clicked.connect(self.show_onboarding)
        self.stacked_widget.addWidget(self.profile_page)

        # 6 — History  ← pass self so HistoryTab can call get_user_id if needed
        self.history_page = HistoryTab(main_container=self)
        self.stacked_widget.addWidget(self.history_page)

        # 7 — Records
        self.records_page = RecordsPage()
        self.stacked_widget.addWidget(self.records_page)

        content_layout.addWidget(self.stacked_widget, 1)
        self.outer_layout.addWidget(self.content_widget)

        self.switch_to_page(0)

    # =========================================================
    # TITLE BAR
    # =========================================================

    def _create_title_bar(self):
        bar = QFrame()
        bar.setObjectName("title_bar")
        bar.setFixedHeight(72)
        bar.setProperty("filled", "false")

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 0, 16, 0)
        layout.setSpacing(12)

        icon = QLabel("🏃")
        icon.setObjectName("app_icon")
        layout.addWidget(icon)

        tc = QVBoxLayout(); tc.setSpacing(0)
        t = QLabel("AI Fitness Advisor"); t.setObjectName("app_title")
        s = QLabel("Smart AI-powered health companion"); s.setObjectName("app_subtitle")
        tc.addWidget(t); tc.addWidget(s)
        layout.addLayout(tc)
        layout.addStretch()

        self.user_chip = QLabel("● Offline")
        self.user_chip.setObjectName("user_chip")
        self.user_chip.setVisible(False)
        layout.addWidget(self.user_chip)

        self.logout_btn = QPushButton("Logout")
        self.logout_btn.setObjectName("logout_btn")
        self.logout_btn.setCursor(Qt.PointingHandCursor)
        self.logout_btn.setFixedHeight(42)
        self.logout_btn.setVisible(False)
        self.logout_btn.clicked.connect(self.on_logout)
        layout.addWidget(self.logout_btn)

        for attr, label in [
            ("min_btn", "—"), ("max_btn", "▢"),
            ("fullscreen_btn", "⛶"), ("close_btn", "✕"),
        ]:
            btn = QPushButton(label)
            btn.setObjectName("window_btn")
            btn.setFixedSize(38, 38)
            btn.setCursor(Qt.PointingHandCursor)
            layout.addWidget(btn)
            setattr(self, attr, btn)

        self.min_btn.clicked.connect(self.showMinimized)
        self.max_btn.clicked.connect(self.toggle_maximize)
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        self.close_btn.clicked.connect(self.close)

        bar.mousePressEvent      = self._tb_press
        bar.mouseMoveEvent       = self._tb_move
        bar.mouseReleaseEvent    = self._tb_release
        bar.mouseDoubleClickEvent = self._tb_dblclick
        return bar

    # =========================================================
    # WINDOW STATE
    # =========================================================

    def toggle_fullscreen(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def toggle_maximize(self):
        self.showNormal() if self.isMaximized() else self.showMaximized()

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            self.update_window_state_ui()
        super().changeEvent(event)

    def update_window_state_ui(self):
        filled = self.isMaximized() or self.isFullScreen()
        margins = 0 if filled else 16
        if hasattr(self, "outer_layout"):
            self.outer_layout.setContentsMargins(margins, margins, margins, margins)
        if hasattr(self, "shadow_effect"):
            self.shadow_effect.setEnabled(not filled)
        if hasattr(self, "fullscreen_btn"):
            self.fullscreen_btn.setText("🗗" if self.isFullScreen() else "⛶")
        if hasattr(self, "max_btn"):
            self.max_btn.setText("❐" if self.isMaximized() else "▢")
        filled_str = "true" if filled else "false"
        for attr in ("content_widget", "title_bar"):
            w = getattr(self, attr, None)
            if w:
                w.setProperty("filled", filled_str)
                w.style().unpolish(w); w.style().polish(w)

    # =========================================================
    # TAB BAR
    # =========================================================

    def _create_tab_bar(self):
        bar = QFrame(); bar.setObjectName("tab_bar"); bar.setFixedHeight(74)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(22, 12, 22, 12); layout.setSpacing(12)

        self.tab_buttons = []
        for text, cb in [
            ("🏠 Home",     self.go_to_home),
            ("📊 Analysis", self.go_to_analysis),
            ("💬 Chat",     self.go_to_chat),
            ("👤 Profile",  self.go_to_profile),
            ("🕓 History",  self.go_to_history),
            ("📋 Records",  self.go_to_records),
        ]:
            btn = QPushButton(text)
            btn.setObjectName("tab_button")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(46)
            btn.clicked.connect(cb)
            self.tab_buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()
        return bar

    def switch_to_page(self, index):
        self.current_page = index
        self.stacked_widget.setCurrentIndex(index)
        # ── DO NOT set a QGraphicsOpacityEffect here — it would destroy
        #    the drop-shadow effects on child cards ──
        if index >= 2:
            self._update_tab_style(index - 2)

    def _update_tab_style(self, active):
        for i, btn in enumerate(self.tab_buttons):
            if i == active:
                btn.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                                    stop:0 #2563eb, stop:1 #7c3aed);
                        color: white; border: none; border-radius: 16px;
                        font-size: 14px; font-weight: 700;
                        padding-left: 22px; padding-right: 22px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: transparent; color: #64748b; border: none;
                        border-radius: 16px; font-size: 14px; font-weight: 600;
                        padding-left: 22px; padding-right: 22px;
                    }
                    QPushButton:hover { background: #f1f5f9; color: #0f172a; }
                """)

    # =========================================================
    # NAVIGATION
    # =========================================================

    def go_to_home(self):     self.switch_to_page(2)
    def go_to_analysis(self): self.switch_to_page(3)
    def go_to_chat(self):     self.switch_to_page(4)
    def go_to_profile(self):  self.switch_to_page(5)
    def go_to_history(self):  self.switch_to_page(6)
    def go_to_records(self):  self.switch_to_page(7)

    # =========================================================
    # SESSION
    # =========================================================

    def on_login_success(self, user):
        print(f"✅ Logged in as {user['username']}")
        self.current_user = user

        if hasattr(self, "records_page"):
            self.records_page.user_id = user["id"]
            self.records_page.load_records()
            self.history_page.sync_records(self.records_page.records)

        # ── Tell history tab the user id so it can load DB records ──
        self.history_page.on_user_login(user["id"])

        self.tab_bar.setVisible(True)
        self.logout_btn.setVisible(True)
        self.user_chip.setVisible(True)
        self.user_chip.setText(f"● {user['username']}")

        self.switch_to_page(2)
        self.profile_page.refresh()

    def on_logout(self):
        self.current_user = None

        if hasattr(self, "records_page"):
            self.records_page.user_id = None
            self.records_page.records.clear()
            self.records_page.refresh_lists()

        # ── Tell history tab to clear user-specific data ──
        self.history_page.on_user_logout()

        self.tab_bar.setVisible(False)
        self.logout_btn.setVisible(False)
        self.user_chip.setVisible(False)
        self.login_page.clear()

        if hasattr(self, "chat_page"):
            self.chat_page.clear_chat()
            self.chat_page.context = None

        self.switch_to_page(0)

    def on_analysis_completed(self, result):
        print(f"📊 Analysis completed: ED={result.get('ED', 'N/A')}")
        if hasattr(self, "chat_page"):
            self.chat_page.set_analysis_context(result)
        self.history_page.add_analysis_result(result)
        self.history_page.sync_records(self.records_page.records)

    def show_onboarding(self):
        self.wizard = OnboardingWizard(edit_mode=True)
        self.wizard.finished.connect(self.on_onboarding_complete)
        self.wizard.exec()

    def on_onboarding_complete(self, data):
        self.profile_page.refresh()

    # =========================================================
    # TITLE BAR DRAG
    # =========================================================

    def _tb_press(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = True
            self.drag_position = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )

    def _tb_move(self, event):
        if self.is_dragging and not (self.isMaximized() or self.isFullScreen()):
            self.move(event.globalPosition().toPoint() - self.drag_position)

    def _tb_release(self, event):
        self.is_dragging = False

    def _tb_dblclick(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle_maximize()

    # =========================================================
    # STYLES
    # =========================================================

    def apply_static_styles(self):
        self.setStyleSheet("""
            QWidget#main_container {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                            stop:0 #eef4ff, stop:1 #f8fafc);
            }
            QFrame#content_widget {
                background: #ffffff;
                border-radius: 28px;
                border: 1px solid #e2e8f0;
            }
            QFrame#content_widget[filled="true"] {
                border-radius: 0px;
                border: none;
            }
            QFrame#title_bar {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                            stop:0 #2563eb, stop:1 #7c3aed);
                border-top-left-radius: 28px;
                border-top-right-radius: 28px;
            }
            QFrame#title_bar[filled="true"] {
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
            }
            QLabel#app_icon    { font-size: 26px; }
            QLabel#app_title   { color: white; font-size: 18px; font-weight: 800; }
            QLabel#app_subtitle { color: rgba(255,255,255,0.82); font-size: 12px; font-weight: 500; }
            QLabel#user_chip {
                background: rgba(255,255,255,0.16);
                color: white; border-radius: 14px;
                padding: 10px 18px; font-size: 12px; font-weight: 700;
            }
            QPushButton#logout_btn {
                background: rgba(255,255,255,0.15);
                color: white; border: none; border-radius: 14px;
                padding-left: 18px; padding-right: 18px;
                font-size: 13px; font-weight: 700;
            }
            QPushButton#logout_btn:hover { background: rgba(255,255,255,0.25); }
            QPushButton#window_btn {
                background: rgba(255,255,255,0.12);
                color: white; border: none; border-radius: 12px;
                font-size: 14px; font-weight: 700;
            }
            QPushButton#window_btn:hover { background: rgba(255,255,255,0.24); }
            QFrame#tab_bar {
                background: #ffffff;
                border-bottom: 1px solid #e2e8f0;
            }
        """)