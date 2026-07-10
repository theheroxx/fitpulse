# ui/desktop/widgets/history_tab.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSplitter, QDialog, QMessageBox,
    QCheckBox, QGraphicsDropShadowEffect, QSizePolicy,
    QGraphicsOpacityEffect,
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath

from datetime import datetime
import json, os, uuid

from database.db import get_latest_experience, get_all_experience_records


# ─────────────────────────────────────────────────────────────────
#  Design tokens  (identical to home.py so the app feels cohesive)
# ─────────────────────────────────────────────────────────────────
NAVY       = "#0D1B2A"
BLUE       = "#2979FF"
BLUE_LIGHT = "#E8F0FE"
MINT       = "#00E5A0"
AMBER      = "#F59E0B"
RED        = "#EF4444"
GREEN      = "#10B981"
WHITE      = "#FFFFFF"
BG         = "#F0F4FA"
CARD_BG    = "#FFFFFF"
BORDER     = "#E3EAF2"
TEXT_HEAD  = "#0D1B2A"
TEXT_BODY  = "#3D5166"
TEXT_MUTED = "#8BA0B8"

MOOD = {
    "😊": {"bg": "#ECFDF5", "border": "#6EE7B7", "bar": GREEN,  "label": "Good"},
    "😐": {"bg": "#FFFBEB", "border": "#FCD34D", "bar": AMBER,  "label": "Neutral"},
    "☹️": {"bg": "#FEF2F2", "border": "#FCA5A5", "bar": RED,    "label": "Tough"},
}

STATUS_STYLE = {
    "SAFE":          {"color": GREEN, "bg": "#ECFDF5", "border": "#6EE7B7"},
    "MODERATE RISK": {"color": AMBER, "bg": "#FFFBEB", "border": "#FCD34D"},
    "UNSAFE":        {"color": RED,   "bg": "#FEF2F2", "border": "#FCA5A5"},
}


# ─────────────────────────────────────────────────────────────────
#  Shared elevated card base
# ─────────────────────────────────────────────────────────────────
class _Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        sh = QGraphicsDropShadowEffect(self)
        sh.setBlurRadius(14)
        sh.setOffset(0, 3)
        sh.setColor(QColor(13, 27, 42, 16))
        self.setGraphicsEffect(sh)
        self._sh = sh
        self._anim = QPropertyAnimation(sh, b"blurRadius")
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def enterEvent(self, e):
        self._anim.stop(); self._anim.setEndValue(28); self._anim.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._anim.stop(); self._anim.setEndValue(14); self._anim.start()
        super().leaveEvent(e)


# ─────────────────────────────────────────────────────────────────
#  Accent bar helper
# ─────────────────────────────────────────────────────────────────
def _bar(color: str) -> QFrame:
    f = QFrame()
    f.setFixedWidth(4)
    f.setStyleSheet(
        f"background:{color}; border-top-left-radius:16px;"
        f" border-bottom-left-radius:16px;"
    )
    return f


# ─────────────────────────────────────────────────────────────────
#  Diet Check-in Card
# ─────────────────────────────────────────────────────────────────
class ExperienceEntryCard(_Card):
    selection_changed = Signal()

    def __init__(self, entry_data):
        super().__init__()
        self.entry_data = entry_data
        self._build()

    def _build(self):
        emoji = self.entry_data.get("emoji", "😐")
        m = MOOD.get(emoji, MOOD["😐"])
        value = self.entry_data.get("experience", "neutral").capitalize()
        ts = self.entry_data.get("created_at", "")

        # ── Safe timestamp formatting ──────────────────────────────
        if isinstance(ts, datetime):
            formatted_ts = ts.strftime("%b %d, %Y  %I:%M %p")
        elif isinstance(ts, str):
            try:
                dt = datetime.fromisoformat(ts)
                formatted_ts = dt.strftime("%b %d, %Y  %I:%M %p")
            except (ValueError, TypeError):
                formatted_ts = str(ts)
        else:
            formatted_ts = ""

        self.setObjectName("expCard")
        self.setStyleSheet(f"""
            QFrame#expCard {{
                background: {m['bg']};
                border-radius: 16px;
                border: 1.5px solid {m['border']};
            }}
        """)
        self.setMinimumHeight(88)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 14, 0)
        root.setSpacing(0)

        root.addWidget(_bar(m['bar']))
        root.addSpacing(14)

        # Big emoji
        el = QLabel(emoji)
        el.setFixedSize(52, 52)
        el.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.setStyleSheet("font-size: 28px; background: transparent;")
        root.addWidget(el)
        root.addSpacing(12)

        # Text block
        col = QVBoxLayout()
        col.setSpacing(2)
        col.setContentsMargins(0, 12, 0, 12)

        chip = QLabel("DIET CHECK-IN")
        chip.setStyleSheet(
            f"color:{m['bar']}; font-size:10px; font-weight:700;"
            f" letter-spacing:1px; background:transparent;"
        )
        title = QLabel(f"Feeling {m['label']} about my diet")
        title.setStyleSheet(
            f"color:{TEXT_HEAD}; font-size:14px; font-weight:700; background:transparent;"
        )
        desc = QLabel(f"Logged as  {emoji}  {value}")
        desc.setStyleSheet(
            f"color:{TEXT_BODY}; font-size:12px; background:transparent;"
        )
        col.addWidget(chip)
        col.addWidget(title)
        col.addWidget(desc)
        col.addStretch()
        root.addLayout(col, 1)

        # Right: checkbox + timestamp
        rc = QVBoxLayout()
        rc.setContentsMargins(0, 10, 0, 10)
        rc.setSpacing(4)
        self.checkbox = QCheckBox()
        self.checkbox.toggled.connect(lambda: self.selection_changed.emit())
        rc.addWidget(self.checkbox, alignment=Qt.AlignmentFlag.AlignRight)
        rc.addStretch()
        ts_lbl = QLabel(formatted_ts)   # Use formatted_ts instead of raw ts
        ts_lbl.setStyleSheet(
            f"color:{TEXT_MUTED}; font-size:10px; background:transparent;"
        )
        ts_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        rc.addWidget(ts_lbl)
        root.addLayout(rc)

    def is_selected(self):
        return self.checkbox.isChecked()


# ─────────────────────────────────────────────────────────────────
#  AI Analysis History Card
# ─────────────────────────────────────────────────────────────────
class HistoryEntryCard(_Card):
    selection_changed = Signal()

    def __init__(self, entry_data):
        super().__init__()
        self.entry_data = entry_data
        self._build()

    def _build(self):
        status    = self.entry_data.get("status", "MODERATE RISK")
        ts        = self.entry_data.get("created_at", "")
        exp_emoji = self.entry_data.get("experience_emoji")
        sm        = STATUS_STYLE.get(status, STATUS_STYLE["MODERATE RISK"])

        self.setObjectName("aiCard")
        self.setStyleSheet(f"""
            QFrame#aiCard {{
                background: {CARD_BG};
                border-radius: 16px;
                border: 1px solid {BORDER};
            }}
            QFrame#aiCard:hover {{ border-color: #A8C4FF; }}
        """)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 14, 0)
        root.setSpacing(0)
        root.addWidget(_bar(sm["color"]))
        root.addSpacing(16)

        col = QVBoxLayout()
        col.setSpacing(8)
        col.setContentsMargins(0, 14, 0, 14)

        # Row 1: status badge + optional mood pill
        r1 = QHBoxLayout(); r1.setSpacing(8)
        badge = QLabel(status)
        badge.setStyleSheet(
            f"background:{sm['bg']}; color:{sm['color']};"
            f" border:1px solid {sm['border']}; border-radius:9px;"
            f" padding:2px 10px; font-size:10px; font-weight:800;"
        )
        badge.setFixedHeight(20)
        r1.addWidget(badge)
        if exp_emoji:
            pill = QLabel(f"{exp_emoji} mood")
            pill.setStyleSheet(
                f"background:#F6F9FF; color:{TEXT_MUTED};"
                f" border:1px solid {BORDER}; border-radius:9px;"
                f" padding:2px 10px; font-size:10px;"
            )
            pill.setFixedHeight(20)
            r1.addWidget(pill)
        r1.addStretch()
        col.addLayout(r1)

        # Title
        t = QLabel(self.entry_data.get("subtitle", "Exercise analysis"))
        t.setWordWrap(True)
        t.setStyleSheet(f"color:{TEXT_HEAD}; font-size:14px; font-weight:700;")
        col.addWidget(t)

        # Reasons box
        reasons = self.entry_data.get("reasons", [])
        if reasons:
            rf = QFrame()
            rf.setStyleSheet(
                f"background:#F6F9FF; border-radius:10px; border:1px solid {BORDER};"
            )
            rfl = QVBoxLayout(rf)
            rfl.setContentsMargins(12, 8, 12, 8)
            rfl.setSpacing(4)
            for r in reasons[:3]:
                lbl = QLabel(f"· {r}")
                lbl.setWordWrap(True)
                lbl.setStyleSheet(f"color:{TEXT_BODY}; font-size:12px;")
                rfl.addWidget(lbl)
            col.addWidget(rf)

        # AI rec box
        ai = self.entry_data.get("ai_recommendation", "")
        if ai:
            af = QFrame()
            af.setStyleSheet(
                f"background:{BLUE_LIGHT}; border-radius:10px; border:1px solid #C5D8FF;"
            )
            afl = QVBoxLayout(af)
            afl.setContentsMargins(12, 8, 12, 8)
            al = QLabel(ai)
            al.setWordWrap(True)
            al.setStyleSheet(f"color:{TEXT_HEAD}; font-size:12px;")
            afl.addWidget(al)
            col.addWidget(af)

        root.addLayout(col, 1)

        # Right col
        rc = QVBoxLayout()
        rc.setContentsMargins(0, 12, 0, 12)
        rc.setSpacing(4)
        self.checkbox = QCheckBox()
        self.checkbox.toggled.connect(lambda: self.selection_changed.emit())
        rc.addWidget(self.checkbox, alignment=Qt.AlignmentFlag.AlignRight)
        rc.addStretch()
        ts_lbl = QLabel(ts)
        ts_lbl.setStyleSheet(f"color:{TEXT_MUTED}; font-size:10px;")
        ts_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        rc.addWidget(ts_lbl)
        root.addLayout(rc)

    def is_selected(self):
        return self.checkbox.isChecked()


# ─────────────────────────────────────────────────────────────────
#  Record Summary Card (right panel)
# ─────────────────────────────────────────────────────────────────
class RecordSummaryCard(_Card):
    selection_changed = Signal()

    def __init__(self, record_data):
        super().__init__()
        self.record_data = record_data
        self._build()

    def _build(self):
        rtype  = self.record_data.get("type", "workout")
        icon   = "🏋️" if rtype == "workout" else "🍽️"
        accent = BLUE if rtype == "workout" else MINT

        self.setObjectName("recCard")
        self.setStyleSheet(f"""
            QFrame#recCard {{
                background: {CARD_BG};
                border-radius: 16px;
                border: 1px solid {BORDER};
            }}
            QFrame#recCard:hover {{ border-color: #A8C4FF; }}
        """)
        self.setMinimumHeight(84)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 14, 0)
        root.setSpacing(0)
        root.addWidget(_bar(accent))
        root.addSpacing(10)

        il = QLabel(icon)
        il.setFixedSize(48, 48)
        il.setAlignment(Qt.AlignmentFlag.AlignCenter)
        il.setStyleSheet("font-size:24px; background:transparent;")
        root.addWidget(il)
        root.addSpacing(10)

        col = QVBoxLayout()
        col.setSpacing(2)
        col.setContentsMargins(0, 12, 0, 12)

        tl = QLabel(self.record_data.get("title", "Record"))
        tl.setStyleSheet(f"color:{TEXT_HEAD}; font-size:13px; font-weight:700;")
        dl = QLabel(self.record_data.get("description", ""))
        dl.setWordWrap(True)
        dl.setStyleSheet(f"color:{TEXT_BODY}; font-size:12px;")
        ml = QLabel(
            f"Intensity: {self.record_data.get('intensity','Medium')}"
            f"   ·   Due: {self.record_data.get('due_date','')}"
        )
        ml.setStyleSheet(f"color:{TEXT_MUTED}; font-size:11px;")
        col.addWidget(tl); col.addWidget(dl); col.addWidget(ml); col.addStretch()
        root.addLayout(col, 1)

        self.checkbox = QCheckBox()
        self.checkbox.toggled.connect(lambda: self.selection_changed.emit())
        root.addWidget(self.checkbox, alignment=Qt.AlignmentFlag.AlignVCenter)

    def is_selected(self):
        return self.checkbox.isChecked()


# ─────────────────────────────────────────────────────────────────
#  AI Analysis Dialog
# ─────────────────────────────────────────────────────────────────
class HistoryAnalysisCard(QDialog):
    analyze_requested = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Combined AI Analysis")
        self.setMinimumWidth(500)
        self.selected_payloads = []
        self._build()

    def _build(self):
        self.setStyleSheet(f"""
            QDialog {{ background: {WHITE}; border-radius: 20px; }}
            QLabel  {{ background: transparent; }}
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 32, 32, 32)
        root.setSpacing(18)

        # Header
        h = QHBoxLayout(); h.setSpacing(14)
        brain = QLabel("🧠"); brain.setStyleSheet("font-size:34px;")
        h.addWidget(brain)
        vc = QVBoxLayout(); vc.setSpacing(2)
        t = QLabel("AI Health Analysis")
        t.setStyleSheet(f"color:{TEXT_HEAD}; font-size:20px; font-weight:800;")
        s = QLabel("Select entries below, then click Analyze.")
        s.setStyleSheet(f"color:{TEXT_MUTED}; font-size:13px;")
        vc.addWidget(t); vc.addWidget(s)
        h.addLayout(vc); h.addStretch()
        root.addLayout(h)

        div = QFrame(); div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"background:{BORDER}; border:none;"); div.setFixedHeight(1)
        root.addWidget(div)

        # Info box
        self.info_box = QFrame()
        self.info_box.setStyleSheet(
            f"background:{BLUE_LIGHT}; border-radius:12px; border:1px solid #C5D8FF;"
        )
        ibl = QVBoxLayout(self.info_box)
        ibl.setContentsMargins(16, 12, 16, 12)
        self.info_lbl = QLabel("No items selected. Check items in the history list first.")
        self.info_lbl.setWordWrap(True)
        self.info_lbl.setStyleSheet(f"color:{TEXT_BODY}; font-size:13px;")
        ibl.addWidget(self.info_lbl)
        root.addWidget(self.info_box)

        # Feature list
        ff = QFrame()
        ff.setStyleSheet(f"background:#F8FAFF; border-radius:12px; border:1px solid {BORDER};")
        fl = QVBoxLayout(ff); fl.setContentsMargins(18, 14, 18, 14); fl.setSpacing(8)
        lbl = QLabel("What's coming")
        lbl.setStyleSheet(f"color:{TEXT_MUTED}; font-size:10px; font-weight:700; letter-spacing:1px;")
        fl.addWidget(lbl); fl.addSpacing(2)
        for icon, text in [
            ("📈","Trend analysis over time"),
            ("🛡️","Exercise safety pattern detection"),
            ("🔁","Workout consistency tracking"),
            ("💡","AI-generated fitness recommendations"),
            ("😊","Mood & diet experience tracking"),
        ]:
            r = QHBoxLayout(); r.setSpacing(10)
            il = QLabel(icon); il.setStyleSheet("font-size:13px;"); il.setFixedWidth(18)
            tl = QLabel(text); tl.setStyleSheet(f"color:{TEXT_BODY}; font-size:13px;")
            r.addWidget(il); r.addWidget(tl); r.addStretch()
            fl.addLayout(r)
        root.addWidget(ff)

        # Button
        br = QHBoxLayout(); br.addStretch()
        self.analyze_btn = QPushButton("Analyze Selected Data")
        self.analyze_btn.setFixedHeight(46)
        self.analyze_btn.setMinimumWidth(210)
        self.analyze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.analyze_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                            stop:0 {BLUE}, stop:1 #5C6BC0);
                color:white; border:none; border-radius:13px;
                font-size:14px; font-weight:700;
                padding-left:20px; padding-right:20px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                            stop:0 #1A56DB, stop:1 #4A5BB8);
            }}
            QPushButton:pressed {{ background:#1A56DB; }}
        """)
        self.analyze_btn.clicked.connect(self._emit)
        br.addWidget(self.analyze_btn)
        root.addLayout(br)

    def set_selected_payloads(self, payloads):
        self.selected_payloads = payloads
        n = len(payloads)
        if n == 0:
            self.info_lbl.setText("No items selected. Check items in the history list first.")
        else:
            ec = sum(1 for p in payloads if p.get("type") == "experience")
            ac = n - ec
            parts = []
            if ac: parts.append(f"{ac} AI result(s)")
            if ec: parts.append(f"{ec} diet check-in(s)")
            self.info_lbl.setText(f"{' + '.join(parts)} ready for analysis.")

    def _emit(self):
        self.analyze_requested.emit(self.selected_payloads)
        self.accept()


# ─────────────────────────────────────────────────────────────────
#  Section header helper
# ─────────────────────────────────────────────────────────────────
def _section(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("sectionLbl")
    return lbl


# ─────────────────────────────────────────────────────────────────
#  Empty state helper
# ─────────────────────────────────────────────────────────────────
def _empty(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setWordWrap(True)
    lbl.setStyleSheet(f"color:{TEXT_MUTED}; font-size:13px; padding:32px;")
    return lbl


# ─────────────────────────────────────────────────────────────────
#  Scroll area factory
# ─────────────────────────────────────────────────────────────────
def _scroll() -> tuple:
    """Returns (QScrollArea, inner_QWidget, inner_QVBoxLayout)."""
    sa = QScrollArea()
    sa.setWidgetResizable(True)
    sa.setFrameShape(QFrame.Shape.NoFrame)
    sa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    sa.setStyleSheet("QScrollArea { background: transparent; border: none; }")
    inner = QWidget()
    inner.setStyleSheet("background: transparent;")
    lay = QVBoxLayout(inner)
    lay.setAlignment(Qt.AlignmentFlag.AlignTop)
    lay.setSpacing(10)
    lay.setContentsMargins(4, 4, 4, 4)
    sa.setWidget(inner)
    return sa, inner, lay


# ─────────────────────────────────────────────────────────────────
#  Main History Tab
# ─────────────────────────────────────────────────────────────────
class HistoryTab(QWidget):
    """
    Unified history tab showing diet check-ins and AI analysis results.

    Wiring requirements in MainContainer
    ─────────────────────────────────────
    1. Construct with main_container reference:
           self.history_page = HistoryTab(main_container=self)

    2. After login succeeds call:
           self.history_page.on_user_login(user_id)

    3. After logout call:
           self.history_page.on_user_logout()

    4. When a diet emoji is tapped in HomePage, call:
           self.history_page.push_experience(emoji, experience_value, record_id)
       (record_id is the int returned by save_experience_record)
    """

    def __init__(self, main_container=None):
        super().__init__()
        self.main_container  = main_container
        self._user_id        = None          # set by on_user_login()
        self.history_entries = []            # AI analysis entries (JSON-persisted)
        self.record_cards    = []
        self.history_file    = "history_storage.json"

        self._build_ui()
        self._apply_styles()
        self._load_json_history()            # load persisted AI analyses

    # ─────────────────────────────────────────────────────────────
    #  Public API called by MainContainer
    # ─────────────────────────────────────────────────────────────

    def on_user_login(self, user_id: int):
        """Call this right after login succeeds."""
        self._user_id = user_id
        self._load_experience_from_db()

    def on_user_logout(self):
        """Call this when the user logs out."""
        self._user_id = None
        # Remove experience entries (they belong to the user); keep AI analyses
        self.history_entries = [
            e for e in self.history_entries if e.get("type") != "experience"
        ]
        self._render_history()

    def push_experience(self, emoji: str, experience_value: str, record_id=None):
        """
        Called immediately after save_experience_record() in home.py.
        Inserts the new check-in at the top of the timeline without a DB round-trip.
        """
        new_id = str(record_id) if record_id else str(uuid.uuid4())
        # Guard: don't add if already present (can happen on rapid double-click)
        if any(e.get("id") == new_id and e.get("type") == "experience"
               for e in self.history_entries):
            return
        entry = {
            "id":         new_id,
            "type":       "experience",
            "emoji":      emoji,
            "experience": experience_value,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.history_entries.insert(0, entry)
        self._render_history()

    # ─────────────────────────────────────────────────────────────
    #  Called by MainContainer.on_analysis_completed
    # ─────────────────────────────────────────────────────────────
    def add_analysis_result(self, result):
        if result is None:
            return
        detector = result.get("detector", {})
        exp_emoji = None
        if self._user_id:
            try:
                exp = get_latest_experience(self._user_id)
                if exp:
                    exp_emoji = exp.get("emoji")
            except Exception:
                pass

        entry = {
            "id":                str(uuid.uuid4()),
            "type":              "analysis",
            "created_at":        datetime.now().strftime("%b %d, %Y  •  %I:%M %p"),
            "status":            self._label_to_status(detector.get("label", "Moderate")),
            "subtitle":          (detector.get("reasons") or ["Exercise analysis"])[0],
            "reasons":           detector.get("reasons", []),
            "confidence":        detector.get("confidence", 0.0),
            "score":             detector.get("score", 0),
            "ai_recommendation": result.get("final_recommendation", ""),
            "experience_emoji":  exp_emoji,
            "raw_result":        result,
        }
        self.history_entries.insert(0, entry)
        self._save_json_history()
        self._render_history()

    # ─────────────────────────────────────────────────────────────
    #  Called by MainContainer to populate the right panel
    # ─────────────────────────────────────────────────────────────
    def sync_records(self, records):
        # Clear old cards
        while self._rec_layout.count():
            item = self._rec_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self.record_cards.clear()

        if not records:
            self._rec_layout.addWidget(
                _empty("No active plans yet.\nAdd records from the Records tab.")
            )
            return

        for record in records:
            payload = {
                "title":       record.title,
                "description": record.description,
                "type":        record.record_type,
                "due_date":    record.due_date,
                "intensity":   getattr(record, "intensity", "Medium"),
            }
            card = RecordSummaryCard(payload)
            card.selection_changed.connect(self._collect_selections)
            self.record_cards.append(card)
            self._rec_layout.addWidget(card)

    # ─────────────────────────────────────────────────────────────
    #  UI build
    # ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 20)
        root.setSpacing(0)

        # ── Header row ──────────────────────────────────────────
        hdr = QHBoxLayout()
        tc = QVBoxLayout(); tc.setSpacing(2)
        title = QLabel("Smart History")
        title.setObjectName("htTitle")
        sub = QLabel("Diet check-ins, AI analyses, and active records — all in one place.")
        sub.setObjectName("htSub")
        sub.setWordWrap(True)
        tc.addWidget(title); tc.addWidget(sub)
        hdr.addLayout(tc, 1)

        self._clear_btn = QPushButton("Clear AI History")
        self._clear_btn.setObjectName("dangerBtn")
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.clicked.connect(self._clear_history)
        hdr.addWidget(self._clear_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(hdr)
        root.addSpacing(16)

        # ── Divider ─────────────────────────────────────────────
        div = QFrame(); div.setFrameShape(QFrame.Shape.HLine)
        div.setObjectName("htDiv"); div.setFixedHeight(1)
        root.addWidget(div)
        root.addSpacing(16)

        # ── Analysis dialog (created but not shown yet) ─────────
        self._analysis_dlg = HistoryAnalysisCard(self)
        self._analysis_dlg.analyze_requested.connect(self._on_analyze)

        # ── Two-column splitter ──────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)
        splitter.setStyleSheet("QSplitter::handle { background: #E3EAF2; }")

        # Left panel — timeline
        left_w = QWidget(); left_w.setStyleSheet("background:transparent;")
        left_l = QVBoxLayout(left_w)
        left_l.setContentsMargins(0, 0, 10, 0)
        left_l.setSpacing(10)
        left_l.addWidget(_section("📊  Check-ins & Analysis Timeline"))

        self._hist_scroll, _, self._hist_layout = _scroll()
        left_l.addWidget(self._hist_scroll)
        splitter.addWidget(left_w)

        # Right panel — records
        right_w = QWidget(); right_w.setStyleSheet("background:transparent;")
        right_l = QVBoxLayout(right_w)
        right_l.setContentsMargins(10, 0, 0, 0)
        right_l.setSpacing(10)
        right_l.addWidget(_section("📋  Active Plans & Records"))

        self._rec_scroll, _, self._rec_layout = _scroll()
        right_l.addWidget(self._rec_scroll)
        splitter.addWidget(right_w)

        splitter.setSizes([640, 440])
        root.addWidget(splitter, 1)

        # ── Bottom CTA ──────────────────────────────────────────
        root.addSpacing(14)
        br = QHBoxLayout(); br.addStretch()
        self._ai_btn = QPushButton("🧠  Open AI Analysis")
        self._ai_btn.setObjectName("primaryBtn")
        self._ai_btn.setFixedHeight(46)
        self._ai_btn.setMinimumWidth(210)
        self._ai_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ai_btn.clicked.connect(self._analysis_dlg.exec)
        br.addWidget(self._ai_btn); br.addStretch()
        root.addLayout(br)

    # ─────────────────────────────────────────────────────────────
    #  Render history timeline
    # ─────────────────────────────────────────────────────────────
    def _render_history(self):
        # Remove all widgets cleanly
        while self._hist_layout.count():
            item = self._hist_layout.takeAt(0)
            if item and item.widget():
                w = item.widget()
                w.hide()
                w.deleteLater()

        if not self.history_entries:
            self._hist_layout.addWidget(
                _empty(
                    "No history yet.\n\n"
                    "Tap a diet emoji on the home page\n"
                    "or run an AI analysis to get started."
                )
            )
            return

        for entry in self.history_entries:
            if entry.get("type") == "experience":
                card = ExperienceEntryCard(entry)
            else:
                card = HistoryEntryCard(entry)
            card.selection_changed.connect(self._collect_selections)
            self._hist_layout.addWidget(card)

    def refresh_records(self):
        """Re-fetch active records from the database and update the right panel."""
        if not self._user_id:
            return
        from database.db import get_user_records
        records_data = get_user_records(self._user_id)
        # Convert to simple objects or dicts (your RecordsPage uses simple dicts)
        # Assuming each record is a dict with title, description, record_type, etc.
        records = []
        for item in records_data:
            records.append(type('Record', (), {
                'title': item['title'],
                'description': item['description'],
                'record_type': item['record_type'],
                'due_date': item['due_date'],
                'intensity': item.get('intensity', 'Medium'),
                'is_done': item.get('is_done', False)
            })())
        self.sync_records(records)

    # ─────────────────────────────────────────────────────────────
    #  Selection collector
    # ─────────────────────────────────────────────────────────────
    def _collect_selections(self):
        payloads = []
        for i in range(self._hist_layout.count()):
            item = self._hist_layout.itemAt(i)
            if not item or not item.widget():
                continue
            w = item.widget()
            if isinstance(w, (HistoryEntryCard, ExperienceEntryCard)):
                if w.is_selected():
                    payloads.append(w.entry_data.copy())
        for card in self.record_cards:
            if card.is_selected():
                payloads.append(card.record_data.copy())
        self._analysis_dlg.set_selected_payloads(payloads)

    # ─────────────────────────────────────────────────────────────
    #  DB loader — runs after login
    # ─────────────────────────────────────────────────────────────
    def _load_experience_from_db(self):
        if not self._user_id:
            return
        try:
            rows = get_all_experience_records(self._user_id)
            self.history_entries = [
                e for e in self.history_entries if e.get("type") != "experience"
            ]
            for row in rows:
                self.history_entries.append({
                    "id": str(row["id"]),
                    "type": "experience",
                    "emoji": row["emoji"],
                    "experience": row["experience_value"],
                    "created_at": row["created_at"],
                })
            # Safe sort: convert to datetime for comparison
            def safe_key(e):
                val = e.get("created_at")
                if val is None:
                    return datetime.min
                if isinstance(val, datetime):
                    return val
                if isinstance(val, str):
                    try:
                        return datetime.fromisoformat(val)
                    except (ValueError, TypeError):
                        return datetime.min
                return datetime.min

            self.history_entries.sort(key=safe_key, reverse=True)
            self._render_history()
        except Exception as ex:
            print(f"[HistoryTab] _load_experience_from_db error: {ex}")

    # ─────────────────────────────────────────────────────────────
    #  JSON persistence (AI analyses only)
    # ─────────────────────────────────────────────────────────────
    def _load_json_history(self):
        if not os.path.exists(self.history_file):
            return
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # Keep only analysis entries from JSON
            for e in saved:
                if e.get("type") == "analysis":
                    self.history_entries.append(e)
            self._render_history()
        except Exception as ex:
            print(f"[HistoryTab] _load_json_history error: {ex}")

    def _save_json_history(self):
        try:
            to_save = [e for e in self.history_entries if e.get("type") == "analysis"]
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(to_save, f, indent=2, ensure_ascii=False)
        except Exception as ex:
            print(f"[HistoryTab] _save_json_history error: {ex}")

    # ─────────────────────────────────────────────────────────────
    #  Clear history
    # ─────────────────────────────────────────────────────────────
    def _clear_history(self):
        reply = QMessageBox.question(
            self, "Clear AI History",
            "Delete all AI analysis entries?\n"
            "(Diet check-ins stored in the database are kept.)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.history_entries = [
                e for e in self.history_entries if e.get("type") == "experience"
            ]
            self._save_json_history()
            self._render_history()

    # ─────────────────────────────────────────────────────────────
    #  AI analysis handler
    # ─────────────────────────────────────────────────────────────
    def _on_analyze(self, payloads):
        ec = sum(1 for p in payloads if p.get("type") == "experience")
        emojis = [p.get("emoji", "") for p in payloads if p.get("type") == "experience"]
        mood_line = f"\n\nMood ratings: {' '.join(emojis)}" if emojis else ""
        QMessageBox.information(
            self, "AI Analysis (Coming Soon)",
            f"{len(payloads)} item(s) selected.\n\n"
            "Combined health reasoning and smart recommendations "
            f"will appear here in a future update.{mood_line}",
        )

    # ─────────────────────────────────────────────────────────────
    #  Helpers
    # ─────────────────────────────────────────────────────────────
    @staticmethod
    def _label_to_status(label: str) -> str:
        return {"Unsafe": "UNSAFE", "Moderate": "MODERATE RISK"}.get(label, "SAFE")

    # ─────────────────────────────────────────────────────────────
    #  Stylesheet
    # ─────────────────────────────────────────────────────────────
    def _apply_styles(self):
        self.setStyleSheet(f"""

        HistoryTab, QWidget {{
            background: {BG};
        }}

        /* ── Page title / subtitle ── */
        QLabel#htTitle {{
            font-size: 22px;
            font-weight: 800;
            color: {TEXT_HEAD};
        }}
        QLabel#htSub {{
            font-size: 13px;
            color: {TEXT_MUTED};
        }}

        /* ── Divider ── */
        QFrame#htDiv {{
            background: {BORDER};
            border: none;
        }}

        /* ── Section headers ── */
        QLabel#sectionLbl {{
            font-size: 12px;
            font-weight: 700;
            color: {TEXT_BODY};
            letter-spacing: 0.5px;
        }}

        /* ── Scrollbar ── */
        QScrollBar:vertical {{
            background: transparent;
            width: 5px;
            border-radius: 3px;
        }}
        QScrollBar::handle:vertical {{
            background: {BORDER};
            border-radius: 3px;
            min-height: 24px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

        /* ── Primary button ── */
        QPushButton#primaryBtn {{
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 {BLUE}, stop:1 #5C6BC0);
            color: white;
            border: none;
            border-radius: 13px;
            font-size: 14px;
            font-weight: 700;
        }}
        QPushButton#primaryBtn:hover {{
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 #1A56DB, stop:1 #4A5BB8);
        }}
        QPushButton#primaryBtn:pressed {{ background: #1A56DB; }}

        /* ── Danger button ── */
        QPushButton#dangerBtn {{
            background: transparent;
            color: {RED};
            border: 1.5px solid #FCA5A5;
            border-radius: 11px;
            padding: 7px 16px;
            font-size: 12px;
            font-weight: 600;
        }}
        QPushButton#dangerBtn:hover {{
            background: #FEF2F2;
            border-color: {RED};
        }}
        QPushButton#dangerBtn:pressed {{ background: #FEE2E2; }}

        /* ── Checkbox ── */
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border-radius: 4px;
            border: 1.5px solid {BORDER};
            background: white;
        }}
        QCheckBox::indicator:checked {{
            background: {BLUE};
            border-color: {BLUE};
        }}

        """)