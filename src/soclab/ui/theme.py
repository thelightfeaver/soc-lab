"""Paleta y hoja de estilos (tema oscuro tipo consola SOC)."""

from soclab.manifest import Difficulty

BG = "#0b1220"
PANEL = "#111a2e"
SURFACE = "#18233b"
BORDER = "#26354f"
TEXT = "#e2e8f0"
MUTED = "#8fa0b8"
ACCENT = "#22d3ee"
SUCCESS = "#22c55e"
WARNING = "#f59e0b"
DANGER = "#ef4444"

DIFFICULTY_COLORS: dict[Difficulty, str] = {
    Difficulty.FACIL: "#22c55e",
    Difficulty.MEDIO: "#eab308",
    Difficulty.DIFICIL: "#f97316",
    Difficulty.EXPERTO: "#a855f7",
}

STYLESHEET = f"""
* {{ color: {TEXT}; font-size: 10pt; }}
QMainWindow, QWidget#central, QScrollArea, QScrollArea > QWidget > QWidget {{ background: {BG}; }}
QMenuBar {{ background: {PANEL}; border-bottom: 1px solid {BORDER}; }}
QMenuBar::item:selected, QMenu::item:selected {{ background: {SURFACE}; color: {ACCENT}; }}
QMenu {{ background: {PANEL}; border: 1px solid {BORDER}; }}
QStatusBar {{ background: {PANEL}; color: {MUTED}; border-top: 1px solid {BORDER}; }}
QFrame#card {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 10px; }}
QFrame#sidebar {{ background: {PANEL}; border-right: 1px solid {BORDER}; }}
QLabel#h1 {{ font-size: 20pt; font-weight: 700; }}
QLabel#h2 {{ font-size: 12pt; font-weight: 600; color: {ACCENT}; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#score {{ font-size: 28pt; font-weight: 800; color: {ACCENT}; }}
QLabel#badge {{ border-radius: 9px; padding: 2px 10px; font-weight: 600; }}
QLabel#feedback_ok {{ color: {SUCCESS}; font-weight: 700; }}
QLabel#feedback_err {{ color: {DANGER}; font-weight: 600; }}
QLabel#feedback_warn {{ color: {WARNING}; font-weight: 600; }}
QLineEdit, QComboBox, QTextBrowser, QPlainTextEdit {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 6px; padding: 6px;
    selection-background-color: {ACCENT}; selection-color: {BG};
}}
QLineEdit:focus, QComboBox:focus {{ border: 1px solid {ACCENT}; }}
QLineEdit#flag {{
    font-family: "JetBrains Mono", "Cascadia Code", Menlo, Consolas, monospace; font-size: 11pt;
}}
QLineEdit#command {{ font-family: Menlo, Consolas, monospace; color: {ACCENT}; }}
QComboBox QAbstractItemView {{ background: {SURFACE}; border: 1px solid {BORDER}; }}
QPushButton {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 6px; padding: 7px 14px;
}}
QPushButton:hover {{ border-color: {ACCENT}; }}
QPushButton:focus {{ border: 1px solid {ACCENT}; }}
QPushButton:disabled {{ color: {MUTED}; background: {PANEL}; }}
QPushButton#primary {{ background: {ACCENT}; color: {BG}; font-weight: 700; border: none; }}
QPushButton#primary:hover {{ background: #67e8f9; }}
QPushButton#primary:disabled {{ background: {BORDER}; color: {MUTED}; }}
QPushButton#danger {{ border-color: {DANGER}; color: {DANGER}; }}
QTableView {{
    background: {PANEL}; alternate-background-color: {SURFACE}; border: none;
    gridline-color: {BORDER}; selection-background-color: #164e63; selection-color: {TEXT};
}}
QTableView::item {{ padding: 6px; }}
QHeaderView::section {{
    background: {PANEL}; color: {MUTED}; border: none; border-bottom: 1px solid {BORDER};
    padding: 6px; font-weight: 600;
}}
QProgressBar {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 6px; height: 14px;
    text-align: center; color: {TEXT};
}}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 5px; }}
QScrollBar:vertical {{ background: {BG}; width: 10px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 5px; min-height: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QToolTip {{ background: {SURFACE}; color: {TEXT}; border: 1px solid {ACCENT}; }}
"""


def badge_style(color: str) -> str:
    # Qt interpreta #RRGGBBAA como #AARRGGBB: la transparencia va con rgba().
    r, g, b = (int(color[i : i + 2], 16) for i in (1, 3, 5))
    return f"background: rgba({r}, {g}, {b}, 40); color: {color}; border: 1px solid {color};"
