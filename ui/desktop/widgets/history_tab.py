# ui/desktop/widgets/history_tab.py

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from datetime import datetime
import json
import os
import uuid

from database.db import get_latest_experience


class HistoryAnalysisCard(QDialog):

    analyze_requested = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Combined AI Analysis")
        self.setMinimumWidth(450)

        self.selected_payloads = []

        self.setup_ui()

    def setup_ui(self):

        self.setObjectName("analysis_card")

        root = QVBoxLayout(self)

        root.setContentsMargins(28, 28, 28, 28)

        root.setSpacing(18)

        # =====================================================
        # HEADER
        # =====================================================

        top = QHBoxLayout()

        icon = QLabel("🧠")

        icon.setStyleSheet("""
            font-size: 34px;
        """)

        top.addWidget(icon)

        titles = QVBoxLayout()

        title = QLabel(
            "Combined AI Analysis"
        )

        title.setObjectName(
            "analysis_title"
        )

        subtitle = QLabel(
            "Select analyses and records for future intelligent health reasoning"
        )

        subtitle.setObjectName(
            "analysis_subtitle"
        )

        titles.addWidget(title)

        titles.addWidget(subtitle)

        top.addLayout(titles)

        top.addStretch()

        root.addLayout(top)

        # =====================================================
        # INFO BOX
        # =====================================================

        self.info_box = QLabel(
            "No items selected yet."
        )

        self.info_box.setObjectName(
            "analysis_info"
        )

        self.info_box.setWordWrap(True)

        root.addWidget(
            self.info_box
        )

        # =====================================================
        # FUTURE FEATURES
        # =====================================================

        features_box = QFrame()

        features_box.setStyleSheet("""
            background: rgba(255,255,255,0.65);
            border-radius: 18px;
            border: 1px solid #dbeafe;
        """)

        features_layout = QVBoxLayout(
            features_box
        )

        features_layout.setContentsMargins(
            20,
            20,
            20,
            20
        )

        features_layout.setSpacing(10)

        features = [

            "• Trend analysis over time",

            "• Exercise safety pattern detection",

            "• Workout consistency tracking",

            "• AI-generated fitness recommendations",

            "• Health-risk prediction system",

            "• Smart scheduling assistant",

            "• Experience tracking (😊 😐 ☹️)"

        ]

        for feature in features:

            lbl = QLabel(feature)

            lbl.setStyleSheet("""
                color: #334155;
                font-size: 13px;
            """)

            features_layout.addWidget(lbl)

        root.addWidget(
            features_box
        )

        # =====================================================
        # BUTTON
        # =====================================================

        button_row = QHBoxLayout()

        button_row.addStretch()

        self.analyze_btn = QPushButton(
            "Analyze Selected Data"
        )

        self.analyze_btn.setFixedHeight(48)

        self.analyze_btn.setMinimumWidth(220)

        self.analyze_btn.clicked.connect(
            self.emit_analysis_request
        )

        button_row.addWidget(
            self.analyze_btn
        )

        root.addLayout(button_row)

    def set_selected_payloads(self, payloads):

        self.selected_payloads = payloads

        count = len(payloads)

        if count == 0:

            self.info_box.setText(
                "No items selected yet."
            )

        else:

            # Count experiences in selection
            exp_count = sum(1 for p in payloads if p.get("type") == "experience")
            exp_text = f" • {exp_count} experience(s)" if exp_count > 0 else ""

            self.info_box.setText(
                f"{count} item(s) selected for future AI analysis.{exp_text}"
            )

    def emit_analysis_request(self):

        self.analyze_requested.emit(
            self.selected_payloads
        )
        # Close the dialog once analysis starts
        self.accept()


# ui/desktop/widgets/history_tab.py

class HistoryEntryCard(QFrame):

    selection_changed = Signal()

    def __init__(self, entry_data, user_id=None):
        super().__init__()

        self.entry_data = entry_data
        self.user_id = user_id

        self.setup_ui()

    def setup_ui(self):

        self.setObjectName(
            "history_entry"
        )

        self.setMinimumHeight(240)

        root = QVBoxLayout(self)

        root.setContentsMargins(
            24,
            24,
            24,
            24
        )

        root.setSpacing(16)

        # =====================================================
        # HEADER
        # =====================================================

        header = QHBoxLayout()

        self.checkbox = QCheckBox()

        self.checkbox.toggled.connect(lambda: self.selection_changed.emit())
        header.addWidget(
            self.checkbox
        )

        status = self.entry_data.get(
            "status",
            "Moderate"
        )

        status_color = {
            "SAFE": "#10b981",
            "MODERATE RISK": "#f59e0b",
            "UNSAFE": "#ef4444"
        }.get(status, "#64748b")

        badge = QLabel(status)

        badge.setStyleSheet(f"""
            background: {status_color};
            color: white;
            padding: 6px 14px;
            border-radius: 14px;
            font-size: 11px;
            font-weight: 800;
        """)

        header.addWidget(
            badge
        )

        # =====================================================
        # EXPERIENCE EMOJI (NEW)
        # =====================================================
        
        # Get experience emoji from entry data
        experience_emoji = self.entry_data.get("experience_emoji")
        
        if experience_emoji:
            exp_label = QLabel(experience_emoji)
            exp_label.setStyleSheet("""
                font-size: 28px;
                background: rgba(255,255,255,0.8);
                border-radius: 20px;
                padding: 4px 12px;
                border: 1px solid #e2e8f0;
            """)
            exp_label.setToolTip("This analysis was saved after a mood/experience rating")
            header.addWidget(exp_label)
            header.addSpacing(8)

        timestamp = QLabel(
            self.entry_data.get(
                "created_at",
                ""
            )
        )

        timestamp.setObjectName(
            "timestamp"
        )

        header.addStretch()

        header.addWidget(
            timestamp
        )

        root.addLayout(header)

        # =====================================================
        # MAIN RESULT
        # =====================================================

        title = QLabel(
            self.entry_data.get(
                "subtitle",
                "Exercise analysis"
            )
        )

        title.setObjectName(
            "entry_title"
        )

        title.setWordWrap(True)

        root.addWidget(title)

        # =====================================================
        # REASONS
        # =====================================================

        reasons = self.entry_data.get(
            "reasons",
            []
        )

        if reasons:

            reason_box = QFrame()

            reason_box.setObjectName(
                "reason_box"
            )

            reason_layout = QVBoxLayout(
                reason_box
            )

            reason_layout.setSpacing(10)

            reason_layout.setContentsMargins(
                16,
                16,
                16,
                16
            )

            for reason in reasons[:3]:

                lbl = QLabel(
                    f"• {reason}"
                )

                lbl.setWordWrap(True)

                lbl.setObjectName(
                    "reason_label"
                )

                reason_layout.addWidget(lbl)

            root.addWidget(reason_box)

        # =====================================================
        # AI RECOMMENDATION
        # =====================================================

        ai_text = self.entry_data.get(
            "ai_recommendation",
            ""
        )

        if ai_text:

            ai_card = QFrame()

            ai_card.setObjectName(
                "mini_ai_card"
            )

            ai_layout = QVBoxLayout(
                ai_card
            )

            ai_layout.setContentsMargins(
                16,
                16,
                16,
                16
            )

            ai_label = QLabel(ai_text)

            ai_label.setWordWrap(True)

            ai_label.setObjectName(
                "mini_ai_text"
            )

            ai_layout.addWidget(ai_label)

            root.addWidget(ai_card)

    def is_selected(self):
        return self.checkbox.isChecked()


class RecordSummaryCard(QFrame):

    selection_changed = Signal()

    def __init__(self, record_data):
        super().__init__()

        self.record_data = record_data

        self.setup_ui()

    def setup_ui(self):

        self.setObjectName(
            "record_summary_card"
        )

        layout = QHBoxLayout(self)

        layout.setContentsMargins(
            20,
            18,
            20,
            18
        )

        layout.setSpacing(18)

        self.checkbox = QCheckBox()

        self.checkbox.toggled.connect(lambda: self.selection_changed.emit())

        layout.addWidget(
            self.checkbox
        )

        icon = QLabel(
            "🏋️"
            if self.record_data["type"] == "workout"
            else "🍽️"
        )

        icon.setStyleSheet(
            "font-size: 28px;"
        )

        layout.addWidget(icon)

        content = QVBoxLayout()

        title = QLabel(
            self.record_data["title"]
        )

        title.setObjectName(
            "record_title"
        )

        content.addWidget(title)

        desc = QLabel(
            self.record_data["description"]
        )

        desc.setWordWrap(True)

        desc.setObjectName(
            "record_desc"
        )

        content.addWidget(desc)

        meta = QLabel(
            f"Intensity: {self.record_data.get('intensity', 'Medium')}   •   Due: {self.record_data.get('due_date', '')}"
        )

        meta.setObjectName(
            "record_meta"
        )

        content.addWidget(meta)

        layout.addLayout(content)

    def is_selected(self):

        return self.checkbox.isChecked()


class HistoryTab(QWidget):

    def __init__(self, main_container=None):
        super().__init__()

        self.main_container = main_container
        self.history_entries = []
        self.record_cards = []
        self.history_file = "history_storage.json"

        self.setup_ui()
        self.load_history()

    # =========================================================
    # UI
    # =========================================================

    def setup_ui(self):

        root = QVBoxLayout(self)

        root.setContentsMargins(
            24,
            24,
            24,
            24
        )

        root.setSpacing(20)

        # =====================================================
        # HEADER
        # =====================================================

        header = QHBoxLayout()

        title_layout = QVBoxLayout()

        title = QLabel(
            "🕓 Smart History"
        )

        title.setObjectName(
            "history_title"
        )

        subtitle = QLabel(
            "Track AI analyses, records, workout planning and future intelligent insights"
        )

        subtitle.setObjectName(
            "history_subtitle"
        )

        title_layout.addWidget(title)

        title_layout.addWidget(subtitle)

        header.addLayout(title_layout)

        header.addStretch()

        self.clear_btn = QPushButton(
            "Clear History"
        )

        self.clear_btn.clicked.connect(
            self.clear_history
        )

        header.addWidget(
            self.clear_btn
        )

        root.addLayout(header)

        # Initialize the pop-up Analysis Card
        self.analysis_card = HistoryAnalysisCard(self)
        self.analysis_card.analyze_requested.connect(self.on_analyze_combined)

        # =====================================================
        # SPLITTER
        # =====================================================

        splitter = QSplitter()

        splitter.setOrientation(
            Qt.Horizontal
        )

        # =====================================================
        # HISTORY SIDE
        # =====================================================

        left_widget = QWidget()

        left_layout = QVBoxLayout(
            left_widget
        )

        left_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        history_label = QLabel(
            "📊 Analysis Results"
        )

        history_label.setObjectName(
            "section_header"
        )

        left_layout.addWidget(
            history_label
        )

        self.history_scroll = QScrollArea()

        self.history_scroll.setWidgetResizable(
            True
        )

        self.history_scroll.setFrameShape(
            QFrame.NoFrame
        )

        self.history_container = QWidget()

        self.history_layout = QVBoxLayout(
            self.history_container
        )

        self.history_layout.setAlignment(
            Qt.AlignTop
        )

        self.history_layout.setSpacing(
            16
        )

        self.history_scroll.setWidget(
            self.history_container
        )

        left_layout.addWidget(
            self.history_scroll
        )

        splitter.addWidget(
            left_widget
        )

        # =====================================================
        # RECORDS SIDE
        # =====================================================

        right_widget = QWidget()

        right_layout = QVBoxLayout(
            right_widget
        )

        right_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        records_label = QLabel(
            "📋 Active Plans & Records"
        )

        records_label.setObjectName(
            "section_header"
        )

        right_layout.addWidget(
            records_label
        )

        self.records_scroll = QScrollArea()

        self.records_scroll.setWidgetResizable(
            True
        )

        self.records_scroll.setFrameShape(
            QFrame.NoFrame
        )

        self.records_container = QWidget()

        self.records_layout = QVBoxLayout(
            self.records_container
        )

        self.records_layout.setAlignment(
            Qt.AlignTop
        )

        self.records_layout.setSpacing(
            16
        )

        self.records_scroll.setWidget(
            self.records_container
        )

        right_layout.addWidget(
            self.records_scroll
        )

        splitter.addWidget(
            right_widget
        )

        splitter.setSizes(
            [700, 500]
        )

        root.addWidget(
            splitter,
            1
        )

        # =====================================================
        # POP-UP BUTTON
        # =====================================================
        
        popup_layout = QHBoxLayout()
        popup_layout.addStretch()

        self.open_popup_btn = QPushButton("🧠 Open AI Analysis")
        self.open_popup_btn.setFixedHeight(48)
        self.open_popup_btn.setMinimumWidth(220)
        
        self.open_popup_btn.clicked.connect(self.analysis_card.exec)

        popup_layout.addWidget(self.open_popup_btn)
        popup_layout.addStretch()

        root.addLayout(popup_layout)

        self.apply_styles()

    # =========================================================
    # GET USER ID
    # =========================================================

    def get_user_id(self):
        if self.main_container and hasattr(self.main_container, 'current_user'):
            return self.main_container.current_user.get('id')
        return None

    # =========================================================
    # SAVE ANALYSIS
    # =========================================================

    def add_analysis_result(self, result):

        if result is None:
            return

        detector = result.get(
            "detector",
            {}
        )

        # Get latest experience emoji for this user
        experience_emoji = None
        user_id = self.get_user_id()
        if user_id:
            try:
                exp_data = get_latest_experience(user_id)
                if exp_data:
                    experience_emoji = exp_data.get("emoji")
            except:
                pass

        final_data = {

            "id":
                str(uuid.uuid4()),

            "created_at":
                datetime.now().strftime(
                    "%b %d, %Y • %I:%M %p"
                ),

            "status":
                self.extract_status(
                    detector.get(
                        "label",
                        "Moderate"
                    )
                ),

            "subtitle":
                detector.get(
                    "reasons",
                    ["Exercise analysis"]
                )[0],

            "reasons":
                detector.get(
                    "reasons",
                    []
                ),

            "confidence":
                detector.get(
                    "confidence",
                    0.0
                ),

            "score":
                detector.get(
                    "score",
                    0
                ),

            "ai_recommendation":
                result.get(
                    "final_recommendation",
                    ""
                ),

            "experience_emoji":
                experience_emoji,  # NEW: Store experience emoji

            "raw_result":
                result
        }

        self.history_entries.insert(
            0,
            final_data
        )

        self.save_history()

        self.render_history()

    def extract_status(self, label):

        if label == "Unsafe":
            return "UNSAFE"

        if label == "Moderate":
            return "MODERATE RISK"

        return "SAFE"

    # =========================================================
    # RECORDS INTEGRATION
    # =========================================================

    def sync_records(self, records):

        for i in reversed(
            range(
                self.records_layout.count()
            )
        ):

            item = self.records_layout.itemAt(i)

            if item and item.widget():
                item.widget().deleteLater()

        self.record_cards.clear()

        for record in records:

            payload = {

                "title":
                    record.title,

                "description":
                    record.description,

                "type":
                    record.record_type,

                "due_date":
                    record.due_date,

                "intensity":
                    getattr(
                        record,
                        "intensity",
                        "Medium"
                    )
            }

            card = RecordSummaryCard(
                payload
            )

            card.selection_changed.connect(
                self.collect_selected_items
            )

            self.record_cards.append(
                card
            )

            self.records_layout.addWidget(
                card
            )

        self.records_layout.addStretch()

    # =========================================================
    # RENDER HISTORY
    # =========================================================

    def render_history(self):

        for i in reversed(
            range(
                self.history_layout.count()
            )
        ):

            item = self.history_layout.itemAt(i)

            if item and item.widget():
                item.widget().deleteLater()

        user_id = self.get_user_id()

        for entry in self.history_entries:

            card = HistoryEntryCard(
                entry,
                user_id
            )

            card.selection_changed.connect(
                self.collect_selected_items
            )

            self.history_layout.addWidget(
                card
            )

        self.history_layout.addStretch()

    # =========================================================
    # COLLECT SELECTIONS
    # =========================================================

    def collect_selected_items(self):

        payloads = []

        for i in range(self.history_layout.count()):
            item = self.history_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, HistoryEntryCard):
                    if widget.is_selected():
                        entry = widget.entry_data.copy()
                        # Ensure experience emoji is included
                        payloads.append(entry)

        for card in self.record_cards:
            if card.is_selected():
                payloads.append(card.record_data)

        self.analysis_card.set_selected_payloads(payloads)

    # =========================================================
    # AI ANALYSIS PLACEHOLDER
    # =========================================================

    def on_analyze_combined(self, payloads):

        # Count experiences in selection
        exp_count = sum(1 for p in payloads if p.get("type") == "experience")
        exp_emojis = [p.get("experience_emoji") for p in payloads if p.get("experience_emoji")]
        
        exp_text = ""
        if exp_count > 0:
            exp_text = f"\n\nExperience emojis: {' '.join(exp_emojis)}"

        QMessageBox.information(
            self,
            "Future AI Analysis",
            (
                f"{len(payloads)} items selected.\n\n"
                "This is where future AI trend analysis,\n"
                "combined health reasoning,\n"
                "and smart recommendations will happen."
                f"{exp_text}"
            )
        )

    # =========================================================
    # STORAGE
    # =========================================================

    def save_history(self):

        try:

            with open(
                self.history_file,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    self.history_entries,
                    f,
                    indent=4,
                    ensure_ascii=False
                )

        except Exception as e:

            print(
                f"History save error: {e}"
            )

    def load_history(self):

        if not os.path.exists(
            self.history_file
        ):

            return

        try:

            with open(
                self.history_file,
                "r",
                encoding="utf-8"
            ) as f:

                self.history_entries = (
                    json.load(f)
                )

            self.render_history()

        except Exception as e:

            print(
                f"History load error: {e}"
            )

    def clear_history(self):

        reply = QMessageBox.question(
            self,
            "Clear History",
            "Delete all analysis history?",
            QMessageBox.Yes |
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:

            self.history_entries.clear()

            self.save_history()

            self.render_history()

    # =========================================================
    # STYLES
    # =========================================================

    def apply_styles(self):

        self.setStyleSheet("""

            QWidget {

                background: #f8fbff;
            }

            QLabel#history_title {

                font-size: 30px;

                font-weight: 900;

                color: #0f172a;
            }

            QLabel#history_subtitle {

                font-size: 14px;

                color: #64748b;
            }

            QLabel#section_header {

                font-size: 16px;

                font-weight: 800;

                color: #0f172a;

                padding-bottom: 8px;
            }

            QFrame#history_entry {

                background:
                    qlineargradient(
                        x1:0,
                        y1:0,
                        x2:1,
                        y2:1,
                        stop:0 #ffffff,
                        stop:1 #f8fafc
                    );

                border-radius: 26px;

                border: 1px solid #dbeafe;
            }

            QFrame#history_entry:hover {

                border: 1px solid #93c5fd;
            }

            QLabel#entry_title {

                font-size: 17px;

                font-weight: 800;

                color: #1e293b;
            }

            QLabel#timestamp {

                color: #94a3b8;

                font-size: 11px;
            }

            QFrame#reason_box {

                background: #eff6ff;

                border-radius: 18px;
            }

            QLabel#reason_label {

                color: #334155;

                font-size: 13px;
            }

            QFrame#mini_ai_card {

                background: white;

                border-radius: 18px;

                border: 1px solid #e2e8f0;
            }

            QLabel#mini_ai_text {

                color: #1e293b;

                font-size: 13px;

                line-height: 1.7;
            }

            QFrame#record_summary_card {

                background: white;

                border-radius: 22px;

                border: 1px solid #e2e8f0;
            }

            QLabel#record_title {

                font-size: 14px;

                font-weight: 800;

                color: #0f172a;
            }

            QLabel#record_desc {

                font-size: 12px;

                color: #475569;
            }

            QLabel#record_meta {

                font-size: 11px;

                color: #94a3b8;
            }

            QDialog#analysis_card {

                background:
                    qlineargradient(
                        x1:0,
                        y1:0,
                        x2:1,
                        y2:1,
                        stop:0 #dbeafe,
                        stop:1 #ede9fe
                    );

                border-radius: 28px;

                border: 1px solid #c4b5fd;
            }

            QLabel#analysis_title {

                font-size: 20px;

                font-weight: 900;

                color: #0f172a;
            }

            QLabel#analysis_subtitle {

                font-size: 13px;

                color: #475569;
            }

            QLabel#analysis_info {

                background:
                    rgba(255,255,255,0.75);

                border-radius: 18px;

                padding: 18px;

                color: #334155;

                font-size: 13px;

                line-height: 1.8;
            }

            QPushButton {

                background:
                    qlineargradient(
                        x1:0,
                        y1:0,
                        x2:1,
                        y2:0,
                        stop:0 #2563eb,
                        stop:1 #7c3aed
                    );

                color: white;

                border: none;

                border-radius: 14px;

                padding: 12px 22px;

                font-size: 13px;

                font-weight: 700;
            }

            QPushButton:hover {

                margin-top: -1px;
            }

            QScrollArea {

                border: none;

                background: transparent;
            }

        """)