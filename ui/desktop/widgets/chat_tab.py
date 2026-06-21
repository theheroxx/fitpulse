# ui/desktop/widgets/chat_tab.py
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from ui.desktop.workers.chat_worker import ChatWorker
from ui.desktop.workers.rag_worker import RAGWorker

# =========================================================
# Animated Message Bubble (unchanged)
# =========================================================
class AnimatedMessage(QWidget):
    def __init__(self, role, content):
        super().__init__()
        self.role = role
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0)
        self.setup_ui(content)
        QTimer.singleShot(50, self.animate_in)

    def setup_ui(self, content):
        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.bubble = QFrame()
        self.bubble.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.bubble.setMaximumWidth(820)

        bubble_layout = QVBoxLayout(self.bubble)
        bubble_layout.setContentsMargins(18, 14, 18, 14)

        self.label = QLabel(content)
        self.label.setWordWrap(True)
        self.label.setTextFormat(Qt.PlainText)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.label.setFont(QFont("Segoe UI", 11))

        metrics = QFontMetrics(self.label.font())
        estimated_width = metrics.horizontalAdvance(content[:120]) + 40
        estimated_width = max(140, min(760, estimated_width))
        self.label.setMaximumWidth(estimated_width)
        self.label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        bubble_layout.addWidget(self.label)

        if self.role == "user":
            self.bubble.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6366f1, stop:1 #8b5cf6);
                    border-radius: 22px;
                }
                QLabel {
                    background: transparent; color: white; border: none; line-height: 1.5;
                }
            """)
            outer_layout.addStretch()
            outer_layout.addWidget(self.bubble)
        else:
            self.bubble.setStyleSheet("""
                QFrame {
                    background: white; border: 1px solid #e2e8f0; border-radius: 22px;
                }
                QLabel {
                    background: transparent; color: #1e293b; border: none; line-height: 1.6;
                }
            """)
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(30)
            shadow.setOffset(0, 6)
            shadow.setColor(QColor(15, 23, 42, 30))
            self.bubble.setGraphicsEffect(shadow)
            outer_layout.addWidget(self.bubble)
            outer_layout.addStretch()

    def animate_in(self):
        fade = QPropertyAnimation(self.opacity_effect, b"opacity")
        fade.setDuration(320)
        fade.setStartValue(0)
        fade.setEndValue(1)
        fade.setEasingCurve(QEasingCurve.OutCubic)

        slide = QPropertyAnimation(self, b"pos")
        current_pos = self.pos()
        if self.role == "user":
            start_pos = QPoint(current_pos.x() + 40, current_pos.y() + 20)
        else:
            start_pos = QPoint(current_pos.x() - 40, current_pos.y() + 20)
        slide.setStartValue(start_pos)
        slide.setEndValue(current_pos)
        slide.setDuration(380)
        slide.setEasingCurve(QEasingCurve.OutBack)

        grow = QPropertyAnimation(self.bubble, b"maximumWidth")
        final_width = self.bubble.sizeHint().width()
        grow.setDuration(280)
        grow.setStartValue(int(final_width * 0.82))
        grow.setEndValue(final_width)
        grow.setEasingCurve(QEasingCurve.OutBack)

        self.anim_group = QParallelAnimationGroup()
        self.anim_group.addAnimation(fade)
        self.anim_group.addAnimation(slide)
        self.anim_group.addAnimation(grow)
        self.anim_group.start()


# =========================================================
# Chat Tab
# =========================================================
class ChatTab(QWidget):
    def __init__(self):
        super().__init__()
        self.chat_model = "gemma3:4b"
        self.messages = []
        self.context = None
        self.worker = None
        self.rag_worker = None
        self.detailed_mode = False
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet("QWidget { background: #f8fafc; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea { border: none; background: #f8fafc; }
            QScrollBar:vertical { background: transparent; width: 10px; margin: 6px; }
            QScrollBar::handle:vertical { background: #cbd5e1; border-radius: 5px; min-height: 30px; }
            QScrollBar::handle:vertical:hover { background: #94a3b8; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)

        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background: #f8fafc;")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_layout.setSpacing(14)
        self.chat_layout.setContentsMargins(24, 24, 24, 24)
        self.chat_layout.setSizeConstraint(QLayout.SetMinAndMaxSize)

        self.scroll_area.setWidget(self.chat_container)
        layout.addWidget(self.scroll_area)
        self.add_welcome()

        input_wrapper = QWidget()
        input_wrapper.setFixedHeight(140)
        input_wrapper.setStyleSheet("QWidget { background: white; border-top: 1px solid #e2e8f0; }")

        main_input_layout = QVBoxLayout(input_wrapper)
        main_input_layout.setContentsMargins(20, 12, 20, 12)
        main_input_layout.setSpacing(12)

        toggle_layout = QHBoxLayout()
        toggle_layout.setSpacing(12)

        self.detail_toggle = QPushButton("🔬 Detailed Answer")
        self.detail_toggle.setCheckable(True)
        self.detail_toggle.setCursor(Qt.PointingHandCursor)
        self.detail_toggle.setFixedHeight(36)
        self.detail_toggle.setStyleSheet("""
            QPushButton {
                background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 18px;
                padding: 0 16px; color: #475569; font-size: 12px; font-weight: 500;
            }
            QPushButton:checked {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6366f1, stop:1 #8b5cf6);
                color: white; border: none;
            }
            QPushButton:hover { background: #e2e8f0; }
        """)
        self.detail_toggle.toggled.connect(self.on_detailed_toggle)

        tooltip_label = QLabel("ℹ️")
        tooltip_label.setCursor(Qt.PointingHandCursor)
        tooltip_label.setToolTip("Detailed answers give more accurate, science-based responses.")
        tooltip_label.setStyleSheet("color: #94a3b8; font-size: 14px;")

        toggle_layout.addWidget(self.detail_toggle)
        toggle_layout.addWidget(tooltip_label)
        toggle_layout.addStretch()
        main_input_layout.addLayout(toggle_layout)

        input_layout = QHBoxLayout()
        input_layout.setSpacing(14)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Ask something about your fitness analysis...")
        self.input.setMinimumHeight(52)
        self.input.setStyleSheet("""
            QLineEdit {
                background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 16px;
                padding: 0 18px; color: #0f172a; font-size: 13px;
            }
            QLineEdit:focus { border: 2px solid #818cf8; background: white; }
        """)
        self.input.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input)

        self.send_btn = QPushButton("Send")
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setFixedSize(90, 52)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6366f1, stop:1 #8b5cf6);
                color: white; border: none; border-radius: 16px; font-size: 13px; font-weight: 700;
            }
            QPushButton:hover { background: #5855eb; }
            QPushButton:pressed { padding-top: 2px; }
            QPushButton:disabled { background: #cbd5e1; color: white; }
        """)
        self.send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_btn)

        main_input_layout.addLayout(input_layout)
        layout.addWidget(input_wrapper)

    def on_detailed_toggle(self, checked):
        self.detailed_mode = checked
        if checked:
            self.add_message("assistant", "🔬 **Detailed Answer Mode Enabled**")
        else:
            self.add_message("assistant", "⚡ **Standard Mode Enabled**")

    def add_welcome(self):
        self.add_message("assistant", "👋 Hi! I'm your AI fitness coach.\n\nRun an analysis first, then ask me questions.")

    def add_message(self, role, content, animated=True):
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        if animated:
            message = AnimatedMessage(role, content)
        else:
            message = QLabel(content)
            message.setWordWrap(True)
            message.setFont(QFont("Segoe UI", 11))
            message.setStyleSheet("color: #64748b; background: transparent; padding: 8px 16px; font-style: italic;")
            if role == "user":
                message.setAlignment(Qt.AlignRight)
        wrapper_layout.addWidget(message)
        self.messages.append(wrapper)
        self.chat_layout.addWidget(wrapper)
        QTimer.singleShot(120, self.scroll_to_bottom)

    def scroll_to_bottom(self):
        scrollbar = self.scroll_area.verticalScrollBar()
        animation = QPropertyAnimation(scrollbar, b"value")
        animation.setDuration(320)
        animation.setStartValue(scrollbar.value())
        animation.setEndValue(scrollbar.maximum())
        animation.setEasingCurve(QEasingCurve.OutCubic)
        self.scroll_animation = animation
        animation.start()

    def set_analysis_context(self, result):
        self.context = result

    def send_message(self):
        question = self.input.text().strip()
        if not question:
            return

        if self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait(3000)
            self.worker = None

        if self.rag_worker and self.rag_worker.isRunning():
            self.rag_worker.quit()
            self.rag_worker.wait(3000)
            self.rag_worker = None

        self.input.clear()
        self.send_btn.setEnabled(False)
        self.input.setEnabled(False)
        self.add_message("user", question)

        context_text = ""
        health = "Unknown"
        activity = "Unknown"

        if self.context:
            user_data = self.context.get('user_data', {})
            ed_score = self.context.get("ED", "N/A")
            status = self.context.get("detector", {}).get("label", "N/A")
            age = user_data.get('Age', 'N/A')
            health = user_data.get('HealthCondition', 'N/A')
            fitness = user_data.get('FitnessLevel', 'N/A')
            activity = user_data.get('ActivityType', 'N/A')
            context_text = f"""
User Profile: {age} years old, {health}, {fitness} fitness
Activity: {activity}
Environmental Risk: {ed_score}/100 ({status})
"""

        base_prompt = f"""You are an AI fitness coach. {context_text}

User question: {question}

Provide a helpful, concise answer (2-3 sentences). Be practical and safety-focused."""

        if not self.detailed_mode:
            self.worker = ChatWorker(base_prompt, self.chat_model)
            self.worker.response_ready.connect(self.on_response_received)
            self.worker.error.connect(self.on_error)
            self.worker.start()
            return

        # DETAILED MODE — RAG on QThread
        self.add_message("assistant", "🔍 Retrieving medical context...", animated=False)
        self.pending_context_text = context_text
        self.pending_question = question
        self.pending_base_prompt = base_prompt

        self.rag_worker = RAGWorker(question, health, activity)
        self.rag_worker.progress.connect(lambda msg: print(f"[RAG] {msg}"))
        self.rag_worker.context_ready.connect(self.on_rag_complete)
        self.rag_worker.error.connect(self.on_rag_error)
        self.rag_worker.start()

    def on_rag_complete(self, rag_context):
        context_text = self.pending_context_text
        question = self.pending_question
        base_prompt = self.pending_base_prompt

        if self.rag_worker:
            self.rag_worker.quit()
            self.rag_worker.wait(5000)
            self.rag_worker = None

        if rag_context and rag_context.strip():
            prompt = f"""You are an AI fitness coach using EVIDENCE-BASED MEDICAL CONTEXT.

{context_text}

{rag_context}

User question: {question}

Provide a DETAILED, SCIENTIFIC answer based on the retrieved medical context above. 
Cite specific information from the context. Be thorough (3-5 sentences)."""
        else:
            prompt = base_prompt

        self.worker = ChatWorker(prompt, self.chat_model)
        self.worker.response_ready.connect(self.on_response_received)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_rag_error(self, error_msg):
        print(f"RAG error: {error_msg}")
        base_prompt = self.pending_base_prompt

        if self.rag_worker:
            self.rag_worker.quit()
            self.rag_worker.wait(5000)
            self.rag_worker = None

        self.add_message("assistant", f"⚠️ Could not retrieve medical context.\nAnswering with general knowledge.\n", animated=False)
        self.worker = ChatWorker(base_prompt, self.chat_model)
        self.worker.response_ready.connect(self.on_response_received)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_response_received(self, response):
        self.add_message("assistant", response)
        self.send_btn.setEnabled(True)
        self.input.setEnabled(True)
        self.input.setFocus()
        if self.worker:
            self.worker.quit()
            self.worker.wait(3000)
        self.worker = None

    def on_error(self, error_msg):
        self.add_message("assistant", f"⚠️ Error: {error_msg}\n\nMake sure Ollama is running.")
        self.send_btn.setEnabled(True)
        self.input.setEnabled(True)
        self.input.setFocus()
        if self.worker:
            self.worker.quit()
            self.worker.wait(3000)
        self.worker = None

    def clear_chat(self):
        if self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait(3000)
            self.worker = None
        if self.rag_worker and self.rag_worker.isRunning():
            self.rag_worker.quit()
            self.rag_worker.wait(3000)
            self.rag_worker = None
        for msg in self.messages:
            msg.deleteLater()
        self.messages.clear()
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.add_welcome()