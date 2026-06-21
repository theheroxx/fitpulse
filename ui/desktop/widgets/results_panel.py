# ui/desktop/widgets/results_panel.py

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *


class ResultsPanel(QWidget):

    def __init__(self):
        super().__init__()

        self.last_result = None
        self.loading_dots = 0
        self.rotation_angle = 0

        self.setup_ui()
        self.apply_styles()
        self.setup_animations()

    # =========================================================
    # UI
    # =========================================================

    def setup_ui(self):

        layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        # =====================================================
        # SCROLL
        # =====================================================

        scroll = QScrollArea()

        scroll.setWidgetResizable(True)

        scroll.setFrameShape(QFrame.NoFrame)

        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        scroll.setStyleSheet(
            "background: transparent;"
        )

        self.content = QWidget()

        self.content.setObjectName(
            "results_content"
        )

        self.main_layout = QVBoxLayout(
            self.content
        )

        self.main_layout.setContentsMargins(
            30,
            30,
            30,
            30
        )

        self.main_layout.setSpacing(28)

        # =====================================================
        # RESULT CARD
        # =====================================================

        self.result_card = QFrame()

        self.result_card.setObjectName(
            "result_card"
        )

        self.result_card.setProperty(
            "status",
            "loading"
        )

        self.result_card.setMinimumHeight(330)

        result_layout = QVBoxLayout(
            self.result_card
        )

        result_layout.setContentsMargins(
            38,
            38,
            38,
            38
        )

        result_layout.setSpacing(18)

        # -----------------------------------------------------
        # TOP GLOW BAR
        # -----------------------------------------------------

        self.glow_bar = QFrame()

        self.glow_bar.setObjectName(
            "glow_bar"
        )

        self.glow_bar.setFixedHeight(6)

        result_layout.addWidget(
            self.glow_bar
        )

        # -----------------------------------------------------
        # STATUS ICON
        # -----------------------------------------------------

        self.status_icon = QLabel("🔍")

        self.status_icon.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.status_icon.setObjectName(
            "status_icon"
        )

        result_layout.addWidget(
            self.status_icon
        )

        # -----------------------------------------------------
        # STATUS BADGE
        # -----------------------------------------------------

        self.status_badge = QFrame()

        self.status_badge.setObjectName(
            "status_badge"
        )

        badge_layout = QHBoxLayout(
            self.status_badge
        )

        badge_layout.setContentsMargins(
            28,
            14,
            28,
            14
        )

        self.status_text = QLabel(
            "Ready to Analyze"
        )

        self.status_text.setObjectName(
            "status_text"
        )

        self.status_text.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        badge_layout.addWidget(
            self.status_text
        )

        badge_wrapper = QHBoxLayout()

        badge_wrapper.addStretch()

        badge_wrapper.addWidget(
            self.status_badge
        )

        badge_wrapper.addStretch()

        result_layout.addLayout(
            badge_wrapper
        )

        # -----------------------------------------------------
        # SUBTITLE
        # -----------------------------------------------------

        self.status_subtitle = QLabel(
            "Enter your data and click Analyze"
        )

        self.status_subtitle.setObjectName(
            "status_subtitle"
        )

        self.status_subtitle.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.status_subtitle.setWordWrap(True)

        result_layout.addWidget(
            self.status_subtitle
        )

        self.main_layout.addWidget(
            self.result_card
        )

        # =====================================================
        # AI SECTION
        # =====================================================

        self.ai_section = QWidget()

        self.ai_section.setVisible(False)

        ai_layout = QVBoxLayout(
            self.ai_section
        )

        ai_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        ai_layout.setSpacing(14)

        ai_header = QHBoxLayout()

        ai_icon = QLabel("🤖")

        ai_icon.setStyleSheet(
            "font-size: 22px;"
        )

        ai_header.addWidget(ai_icon)

        ai_title = QLabel(
            "AI Coach Advice"
        )

        ai_title.setObjectName(
            "section_title"
        )

        ai_header.addWidget(ai_title)

        ai_header.addStretch()

        ai_layout.addLayout(ai_header)

        self.ai_card = QFrame()

        self.ai_card.setObjectName(
            "ai_card"
        )

        ai_card_layout = QVBoxLayout(
            self.ai_card
        )

        ai_card_layout.setContentsMargins(
            24,
            24,
            24,
            24
        )

        self.ai_text = QLabel("")

        self.ai_text.setObjectName(
            "ai_text"
        )

        self.ai_text.setWordWrap(True)

        ai_card_layout.addWidget(
            self.ai_text
        )

        ai_layout.addWidget(
            self.ai_card
        )

        self.main_layout.addWidget(
            self.ai_section
        )

        # =====================================================
        # QUICK TIPS
        # =====================================================

        self.tips_section = QWidget()

        tips_layout = QVBoxLayout(
            self.tips_section
        )

        tips_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        tips_layout.setSpacing(14)

        tips_header = QLabel(
            "💡 Quick Tips"
        )

        tips_header.setObjectName(
            "section_title"
        )

        tips_layout.addWidget(
            tips_header
        )

        tips_grid = QGridLayout()

        tips_grid.setHorizontalSpacing(14)

        tips_grid.setVerticalSpacing(14)

        tips = [

            (
                "🌡️",
                "Check temperature & humidity before outdoor activities"
            ),

            (
                "🌫️",
                "High pollution? Consider indoor alternatives"
            ),

            (
                "💪",
                "Start slow if you're new to exercise"
            ),

            (
                "💧",
                "Stay hydrated — especially in hot weather"
            )

        ]

        for i, (icon, text) in enumerate(tips):

            tip_card = QFrame()

            tip_card.setObjectName(
                "tip_card"
            )

            tip_layout = QHBoxLayout(
                tip_card
            )

            tip_layout.setContentsMargins(
                18,
                18,
                18,
                18
            )

            tip_layout.setSpacing(14)

            tip_icon = QLabel(icon)

            tip_icon.setStyleSheet(
                "font-size: 22px;"
            )

            tip_layout.addWidget(
                tip_icon
            )

            tip_label = QLabel(text)

            tip_label.setWordWrap(True)

            tip_label.setStyleSheet("""

                color: #334155;

                font-size: 13px;

                font-weight: 500;

            """)

            tip_layout.addWidget(
                tip_label,
                1
            )

            tips_grid.addWidget(
                tip_card,
                i // 2,
                i % 2
            )

        tips_layout.addLayout(
            tips_grid
        )

        self.main_layout.addWidget(
            self.tips_section
        )

        self.main_layout.addStretch()

        scroll.setWidget(
            self.content
        )

        layout.addWidget(scroll)

    # =========================================================
    # ANIMATIONS
    # =========================================================

    def setup_animations(self):

        # -----------------------------------------------------
        # SHADOW
        # -----------------------------------------------------

        shadow = QGraphicsDropShadowEffect()

        shadow.setBlurRadius(45)

        shadow.setOffset(0, 14)

        shadow.setColor(
            QColor(37, 99, 235, 35)
        )

        self.result_card.setGraphicsEffect(
            shadow
        )

        self.result_shadow = shadow

        # -----------------------------------------------------
        # FADE EFFECT
        # -----------------------------------------------------

        self.text_opacity = QGraphicsOpacityEffect()

        self.status_badge.setGraphicsEffect(
            self.text_opacity
        )

        self.fade_animation = QPropertyAnimation(
            self.text_opacity,
            b"opacity"
        )

        self.fade_animation.setDuration(700)

        self.fade_animation.setStartValue(0)

        self.fade_animation.setEndValue(1)

        self.fade_animation.setEasingCurve(
            QEasingCurve.Type.OutCubic
        )

        # -----------------------------------------------------
        # BADGE POP
        # -----------------------------------------------------

        self.badge_animation = QPropertyAnimation(
            self.status_badge,
            b"maximumHeight"
        )

        self.badge_animation.setDuration(400)

        self.badge_animation.setStartValue(20)

        self.badge_animation.setEndValue(90)

        self.badge_animation.setEasingCurve(
            QEasingCurve.Type.OutBack
        )

        # -----------------------------------------------------
        # CARD ENTRANCE
        # -----------------------------------------------------

        self.card_opacity = QGraphicsOpacityEffect()

        # Loading timer setup below
        # (shadow effect already applied at line 445)

        # -----------------------------------------------------
        # LOADING TIMER
        # -----------------------------------------------------

        self.loading_timer = QTimer()

        self.loading_timer.timeout.connect(
            self.animate_loading
        )

    # =========================================================
    # LOADING ANIMATION
    # =========================================================

    def animate_loading(self):

        self.loading_dots += 1

        dots = "." * (
            self.loading_dots % 4
        )

        self.status_text.setText(
            f"Analyzing{dots}"
        )

        icons = [
            "🧠",
            "⚡",
            "📊",
            "🔬"
        ]

        self.status_icon.setText(
            icons[
                self.loading_dots %
                len(icons)
            ]
        )

        # Animated glow
        blur = 40 + (
            (
                self.loading_dots % 4
            ) * 6
        )

        self.result_shadow.setBlurRadius(
            blur
        )

        # Subtitle animation
        subtitles = [

            "Analyzing weather conditions",

            "Checking environmental safety",

            "Generating AI recommendations",

            "Calculating exercise risk"

        ]

        self.status_subtitle.setText(
            subtitles[
                self.loading_dots %
                len(subtitles)
            ]
        )

    # =========================================================
    # RESULT ANIMATION
    # =========================================================

    def animate_result_text(self):

        self.fade_animation.stop()

        self.badge_animation.stop()

        self.text_opacity.setOpacity(0)

        self.status_badge.setMaximumHeight(
            20
        )

        self.fade_animation.start()

        self.badge_animation.start()

    # =========================================================
    # PUBLIC METHODS
    # =========================================================

    def show_loading(self):

        self.result_card.setProperty(
            "status",
            "loading"
        )

        self.status_icon.setText("🧠")

        self.status_text.setText(
            "Analyzing..."
        )

        self.status_subtitle.setText(
            "Processing environmental data"
        )

        self.ai_section.setVisible(False)

        self.tips_section.setVisible(True)

        self.loading_timer.start(450)

        self.update_style()

        QApplication.processEvents()

    def update_status(self, msg):

        self.status_text.setText(msg)

        self.status_subtitle.setText(
            "Please wait..."
        )

        QApplication.processEvents()

    def update_results(self, result):
        self.loading_timer.stop()

        # SAFE EXTRACTION WITH FALLBACKS
        if result is None:
            result = {}
        
        # Get detector output
        detector = result.get("detector", {})
        if detector is None:
            detector = {}
        
        detector_label = detector.get("label", "Moderate")
        detector_score = detector.get("score", 50)
        detector_reasons = detector.get("reasons", [])
        detector_confidence = detector.get("confidence", 0.7)
        
        # Get final AI recommendation
        final_recommendation = result.get("final_recommendation", "")
        if final_recommendation is None:
            final_recommendation = ""

        # Determine display based on detector label
        if detector_label == "Unsafe":
            status_icon = "🚫"
            status_text = "UNSAFE"
            status_color = "#dc2626"
            status_type = "danger"
            status_subtitle = detector_reasons[0][:80] if detector_reasons else "This activity is not recommended"
                
        elif detector_label == "Moderate":
            status_icon = "⚠️"
            status_text = "MODERATE RISK"
            status_color = "#d97706"
            status_type = "moderate"
            status_subtitle = detector_reasons[0][:60] if detector_reasons else "Exercise with caution"
                
        else:
            status_icon = "✅"
            status_text = "SAFE"
            status_color = "#059669"
            status_type = "safe"
            status_subtitle = "Good conditions for exercise"

        # Update UI
        self.result_card.setProperty("status", status_type)
        self.status_icon.setText(status_icon)
        self.status_text.setText(status_text)
        self.status_subtitle.setText(status_subtitle)
        self.status_text.setStyleSheet(f"""
            font-size: 36px;
            font-weight: 900;
            color: {status_color};
            letter-spacing: 1px;
        """)

        self.animate_result_text()

        # AI Advice
        if final_recommendation and len(final_recommendation) > 10 and "Error" not in final_recommendation:
            self.ai_text.setText(final_recommendation)
            self.ai_section.setVisible(True)
        else:
            self.ai_text.setText("Analysis complete. Click 'Detailed Answer' in chat for more information.")
            self.ai_section.setVisible(True)

        self.last_result = result
        self.update_style()
        QApplication.processEvents()

    def show_error(self, msg):

        self.loading_timer.stop()

        self.result_card.setProperty(
            "status",
            "error"
        )

        self.status_icon.setText("❌")

        self.status_text.setText(
            "ERROR"
        )

        self.status_subtitle.setText(msg)

        self.animate_result_text()

        self.ai_section.setVisible(False)

        self.update_style()

    def clear_insights(self):
        pass

    # =========================================================
    # STYLE UPDATE
    # =========================================================

    def update_style(self):

        self.style().unpolish(
            self.result_card
        )

        self.style().polish(
            self.result_card
        )

    # =========================================================
    # STYLES
    # =========================================================

    def apply_styles(self):

        self.setStyleSheet("""

            QWidget#results_content {

                background:
                    qlineargradient(
                        x1:0,
                        y1:0,
                        x2:1,
                        y2:1,
                        stop:0 #f7faff,
                        stop:1 #eef4ff
                    );
            }

            QScrollArea {
                border: none;
                background: transparent;
            }

            /* =================================================
               RESULT CARD
            ================================================= */

            QFrame#result_card {

                border-radius: 36px;

                border: 1px solid rgba(255,255,255,0.8);
            }

            QFrame#result_card[status="loading"] {

                background:
                    qlineargradient(
                        x1:0,
                        y1:0,
                        x2:1,
                        y2:1,
                        stop:0 #dbeafe,
                        stop:1 #c7d2fe
                    );
            }

            QFrame#result_card[status="safe"] {

                background:
                    qlineargradient(
                        x1:0,
                        y1:0,
                        x2:1,
                        y2:1,
                        stop:0 #dcfce7,
                        stop:1 #bbf7d0
                    );
            }

            QFrame#result_card[status="moderate"] {

                background:
                    qlineargradient(
                        x1:0,
                        y1:0,
                        x2:1,
                        y2:1,
                        stop:0 #fef3c7,
                        stop:1 #fde68a
                    );
            }

            QFrame#result_card[status="high"] {

                background:
                    qlineargradient(
                        x1:0,
                        y1:0,
                        x2:1,
                        y2:1,
                        stop:0 #fed7aa,
                        stop:1 #fdba74
                    );
            }

            QFrame#result_card[status="danger"] {

                background:
                    qlineargradient(
                        x1:0,
                        y1:0,
                        x2:1,
                        y2:1,
                        stop:0 #fecaca,
                        stop:1 #fca5a5
                    );
            }

            QFrame#result_card[status="error"] {

                background:
                    qlineargradient(
                        x1:0,
                        y1:0,
                        x2:1,
                        y2:1,
                        stop:0 #e2e8f0,
                        stop:1 #cbd5e1
                    );
            }

            /* =================================================
               GLOW BAR
            ================================================= */

            QFrame#glow_bar {

                background:
                    qlineargradient(
                        x1:0,
                        y1:0,
                        x2:1,
                        y2:0,
                        stop:0 #2563eb,
                        stop:1 #7c3aed
                    );

                border-radius: 3px;
            }

            /* =================================================
               STATUS ICON
            ================================================= */

            QLabel#status_icon {

                font-size: 70px;

                padding-top: 10px;
                padding-bottom: 10px;
            }

            /* =================================================
               STATUS BADGE
            ================================================= */

            QFrame#status_badge {

                background:
                    rgba(255,255,255,0.78);

                border: 1px solid rgba(255,255,255,0.95);

                border-radius: 24px;

                min-height: 64px;
            }

            QLabel#status_text {

                font-size: 36px;

                font-weight: 900;

                color: #0f172a;

                letter-spacing: 1px;
            }

            QLabel#status_subtitle {

                font-size: 15px;

                font-weight: 500;

                color: #334155;

                padding-top: 4px;
            }

            /* =================================================
               SECTIONS
            ================================================= */

            QLabel#section_title {

                font-size: 14px;

                font-weight: 800;

                color: #0f172a;

                letter-spacing: 1px;
            }

            /* =================================================
               AI CARD
            ================================================= */

            QFrame#ai_card {

                background:
                    qlineargradient(
                        x1:0,
                        y1:0,
                        x2:1,
                        y2:1,
                        stop:0 rgba(255,255,255,0.98),
                        stop:1 rgba(248,250,252,0.96)
                    );

                border-radius: 26px;

                border: 1px solid #dbeafe;
            }

            QFrame#ai_card:hover {

                border: 1px solid #93c5fd;
            }

            QLabel#ai_text {

                color: #1e293b;

                font-size: 14px;

                line-height: 1.8;

                font-weight: 500;
            }

            /* =================================================
               TIP CARDS
            ================================================= */

            QFrame#tip_card {

                background:
                    qlineargradient(
                        x1:0,
                        y1:0,
                        x2:1,
                        y2:1,
                        stop:0 rgba(255,255,255,0.98),
                        stop:1 rgba(248,250,252,0.96)
                    );

                border-radius: 22px;

                border: 1px solid #e2e8f0;
            }

            QFrame#tip_card:hover {

                background: white;

                border: 1px solid #bfdbfe;

                margin-top: -2px;
            }

            QLabel {

                color: #0f172a;
            }

        """)