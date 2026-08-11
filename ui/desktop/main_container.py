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
from ui.desktop.workers.ml_loader import MLLoaderWorker
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
        self.is_dragging = False
        self.drag_position = QPoint()
        self.rag_available = False
        self.is_menu_expanded = True  # Tracks menu state

        # ── FIRST: Create ED engine ─────────────────────────────
        from ed_calculator.math_model import ExerciseDangerMathModel
        self.ed_engine = ExerciseDangerMathModel()

        # ── START ML WORKER (will populate ed_engine) ────────────
        # self.ml_worker = MLLoaderWorker(r"D:\Data mining")
        # self.ml_worker.progress.connect(self.on_ml_progress)
        # self.ml_worker.finished.connect(self.on_ml_loaded)
        # self.ml_worker.error.connect(self.on_ml_error)
        # self.ml_worker.start()

        # ── SETUP UI ──────────────────────────────────────────────
        self.setup_ui()

        # ── CONNECT SIGNALS ───────────────────────────────────────
        if hasattr(self, 'records_page') and hasattr(self, 'history_page'):
            self.records_page.records_changed.connect(self.history_page.refresh_records)

        self.apply_static_styles()
        self.showFullScreen()
        self.update_window_state_ui()

    # =========================================================
    # ML WORKER CALLBACKS
    # =========================================================

    def on_ml_progress(self, message):
        print(f"[ML] {message}")

    def on_ml_loaded(self, result):
        print("[ML] Models loaded successfully!")
        try:
            if result and result.get('is_ready', False):
                if 'bias_map' in result and result['bias_map']:
                    self.ed_engine.bias_map = result['bias_map']
                if 'sigma_map' in result and result['sigma_map']:
                    self.ed_engine.sigma_map = result['sigma_map']
                if 'scaler' in result and result['scaler'] is not None:
                    self.ed_engine.scaler = result['scaler']
                if 'cluster_model' in result and result['cluster_model'] is not None:
                    self.ed_engine.cluster_model = result['cluster_model']
                self.ed_engine.is_ai_ready = result.get('is_ready', False)
                print("✅ ML models integrated into ED engine.")
            else:
                print("ℹ️ ML models not ready. ED engine will use rule-based logic.")
        except Exception as e:
            print(f"⚠️ Error integrating ML models: {e}")

    def on_ml_error(self, error):
        print(f"[ML] Error: {error}")

    # =========================================================
    # RAG STATUS
    # =========================================================

    def set_rag_status(self, available: bool):
        self.rag_available = available
        if hasattr(self, "chat_page"):
            self.chat_page.set_rag_status(available)

    # =========================================================
    # UI SETUP
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

        # Main horizontal layout
        main_horizontal_layout = QHBoxLayout(self.content_widget)
        main_horizontal_layout.setContentsMargins(0, 0, 0, 0)
        main_horizontal_layout.setSpacing(0)

        # Build Side Navigation
        self.side_menu = self._create_side_menu()
        self.side_menu.setVisible(False)  # Hidden on login/register
        main_horizontal_layout.addWidget(self.side_menu)

        # Setup Sliding Animation
        self.menu_animation = QPropertyAnimation(self.side_menu, b"maximumWidth")
        self.menu_animation.setDuration(300)
        self.menu_animation.setEasingCurve(QEasingCurve.InOutCubic)

        # Right Content Area (Title Bar + Stacked Widget)
        self.right_container = QFrame()
        self.right_container.setObjectName("right_container")
        right_layout = QVBoxLayout(self.right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.title_bar = self._create_title_bar()
        right_layout.addWidget(self.title_bar)

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

        # 2 — Home
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

        # 6 — History
        self.history_page = HistoryTab(main_container=self)
        self.stacked_widget.addWidget(self.history_page)

        # 7 — Records
        self.records_page = RecordsPage()
        self.stacked_widget.addWidget(self.records_page)

        right_layout.addWidget(self.stacked_widget, 1)
        main_horizontal_layout.addWidget(self.right_container, 1)

        self.outer_layout.addWidget(self.content_widget)
        self.switch_to_page(0)

    # =========================================================
    # SIDE MENU DESIGN & ANIMATION
    # =========================================================

    def _create_side_menu(self):
        menu = QFrame()
        menu.setObjectName("side_menu")
        menu.setFixedWidth(250)

        layout = QVBoxLayout(menu)
        layout.setContentsMargins(12, 24, 12, 20)
        layout.setSpacing(8)

        # Branding Header
        brand_layout = QHBoxLayout()
        brand_layout.setContentsMargins(4, 0, 4, 16)
        brand_layout.setSpacing(12)

        app_icon = QLabel("🏃")
        app_icon.setObjectName("brand_icon")
        
        self.brand_text_container = QWidget()
        brand_text_layout = QVBoxLayout(self.brand_text_container)
        brand_text_layout.setContentsMargins(0, 0, 0, 0)
        brand_text_layout.setSpacing(2)
        
        brand_title = QLabel("AI Fitness")
        brand_title.setObjectName("brand_title")
        brand_sub = QLabel("Advisor v2.0")
        brand_sub.setObjectName("brand_subtitle")

        brand_text_layout.addWidget(brand_title)
        brand_text_layout.addWidget(brand_sub)
        
        brand_layout.addWidget(app_icon)
        brand_layout.addWidget(self.brand_text_container)
        brand_layout.addStretch()

        layout.addLayout(brand_layout)

        # Divider
        divider = QFrame()
        divider.setObjectName("menu_divider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)
        layout.addSpacing(12)

        # Navigation Buttons
        self.tab_buttons = []
        self.nav_items_data = [
            ("🏠", "Home", self.go_to_home),
            ("📊", "Analysis", self.go_to_analysis),
            ("💬", "Chat", self.go_to_chat),
            ("👤", "Profile", self.go_to_profile),
            ("🕓", "History", self.go_to_history),
            ("📋", "Records", self.go_to_records),
        ]

        for icon, text, cb in self.nav_items_data:
            btn = QPushButton(f"  {icon}   {text}")
            btn.setProperty("icon_symbol", icon)
            btn.setProperty("full_text", text)
            btn.setObjectName("side_menu_btn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(48)
            btn.clicked.connect(cb)
            self.tab_buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        # User Profile & Logout Box at Bottom
        self.user_card = QFrame()
        self.user_card.setObjectName("user_card")
        user_card_layout = QVBoxLayout(self.user_card)
        user_card_layout.setContentsMargins(8, 12, 8, 12)
        user_card_layout.setSpacing(10)

        self.user_chip = QLabel("● Offline")
        self.user_chip.setObjectName("user_chip")
        user_card_layout.addWidget(self.user_chip)

        self.logout_btn = QPushButton("Logout")
        self.logout_btn.setObjectName("logout_btn")
        self.logout_btn.setCursor(Qt.PointingHandCursor)
        self.logout_btn.setFixedHeight(36)
        self.logout_btn.clicked.connect(self.on_logout)
        user_card_layout.addWidget(self.logout_btn)

        layout.addWidget(self.user_card)

        return menu

    def toggle_side_menu(self):
        """Animates menu sliding between expanded (250px) and collapsed (68px)."""
        if self.menu_animation.state() == QAbstractAnimation.Running:
            return
        start_val = self.side_menu.width()
        # If currently expanded, slide fully closed to 0
        if self.is_menu_expanded:
            end_val = 0
            # shrink visuals immediately
            self.brand_text_container.hide()
            self.user_chip.hide()
            self.logout_btn.setText("🚪")
            for btn in self.tab_buttons:
                icon = btn.property("icon_symbol")
                btn.setText(icon)
        else:
            # ensure visible before expanding
            if not self.side_menu.isVisible():
                self.side_menu.setVisible(True)
            end_val = 250
            # restore full texts
            self.brand_text_container.show()
            self.user_chip.show()
            self.logout_btn.setText("Logout")
            for btn in self.tab_buttons:
                icon = btn.property("icon_symbol")
                text = btn.property("full_text")
                btn.setText(f"  {icon}   {text}")

        self.side_menu.setMinimumWidth(0)
        self.side_menu.setMaximumWidth(start_val)

        self.menu_animation.setStartValue(start_val)
        self.menu_animation.setEndValue(end_val)
        self.menu_animation.start()

        # flip state; final visibility will be adjusted on animation finished
        self.is_menu_expanded = not self.is_menu_expanded

        # connect finished handler to hide when closed
        try:
            self.menu_animation.finished.disconnect()
        except Exception:
            pass
        self.menu_animation.finished.connect(self._on_menu_anim_finished)

    def _on_menu_anim_finished(self):
        # Hide the side menu widget when its width is zero to fully remove from layout
        if self.side_menu.width() == 0:
            self.side_menu.setVisible(False)

    # =========================================================
    # TITLE BAR
    # =========================================================

    def _create_title_bar(self):
        bar = QFrame()
        bar.setObjectName("title_bar")
        bar.setFixedHeight(64)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        # Hamburger Button
        self.hamburger_btn = QPushButton("☰")
        self.hamburger_btn.setObjectName("hamburger_btn")
        self.hamburger_btn.setFixedSize(40, 40)
        self.hamburger_btn.setCursor(Qt.PointingHandCursor)
        self.hamburger_btn.setVisible(False)  # Hidden initially until login
        self.hamburger_btn.clicked.connect(self.toggle_side_menu)
        layout.addWidget(self.hamburger_btn)

        layout.addStretch()

        for attr, label in [
            ("min_btn", "—"),
            ("max_btn", "▢"),
            ("fullscreen_btn", "⛶"),
            ("close_btn", "✕"),
        ]:
            btn = QPushButton(label)
            btn.setObjectName("window_btn")
            btn.setFixedSize(36, 36)
            btn.setCursor(Qt.PointingHandCursor)
            layout.addWidget(btn)
            setattr(self, attr, btn)

        self.min_btn.clicked.connect(self.showMinimized)
        self.max_btn.clicked.connect(self.toggle_maximize)
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        self.close_btn.clicked.connect(self.close)

        bar.mousePressEvent = self._tb_press
        bar.mouseMoveEvent = self._tb_move
        bar.mouseReleaseEvent = self._tb_release
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
        for attr in ("content_widget", "title_bar", "side_menu"):
            w = getattr(self, attr, None)
            if w:
                w.setProperty("filled", filled_str)
                w.style().unpolish(w)
                w.style().polish(w)

    # =========================================================
    # NAVIGATION
    # =========================================================

    def switch_to_page(self, index):
        self.current_page = index
        self.stacked_widget.setCurrentIndex(index)
        if index >= 2:
            self._update_tab_style(index - 2)

    def _update_tab_style(self, active):
        for i, btn in enumerate(self.tab_buttons):
            if i == active:
                btn.setStyleSheet("""
                    QPushButton#side_menu_btn {
                        background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #3b82f6, stop:1 #2563eb);
                        color: #ffffff;
                        font-weight: 700;
                        border-left: 4px solid #60a5fa;
                        border-radius: 12px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton#side_menu_btn {
                        background: transparent;
                        color: #94a3b8;
                        font-weight: 600;
                        border-left: 4px solid transparent;
                        border-radius: 12px;
                    }
                    QPushButton#side_menu_btn:hover {
                        background: #1e293b;
                        color: #f8fafc;
                    }
                """)

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

        self.history_page.on_user_login(user["id"])

        self.side_menu.setVisible(True)
        self.hamburger_btn.setVisible(True)
        self.user_chip.setText(f"● {user['username']}")

        self.switch_to_page(2)
        self.profile_page.refresh()

    def on_logout(self):
        self.current_user = None

        if hasattr(self, "records_page"):
            self.records_page.user_id = None
            self.records_page.records.clear()
            self.records_page.refresh_lists()

        self.history_page.on_user_logout()

        self.side_menu.setVisible(False)
        self.hamburger_btn.setVisible(False)
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
                background: #090d16;
            }
            QFrame#content_widget {
                background: #0f172a;
                border-radius: 20px;
                border: 1px solid #1e293b;
            }
            QFrame#content_widget[filled="true"] {
                border-radius: 0px;
                border: none;
            }
            QFrame#side_menu {
                background: #0f172a;
                border-right: 1px solid #1e293b;
                border-top-left-radius: 20px;
                border-bottom-left-radius: 20px;
            }
            QFrame#side_menu[filled="true"] {
                border-top-left-radius: 0px;
                border-bottom-left-radius: 0px;
            }
            QLabel#brand_icon {
                font-size: 26px;
            }
            QLabel#brand_title {
                color: #f8fafc;
                font-size: 16px;
                font-weight: 800;
            }
            QLabel#brand_subtitle {
                color: #64748b;
                font-size: 11px;
                font-weight: 600;
            }
            QFrame#menu_divider {
                background: #1e293b;
                border: none;
            }
            QPushButton#side_menu_btn {
                font-size: 14px;
                text-align: left;
            }
            QFrame#user_card {
                background: #1e293b;
                border-radius: 14px;
                border: 1px solid #334155;
            }
            QLabel#user_chip {
                color: #38bdf8;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton#logout_btn {
                background: #ef4444;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton#logout_btn:hover {
                background: #dc2626;
            }
            QFrame#right_container {
                background: #f8fafc;
                border-top-right-radius: 20px;
                border-bottom-right-radius: 20px;
            }
            QFrame#title_bar {
                background: transparent;
            }
            QPushButton#hamburger_btn {
                background: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 10px;
                font-size: 18px;
                font-weight: 700;
            }
            QPushButton#hamburger_btn:hover {
                background: #334155;
            }
            QPushButton#window_btn {
                background: #e2e8f0;
                color: #475569;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 700;
            }
            QPushButton#window_btn:hover {
                background: #cbd5e1;
                color: #0f172a;
            }
        """)