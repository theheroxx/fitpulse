# ui/desktop/widgets/results_panel.py

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *


BRAND_START = "#2563eb"
BRAND_END = "#7c3aed"

STATUS_STYLES = {
    "loading": {
        "icon": "🔍",
        "label": "Ready to Analyze",
        "accent": BRAND_START,
        "fallback_subtitle": "Enter your data and click Analyze",
        "gradient": ("#dbeafe", "#c7d2fe"),
    },
    "safe": {
        "icon": "✅",
        "label": "SAFE",
        "accent": "#059669",
        "fallback_subtitle": "Good conditions for exercise",
        "gradient": ("#dcfce7", "#bbf7d0"),
    },
    "moderate": {
        "icon": "⚠️",
        "label": "MODERATE RISK",
        "accent": "#d97706",
        "fallback_subtitle": "Exercise with caution",
        "gradient": ("#fef3c7", "#fde68a"),
    },
    "high": {
        "icon": "🔶",
        "label": "HIGH RISK",
        "accent": "#ea580c",
        "fallback_subtitle": "Elevated risk — extra precautions recommended",
        "gradient": ("#fed7aa", "#fdba74"),
    },
    "danger": {
        "icon": "🚫",
        "label": "UNSAFE",
        "accent": "#dc2626",
        "fallback_subtitle": "This activity is not recommended",
        "gradient": ("#fecaca", "#fca5a5"),
    },
    "error": {
        "icon": "❌",
        "label": "ERROR",
        "accent": "#64748b",
        "fallback_subtitle": "Something went wrong",
        "gradient": ("#e2e8f0", "#cbd5e1"),
    },
}


def _escape_html(text) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _clear_layout(layout):
    """Recursively remove and delete every widget/child-layout from `layout`."""
    if layout is None:
        return
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()
            continue
        child_layout = item.layout()
        if child_layout is not None:
            _clear_layout(child_layout)


class ScoreGauge(QWidget):
    """Animated ring gauge that visualises the detector's 0-100 score."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(104, 104)
        self._display_value = 0.0
        self._target_value = 0.0
        self._ring_color = QColor(BRAND_START)

        self._animation = QPropertyAnimation(self, b"ringValue")
        self._animation.setDuration(900)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _get_ring_value(self):
        return self._display_value

    def _set_ring_value(self, value):
        self._display_value = value
        self.update()

    ringValue = Property(float, _get_ring_value, _set_ring_value)

    def set_score(self, value, color: str):
        """Animate the ring to a new 0-100 score using the given accent color."""
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = 0.0
        self._target_value = max(0.0, min(100.0, value))
        self._ring_color = QColor(color)
        self._animation.stop()
        self._animation.setStartValue(self._display_value)
        self._animation.setEndValue(self._target_value)
        self._animation.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        stroke = 10
        rect = QRectF(stroke / 2, stroke / 2, self.width() - stroke, self.height() - stroke)

        track_pen = QPen(QColor(255, 255, 255, 130))
        track_pen.setWidth(stroke)
        track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(track_pen)
        painter.drawArc(rect, 0, 360 * 16)

        value_pen = QPen(self._ring_color)
        value_pen.setWidth(stroke)
        value_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(value_pen)
        span = -int(self._display_value / 100 * 360 * 16)
        painter.drawArc(rect, 90 * 16, span)

        painter.setPen(QColor("#0f172a"))
        font = QFont()
        font.setPointSize(19)
        font.setWeight(QFont.Weight.Black)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(int(round(self._display_value))))
        painter.end()


class LoadingSpinner(QWidget):
    """Lightweight rotating-arc busy indicator shown while an analysis runs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(64, 64)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)

    def start(self):
        self._timer.start(16)

    def stop(self):
        self._timer.stop()

    def _advance(self):
        self._angle = (self._angle + 6) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        stroke = 6
        rect = QRectF(stroke / 2, stroke / 2, self.width() - stroke, self.height() - stroke)

        track_pen = QPen(QColor(255, 255, 255, 100))
        track_pen.setWidth(stroke)
        track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(track_pen)
        painter.drawArc(rect, 0, 360 * 16)

        arc_pen = QPen(QColor(BRAND_START))
        arc_pen.setWidth(stroke)
        arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(arc_pen)
        painter.drawArc(rect, -self._angle * 16, 110 * 16)
        painter.end()


class ResultsPanel(QWidget):

    SHADOW_BASE_BLUR = 45
    ICON_STAGE_SIZE = 112

    def __init__(self):
        super().__init__()

        self.last_result = None
        self.loading_dots = 0
        self.rotation_angle = 0

        self.setup_ui()
        self.apply_styles()
        self.setup_animations()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent;")

        self.content = QWidget()
        self.content.setObjectName("results_content")

        self.main_layout = QVBoxLayout(self.content)
        self.main_layout.setContentsMargins(28, 28, 28, 28)
        self.main_layout.setSpacing(26)

        # Hero Card
        self.result_card = QFrame()
        self.result_card.setObjectName("result_card")
        self.result_card.setProperty("status", "loading")
        self.result_card.setMinimumHeight(320)
        self.result_card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        result_layout = QVBoxLayout(self.result_card)
        result_layout.setContentsMargins(36, 32, 36, 34)
        result_layout.setSpacing(20)

        # Glow bar
        self.glow_bar = QFrame()
        self.glow_bar.setObjectName("glow_bar")
        self.glow_bar.setFixedHeight(5)
        result_layout.addWidget(self.glow_bar)

        # Stage setup
        self.icon_stage = QWidget()
        self.icon_stage.setFixedSize(self.ICON_STAGE_SIZE, self.ICON_STAGE_SIZE)
        
        self.icon_stack = QStackedLayout(self.icon_stage)
        self.icon_stack.setContentsMargins(0, 0, 0, 0)

        self.idle_icon = QLabel(STATUS_STYLES["loading"]["icon"])
        self.idle_icon.setObjectName("idle_icon")
        self.idle_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.spinner = LoadingSpinner()
        self.gauge = ScoreGauge()

        self._idle_page = self._centered_page(self.idle_icon)
        self._spinner_page = self._centered_page(self.spinner)
        self._gauge_page = self._centered_page(self.gauge)

        self.icon_stack.addWidget(self._idle_page)
        self.icon_stack.addWidget(self._spinner_page)
        self.icon_stack.addWidget(self._gauge_page)

        stage_wrapper = QHBoxLayout()
        stage_wrapper.addStretch()
        stage_wrapper.addWidget(self.icon_stage)
        stage_wrapper.addStretch()
        result_layout.addLayout(stage_wrapper)

        # Info wrapper
        self.info_wrapper = QWidget()
        info_layout = QVBoxLayout(self.info_wrapper)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(12)

        self.status_badge = QFrame()
        self.status_badge.setObjectName("status_badge")

        badge_layout = QHBoxLayout(self.status_badge)
        badge_layout.setContentsMargins(26, 12, 26, 12)

        self.status_text = QLabel("Ready to Analyze")
        self.status_text.setObjectName("status_text")
        self.status_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_text.setWordWrap(True)
        badge_layout.addWidget(self.status_text)

        badge_wrapper = QHBoxLayout()
        badge_wrapper.addStretch()
        badge_wrapper.addWidget(self.status_badge)
        badge_wrapper.addStretch()
        info_layout.addLayout(badge_wrapper)

        self.status_subtitle = QLabel("Enter your data and click Analyze")
        self.status_subtitle.setObjectName("status_subtitle")
        self.status_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_subtitle.setWordWrap(True)
        info_layout.addWidget(self.status_subtitle)

        meta_row = QHBoxLayout()
        meta_row.addStretch()
        self.confidence_pill = QLabel("Confidence  —")
        self.confidence_pill.setObjectName("confidence_pill")
        self.confidence_pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.confidence_pill.setVisible(False)
        self.confidence_pill.setToolTip("How confident the model is in this assessment")
        meta_row.addWidget(self.confidence_pill)
        meta_row.addStretch()
        info_layout.addLayout(meta_row)

        self.reasons_container = QFrame()
        self.reasons_container.setObjectName("reasons_panel")
        self.reasons_container.setVisible(False)
        self.reasons_layout = QVBoxLayout(self.reasons_container)
        self.reasons_layout.setContentsMargins(20, 14, 20, 14)
        self.reasons_layout.setSpacing(8)
        info_layout.addWidget(self.reasons_container)

        result_layout.addWidget(self.info_wrapper)
        self.main_layout.addWidget(self.result_card)

        # AI Section
        self.ai_section = QWidget()
        self.ai_section.setVisible(False)

        ai_layout = QVBoxLayout(self.ai_section)
        ai_layout.setContentsMargins(0, 0, 0, 0)
        ai_layout.setSpacing(14)

        ai_header = QHBoxLayout()
        ai_header.setSpacing(12)

        self.ai_avatar = QLabel("🤖")
        self.ai_avatar.setObjectName("ai_avatar")
        self.ai_avatar.setFixedSize(38, 38)
        self.ai_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ai_header.addWidget(self.ai_avatar)

        ai_title_box = QVBoxLayout()
        ai_title_box.setSpacing(0)
        ai_title = QLabel("AI Coach Advice")
        ai_title.setObjectName("section_title")
        ai_subtitle = QLabel("Personalized recommendation")
        ai_subtitle.setObjectName("section_subtitle")
        ai_title_box.addWidget(ai_title)
        ai_title_box.addWidget(ai_subtitle)
        ai_header.addLayout(ai_title_box)

        ai_header.addStretch()
        ai_layout.addLayout(ai_header)

        self.ai_card = QFrame()
        self.ai_card.setObjectName("ai_card")

        ai_card_layout = QVBoxLayout(self.ai_card)
        ai_card_layout.setContentsMargins(22, 22, 22, 22)

        self.ai_text = QTextBrowser()
        self.ai_text.setObjectName("ai_text")
        self.ai_text.setOpenExternalLinks(False)
        self.ai_text.setReadOnly(True)
        self.ai_text.setFrameStyle(QFrame.NoFrame)
        self.ai_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ai_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.ai_text.setWordWrapMode(QTextOption.WordWrap)
        self.ai_text.setMinimumHeight(140)
        self.ai_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        ai_card_layout.addWidget(self.ai_text)

        ai_layout.addWidget(self.ai_card)
        self.main_layout.addWidget(self.ai_section)

        # Quick Tips
        self.tips_section = QWidget()
        tips_layout = QVBoxLayout(self.tips_section)
        tips_layout.setContentsMargins(0, 0, 0, 0)
        tips_layout.setSpacing(14)

        tips_header = QLabel("💡 Quick Tips")
        tips_header.setObjectName("section_title")
        tips_layout.addWidget(tips_header)

        tips_grid = QGridLayout()
        tips_grid.setHorizontalSpacing(14)
        tips_grid.setVerticalSpacing(14)

        tips = [
            ("🌡️", "#dbeafe", "Check temperature & humidity before outdoor activities"),
            ("🌫️", "#ede9fe", "High pollution? Consider indoor alternatives"),
            ("💪", "#dcfce7", "Start slow if you're new to exercise"),
            ("💧", "#cffafe", "Stay hydrated — especially in hot weather"),
        ]

        for i, (icon, badge_color, text) in enumerate(tips):
            tip_card = self._build_tip_card(icon, badge_color, text)
            tips_grid.addWidget(tip_card, i // 2, i % 2)

        tips_layout.addLayout(tips_grid)
        self.main_layout.addWidget(self.tips_section)
        self.main_layout.addStretch()

        scroll.setWidget(self.content)
        layout.addWidget(scroll)

    def _centered_page(self, widget) -> QWidget:
        holder = QWidget()
        outer = QHBoxLayout(holder)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch(1)

        inner = QVBoxLayout()
        inner.setContentsMargins(0, 0, 0, 0)
        inner.addStretch(1)
        inner.addWidget(widget, 0, Qt.AlignmentFlag.AlignCenter)
        inner.addStretch(1)

        outer.addLayout(inner)
        outer.addStretch(1)
        return holder

    def _build_tip_card(self, icon: str, badge_color: str, text: str) -> QFrame:
        tip_card = QFrame()
        tip_card.setObjectName("tip_card")

        tip_layout = QHBoxLayout(tip_card)
        tip_layout.setContentsMargins(16, 16, 16, 16)
        tip_layout.setSpacing(14)

        tip_icon = QLabel(icon)
        tip_icon.setFixedSize(38, 38)
        tip_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tip_icon.setStyleSheet(
            f"font-size: 18px; background-color: {badge_color}; border-radius: 19px;"
        )
        tip_layout.addWidget(tip_icon)

        tip_label = QLabel(text)
        tip_label.setObjectName("tip_text")
        tip_label.setWordWrap(True)
        tip_layout.addWidget(tip_label, 1)

        return tip_card

    def _show_icon(self, which: str):
        if which == "idle":
            self.icon_stack.setCurrentWidget(self._idle_page)
        elif which == "spinner":
            self.icon_stack.setCurrentWidget(self._spinner_page)
        elif which == "gauge":
            self.icon_stack.setCurrentWidget(self._gauge_page)

    def _set_reasons(self, reasons, accent: str):
        _clear_layout(self.reasons_layout)
        reasons = [r for r in (reasons or []) if r]

        if not reasons:
            self.reasons_container.setVisible(False)
            return

        for reason in reasons[:4]:
            row = QLabel()
            row.setObjectName("reason_row")
            row.setWordWrap(True)
            row.setTextFormat(Qt.TextFormat.RichText)
            row.setText(f'<span style="color:{accent};">&#9679;</span>&nbsp;&nbsp;{_escape_html(reason)}')
            self.reasons_layout.addWidget(row)

        self.reasons_container.setVisible(True)

    def setup_animations(self):
        shadow = QGraphicsDropShadowEffect(self.result_card)
        shadow.setBlurRadius(self.SHADOW_BASE_BLUR)
        shadow.setOffset(0, 14)
        shadow.setColor(QColor(37, 99, 235, 35))
        self.result_card.setGraphicsEffect(shadow)
        self.result_shadow = shadow

        self.reveal_effect = QGraphicsOpacityEffect(self.info_wrapper)
        self.reveal_effect.setOpacity(1.0)
        self.info_wrapper.setGraphicsEffect(self.reveal_effect)

        self.reveal_animation = QPropertyAnimation(self.reveal_effect, b"opacity", self)
        self.reveal_animation.setDuration(400)
        self.reveal_animation.setStartValue(0.2)
        self.reveal_animation.setEndValue(1.0)
        self.reveal_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.loading_timer = QTimer(self)
        self.loading_timer.timeout.connect(self.animate_loading)

    def animate_loading(self):
        self.loading_dots += 1
        dots = "." * (self.loading_dots % 4)
        self.status_text.setText(f"Analyzing{dots}")

        subtitles = [
            "Analyzing weather conditions",
            "Checking environmental safety",
            "Generating AI recommendations",
            "Calculating exercise risk",
        ]
        self.status_subtitle.setText(subtitles[self.loading_dots % len(subtitles)])

        blur = self.SHADOW_BASE_BLUR + ((self.loading_dots % 4) * 6)
        self.result_shadow.setBlurRadius(blur)

    def animate_result_text(self):
        self.reveal_animation.stop()
        self.reveal_animation.start()

    def show_loading(self):
        self.result_card.setProperty("status", "loading")

        self._show_icon("spinner")
        self.spinner.start()

        self.status_text.setText("Analyzing...")
        self.status_text.setStyleSheet("")
        self.status_subtitle.setText("Processing environmental data")

        self.confidence_pill.setVisible(False)
        self._set_reasons([], STATUS_STYLES["loading"]["accent"])

        self.reveal_animation.stop()
        self.reveal_effect.setOpacity(1.0)
        self.result_shadow.setBlurRadius(self.SHADOW_BASE_BLUR)

        self.ai_section.setVisible(False)
        self.tips_section.setVisible(True)

        self.loading_dots = 0
        self.loading_timer.start(450)

        self.update_style()

    def update_status(self, msg):
        self.status_text.setText(msg)
        self.status_subtitle.setText("Please wait...")

    def update_results(self, result):
        self.loading_timer.stop()
        self.spinner.stop()
        self.result_shadow.setBlurRadius(self.SHADOW_BASE_BLUR)

        if result is None:
            result = {}

        detector = result.get("detector", {}) or {}
        detector_label = detector.get("label", "Moderate")
        detector_score = detector.get("score", 50)
        detector_reasons = detector.get("reasons", []) or []
        detector_confidence = detector.get("confidence", 0.7)

        final_recommendation = result.get("final_recommendation", "") or ""

        fallback_phrases = [
            "Great conditions! Enjoy your workout today",
            "Moderate risk. Take it a bit easier",
            "Not the best day for outdoor exercise",
            "Analysis complete. Use the Chat tab",
            "Unable to generate AI recommendation"
        ]
        is_fallback = any(phrase in final_recommendation for phrase in fallback_phrases)

        if detector_label == "Unsafe":
            status_type = "danger"
        elif detector_label == "High":
            status_type = "high"
        elif detector_label == "Moderate":
            status_type = "moderate"
        else:
            status_type = "safe"

        style = STATUS_STYLES[status_type]
        status_subtitle = (
            str(detector_reasons[0])[:90] if detector_reasons else style["fallback_subtitle"]
        )

        self._show_icon("gauge")
        self.gauge.set_score(detector_score, style["accent"])

        self.result_card.setProperty("status", status_type)
        self.status_text.setText(style["label"])
        self.status_text.setStyleSheet(f"color: {style['accent']};")
        self.status_subtitle.setText(status_subtitle)

        self.confidence_pill.setText(f"Confidence  {int(round(detector_confidence * 100))}%")
        self.confidence_pill.setVisible(True)

        self._set_reasons(detector_reasons, style["accent"])

        if final_recommendation and len(final_recommendation) > 10 and not is_fallback:
            self.ai_text.setMarkdown(final_recommendation)
            self.ai_section.setVisible(True)
        else:
            if status_type != "error":
                self.ai_text.setPlainText(
                    "🤖 AI Coach is currently unavailable.\n\n"
                    "• The LLM service may be busy or not responding.\n"
                    "• Try again in a moment.\n"
                    "• You can also use the Chat tab for Q&A."
                )
                self.ai_section.setVisible(True)
            else:
                self.ai_text.setPlainText("")
                self.ai_section.setVisible(False)

        self.last_result = result
        self.update_style()
        self.animate_result_text()

    def show_error(self, msg):
        self.loading_timer.stop()
        self.spinner.stop()
        self.result_shadow.setBlurRadius(self.SHADOW_BASE_BLUR)

        style = STATUS_STYLES["error"]

        self._show_icon("idle")
        self.idle_icon.setText(style["icon"])

        self.result_card.setProperty("status", "error")
        self.status_text.setText("ERROR")
        self.status_text.setStyleSheet(f"color: {style['accent']};")
        self.status_subtitle.setText(msg)

        self.confidence_pill.setVisible(False)
        self._set_reasons([], style["accent"])

        self.ai_section.setVisible(False)
        self.update_style()
        self.animate_result_text()

    def clear_insights(self):
        self.loading_timer.stop()
        self.spinner.stop()
        self.reveal_animation.stop()
        self.reveal_effect.setOpacity(1.0)
        self.result_shadow.setBlurRadius(self.SHADOW_BASE_BLUR)

        style = STATUS_STYLES["loading"]

        self._show_icon("idle")
        self.idle_icon.setText(style["icon"])

        self.result_card.setProperty("status", "loading")
        self.status_text.setText("Ready to Analyze")
        self.status_text.setStyleSheet("")
        self.status_subtitle.setText(style["fallback_subtitle"])

        self.confidence_pill.setVisible(False)
        self._set_reasons([], style["accent"])

        if hasattr(self.ai_text, 'clear'):
            self.ai_text.clear()
        else:
            self.ai_text.setText("")
        self.ai_section.setVisible(False)

        self.gauge.set_score(0, style["accent"])
        self.last_result = None
        self.update_style()

    def update_style(self):
        self.style().unpolish(self.result_card)
        self.style().polish(self.result_card)

    def apply_styles(self):
        def grad(colors):
            start, end = colors
            return (
                "qlineargradient(x1:0, y1:0, x2:1, y2:1, "
                f"stop:0 {start}, stop:1 {end})"
            )

        status_blocks = "\n".join(
            f'QFrame#result_card[status="{key}"] {{ background: {grad(style["gradient"])}; }}'
            for key, style in STATUS_STYLES.items()
        )

        self.setStyleSheet(f"""
            QWidget {{
                font-family: "Segoe UI", "SF Pro Display", "Helvetica Neue", Arial, sans-serif;
            }}

            QWidget#results_content {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f7faff, stop:1 #eef4ff);
            }}

            QScrollArea {{
                border: none;
                background: transparent;
            }}

            QFrame#result_card {{
                border-radius: 32px;
                border: 1px solid rgba(255,255,255,0.8);
            }}

            {status_blocks}

            QFrame#glow_bar {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {BRAND_START}, stop:1 {BRAND_END});
                border-radius: 2px;
            }}

            QLabel#idle_icon {{
                font-size: 60px;
                padding: 6px 0;
            }}

            QFrame#status_badge {{
                background: rgba(255,255,255,0.8);
                border: 1px solid rgba(255,255,255,0.95);
                border-radius: 22px;
            }}

            QLabel#status_text {{
                font-size: 32px;
                font-weight: 900;
                color: #0f172a;
                letter-spacing: 0.5px;
            }}

            QLabel#status_subtitle {{
                font-size: 14px;
                font-weight: 500;
                color: #334155;
                padding-top: 2px;
            }}

            QLabel#confidence_pill {{
                background: rgba(15, 23, 42, 0.06);
                border: 1px solid rgba(15, 23, 42, 0.1);
                border-radius: 12px;
                padding: 4px 14px;
                font-size: 12px;
                font-weight: 700;
                color: #334155;
                letter-spacing: 0.3px;
            }}

            QFrame#reasons_panel {{
                background: rgba(255,255,255,0.55);
                border: 1px solid rgba(255,255,255,0.8);
                border-radius: 18px;
            }}

            QLabel#reason_row {{
                font-size: 13px;
                font-weight: 500;
                color: #1e293b;
            }}

            QLabel#section_title {{
                font-size: 14px;
                font-weight: 800;
                color: #0f172a;
                letter-spacing: 0.6px;
            }}

            QLabel#section_subtitle {{
                font-size: 12px;
                font-weight: 500;
                color: #64748b;
            }}

            QLabel#ai_avatar {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {BRAND_START}, stop:1 {BRAND_END});
                border-radius: 19px;
                font-size: 16px;
                color: white;
            }}

            QFrame#ai_card {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255,255,255,0.98), stop:1 rgba(248,250,252,0.96));
                border-radius: 24px;
                border: 1px solid #dbeafe;
            }}

            QFrame#ai_card:hover {{
                border: 1px solid #93c5fd;
            }}

            QTextBrowser#ai_text {{
                background: transparent;
                border: none;
                color: #1e293b;
                font-size: 14px;
                font-weight: 500;
            }}

            QFrame#tip_card {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255,255,255,0.98), stop:1 rgba(248,250,252,0.96));
                border-radius: 20px;
                border: 1px solid #e2e8f0;
            }}

            QFrame#tip_card:hover {{
                background: white;
                border: 1px solid #bfdbfe;
            }}

            QLabel#tip_text {{
                color: #334155;
                font-size: 13px;
                font-weight: 500;
            }}

            QLabel {{
                color: #0f172a;
            }}
        """)