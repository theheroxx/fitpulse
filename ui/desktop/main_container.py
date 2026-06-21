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
# AUTH
from ui.desktop.widgets.login_widget import LoginWidget
from ui.desktop.widgets.register_widget import RegisterWidget


class MainContainer(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("AI Fitness Advisor")
        self.setMinimumSize(1220, 820)
        self.resize(1360, 860)

        # Retain beautiful frameless window state consistently
        self.setWindowFlags(Qt.FramelessWindowHint)

        # Avoid translucent background rendering engine pipeline lag
        self.setAttribute(Qt.WA_NoSystemBackground, False)

        self.current_page = 0
        self.current_user = None
        self.is_dragging = False
        self.drag_position = QPoint()

        # Track RAG availability
        self.rag_available = False

        self.setup_ui()
        self.apply_static_styles()
        
        # Explicitly force the application to open directly into full screen mode
        self.showFullScreen()
        self.update_window_state_ui()

    # =========================================================
    # RAG STATUS
    # =========================================================
    
    def set_rag_status(self, available: bool):
        """Called from main.py after RAG pre-initialization"""
        self.rag_available = available
        if hasattr(self, 'chat_page'):
            self.chat_page.set_rag_status(available)

    # =========================================================
    # UI INITIALIZATION
    # =========================================================

    def setup_ui(self):
        central = QWidget()
        central.setObjectName("main_container")
        self.setCentralWidget(central)

        self.outer_layout = QVBoxLayout(central)
        self.outer_layout.setSpacing(0)
        self.outer_layout.setContentsMargins(16, 16, 16, 16)

        # =====================================================
        # MAIN CONTENT CONTAINER
        # =====================================================
        self.content_widget = QFrame()
        self.content_widget.setObjectName("content_widget")
        self.content_widget.setProperty("filled", "false")

        # CLEAN HIGH-FIDELITY INTERFACE DROPSHADOW
        self.shadow_effect = QGraphicsDropShadowEffect()
        self.shadow_effect.setBlurRadius(35)
        self.shadow_effect.setOffset(0, 8)
        self.shadow_effect.setColor(QColor(15, 23, 42, 45))
        self.content_widget.setGraphicsEffect(self.shadow_effect)

        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # =====================================================
        # TITLE BAR
        # =====================================================
        self.title_bar = self.create_title_bar()
        content_layout.addWidget(self.title_bar)

        # =====================================================
        # TAB BAR
        # =====================================================
        self.tab_bar = self.create_tab_bar()
        self.tab_bar.setVisible(False)
        content_layout.addWidget(self.tab_bar)

        # =====================================================
        # CORE UI PAGES STACK
        # =====================================================
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setObjectName("stacked_widget")

        # LOGIN PAGE
        self.login_page = LoginWidget()
        self.login_page.login_successful.connect(self.on_login_success)
        self.login_page.switch_to_register.connect(lambda: self.switch_to_page(1))
        self.stacked_widget.addWidget(self.login_page)

        # REGISTER PAGE
        self.register_page = RegisterWidget()
        self.register_page.switch_to_login.connect(lambda: self.switch_to_page(0))
        self.register_page.registration_successful.connect(lambda: self.switch_to_page(0))
        self.stacked_widget.addWidget(self.register_page)

        # HOME PAGE
        self.home_page = HomePage(self)
        self.stacked_widget.addWidget(self.home_page)

        # ANALYSIS PAGE
        self.analysis_page = AnalysisWidget()
        self.analysis_page.analysis_completed.connect(self.on_analysis_completed)
        self.stacked_widget.addWidget(self.analysis_page)

        # CHAT PAGE
        self.chat_page = ChatTab()
        self.stacked_widget.addWidget(self.chat_page)

        # PROFILE PAGE
        self.profile_page = UserProfileWidget()
        self.profile_page.edit_clicked.connect(self.show_onboarding)
        self.stacked_widget.addWidget(self.profile_page)

        # HISTORY PAGE
        self.history_page = HistoryTab()
        self.stacked_widget.addWidget(self.history_page)

        # RECORDS PAGE
        self.records_page = RecordsPage()
        self.stacked_widget.addWidget(self.records_page)

        content_layout.addWidget(self.stacked_widget, 1)
        self.outer_layout.addWidget(self.content_widget)

        self.switch_to_page(0)

    # =========================================================
    # TITLE BAR DESIGN
    # =========================================================

    def create_title_bar(self):
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

        title_layout = QVBoxLayout()
        title_layout.setSpacing(0)

        title = QLabel("AI Fitness Advisor")
        title.setObjectName("app_title")

        subtitle = QLabel("Smart AI-powered health companion")
        subtitle.setObjectName("app_subtitle")

        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        layout.addLayout(title_layout)

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

        # WINDOW CONTROLS
        self.min_btn = QPushButton("—")
        self.max_btn = QPushButton("▢")
        self.fullscreen_btn = QPushButton("⛶")
        self.close_btn = QPushButton("✕")

        for btn in [self.min_btn, self.max_btn, self.fullscreen_btn, self.close_btn]:
            btn.setObjectName("window_btn")
            btn.setFixedSize(38, 38)
            btn.setCursor(Qt.PointingHandCursor)
            layout.addWidget(btn)

        self.min_btn.clicked.connect(self.showMinimized)
        self.max_btn.clicked.connect(self.toggle_maximize)
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        self.close_btn.clicked.connect(self.close)

        # ADVANCED CONTROL HOOKS
        bar.mousePressEvent = self.title_bar_mouse_press
        bar.mouseMoveEvent = self.title_bar_mouse_move
        bar.mouseReleaseEvent = self.title_bar_mouse_release
        bar.mouseDoubleClickEvent = self.title_bar_mouse_double_click

        return bar

    # =========================================================
    # STATE MANAGEMENT & DYNAMIC STYLING
    # =========================================================

    def toggle_fullscreen(self):
        """Toggle true fullscreen state smoothly"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def toggle_maximize(self):
        """Toggle maximization layout optimizations"""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def changeEvent(self, event):
        """Listens directly to engine window states to handle updates instantly"""
        if event.type() == QEvent.WindowStateChange:
            self.update_window_state_ui()
        super().changeEvent(event)

    def update_window_state_ui(self):
        """Adapts UI configurations seamlessly using cheap, ultra-fast property manipulation"""
        is_maximized = self.isMaximized()
        is_fullscreen = self.isFullScreen()
        is_filled = is_maximized or is_fullscreen

        # Control Layout Margins smoothly without flickering
        margins = 0 if is_filled else 16
        if hasattr(self, 'outer_layout'):
            self.outer_layout.setContentsMargins(margins, margins, margins, margins)

        # Handle Dropshadow artifacts cleanly on full display execution
        if hasattr(self, 'shadow_effect'):
            self.shadow_effect.setEnabled(not is_filled)

        # Adjust Title Action Icon Display Contexts
        if hasattr(self, 'fullscreen_btn'):
            self.fullscreen_btn.setText("🗗" if is_fullscreen else "⛶")
        if hasattr(self, 'max_btn'):
            self.max_btn.setText("❐" if is_maximized else "▢")

        # Update dynamic styling properties instead of parsing global QSS again
        filled_str = "true" if is_filled else "false"
        
        if hasattr(self, 'content_widget'):
            self.content_widget.setProperty("filled", filled_str)
            self.content_widget.style().unpolish(self.content_widget)
            self.content_widget.style().polish(self.content_widget)
            
        if hasattr(self, 'title_bar'):
            self.title_bar.setProperty("filled", filled_str)
            self.title_bar.style().unpolish(self.title_bar)
            self.title_bar.style().polish(self.title_bar)

    # =========================================================
    # NAVIGATION TAB BAR
    # =========================================================

    def create_tab_bar(self):
        tab_widget = QFrame()
        tab_widget.setObjectName("tab_bar")
        tab_widget.setFixedHeight(74)

        layout = QHBoxLayout(tab_widget)
        layout.setContentsMargins(22, 12, 22, 12)
        layout.setSpacing(12)

        tabs = [
            ("🏠 Home", self.go_to_home),
            ("📊 Analysis", self.go_to_analysis),
            ("💬 Chat", self.go_to_chat),
            ("👤 Profile", self.go_to_profile),
            ("🕓 History", self.go_to_history),
            ("📋 Records", self.go_to_records)
        ]

        self.tab_buttons = []
        for text, callback in tabs:
            btn = QPushButton(text)
            btn.setObjectName("tab_button")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(46)
            btn.clicked.connect(callback)
            self.tab_buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()
        return tab_widget

    def switch_to_page(self, index):
        self.current_page = index
        self.stacked_widget.setCurrentIndex(index)
        self.animate_current_page()

        if index >= 2:
            self.update_tab_style(index - 2)

    def animate_current_page(self):
        page = self.stacked_widget.currentWidget()
        if not page:
            return

        opacity_effect = QGraphicsOpacityEffect()
        page.setGraphicsEffect(opacity_effect)
        
        self.page_anim = QPropertyAnimation(opacity_effect, b"opacity")
        self.page_anim.setDuration(200)
        self.page_anim.setStartValue(0.85)
        self.page_anim.setEndValue(1.0)
        self.page_anim.setEasingCurve(QEasingCurve.OutCubic)
        self.page_anim.start()

    def update_tab_style(self, active_index):
        for i, btn in enumerate(self.tab_buttons):
            if i == active_index:
                btn.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2563eb, stop:1 #7c3aed);
                        color: white;
                        border: none;
                        border-radius: 16px;
                        font-size: 14px;
                        font-weight: 700;
                        padding-left: 22px;
                        padding-right: 22px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        color: #64748b;
                        border: none;
                        border-radius: 16px;
                        font-size: 14px;
                        font-weight: 600;
                        padding-left: 22px;
                        padding-right: 22px;
                    }
                    QPushButton:hover {
                        background: #f1f5f9;
                        color: #0f172a;
                    }
                """)

    # =========================================================
    # NAVIGATION HANDLERS
    # =========================================================

    def go_to_home(self): self.switch_to_page(2)
    def go_to_analysis(self): self.switch_to_page(3)
    def go_to_chat(self): self.switch_to_page(4)
    def go_to_profile(self): self.switch_to_page(5)
    def go_to_history(self): self.switch_to_page(6)
    def go_to_records(self): self.switch_to_page(7)

    # =========================================================
    # SESSION MANAGEMENT HOOKS
    # =========================================================

    def on_login_success(self, user):
        print(f"✅ Logged in as {user['username']}")
        self.current_user = user

        if hasattr(self, 'records_page'):
            self.records_page.user_id = user['id']
            self.records_page.load_records()
            self.history_page.sync_records(self.records_page.records)

        self.tab_bar.setVisible(True)
        self.logout_btn.setVisible(True)
        self.user_chip.setVisible(True)
        self.user_chip.setText(f"● {user['username']}")

        self.switch_to_page(2)
        self.profile_page.refresh()

    def on_logout(self):
        self.current_user = None
        if hasattr(self, 'records_page'):
            self.records_page.user_id = None
            self.records_page.records.clear()
            self.records_page.refresh_lists()

        self.tab_bar.setVisible(False)
        self.logout_btn.setVisible(False)
        self.user_chip.setVisible(False)
        self.login_page.clear()

        if hasattr(self, 'chat_page'):
            self.chat_page.clear_chat()
            self.chat_page.context = None

        self.switch_to_page(0)

    def on_analysis_completed(self, result):
        print(f"📊 Analysis completed: ED={result.get('ED', 'N/A')}")
        if hasattr(self, 'chat_page'):
            self.chat_page.set_analysis_context(result)
        if hasattr(self, 'history_page'):
            self.history_page.add_analysis_result(result)
        if hasattr(self, 'history_page') and hasattr(self, 'records_page'):
            self.history_page.sync_records(self.records_page.records)

    def show_onboarding(self):
        self.wizard = OnboardingWizard(edit_mode=True)
        self.wizard.finished.connect(self.on_onboarding_complete)
        self.wizard.exec()

    def on_onboarding_complete(self, data):
        self.profile_page.refresh()

    # =========================================================
    # MOUSE EVENT DRAGGING INTERCEPTORS
    # =========================================================

    def title_bar_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def title_bar_mouse_move(self, event):
        # Prevent dragging window anomalies if filled/fullscreen
        if self.is_dragging and not (self.isMaximized() or self.isFullScreen()):
            self.move(event.globalPosition().toPoint() - self.drag_position)

    def title_bar_mouse_release(self, event):
        self.is_dragging = False

    def title_bar_mouse_double_click(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle_maximize()

    # =========================================================
    # STATIC STYLES ENGINE
    # =========================================================

    def apply_static_styles(self):
        """Applies a high-performance single-pass style matrix utilizing dynamic properties"""
        self.setStyleSheet("""
            QWidget#main_container {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #eef4ff, stop:1 #f8fafc);
            }

            /* Content Frame standard state */
            QFrame#content_widget {
                background: #ffffff;
                border-radius: 28px;
                border: 1px solid #e2e8f0;
            }
            
            /* Content Frame maximized/fullscreen state */
            QFrame#content_widget[filled="true"] {
                border-radius: 0px;
                border: none;
            }

            /* Title Bar standard state */
            QFrame#title_bar {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #7c3aed);
                border-top-left-radius: 28px;
                border-top-right-radius: 28px;
            }
            
            /* Title Bar maximized/fullscreen state */
            QFrame#title_bar[filled="true"] {
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
            }

            QLabel#app_icon {
                font-size: 26px;
            }

            QLabel#app_title {
                color: white;
                font-size: 18px;
                font-weight: 800;
            }

            QLabel#app_subtitle {
                color: rgba(255, 255, 255, 0.82);
                font-size: 12px;
                font-weight: 500;
            }

            QLabel#user_chip {
                background: rgba(255, 255, 255, 0.16);
                color: white;
                border-radius: 14px;
                padding: 10px 18px;
                font-size: 12px;
                font-weight: 700;
            }

            QPushButton#logout_btn {
                background: rgba(255, 255, 255, 0.15);
                color: white;
                border: none;
                border-radius: 14px;
                padding-left: 18px;
                padding-right: 18px;
                font-size: 13px;
                font-weight: 700;
            }

            QPushButton#logout_btn:hover {
                background: rgba(255, 255, 255, 0.25);
            }

            QPushButton#window_btn {
                background: rgba(255, 255, 255, 0.12);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 700;
            }

            QPushButton#window_btn:hover {
                background: rgba(255, 255, 255, 0.24);
            }

            QFrame#tab_bar {
                background: #ffffff;
                border-bottom: 1px solid #e2e8f0;
            }

            QFrame#history_card {
                background: #ffffff;
                border-radius: 24px;
                border: 1px solid #e2e8f0;
            }
        """)