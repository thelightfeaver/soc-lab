"""Tema «Expediente forense»: papel, tinta y sello.

Cada reto es un caso; la hoja blanca es el informe y el sello rojo marca los
casos resueltos. El color se reserva para significado: dificultad, selección
(etiqueta de evidencia amarilla), acción principal (azul archivo) y sello.
"""

from pathlib import Path

from PySide6.QtGui import QFontDatabase

from soclab.manifest import Difficulty

FONTS_DIR = Path(__file__).resolve().parent / "fonts"

PAPER = "#E9EDF1"  # fondo: carpeta gris azulada
SHEET = "#FFFFFF"  # hoja del informe
INK = "#1F2A37"
INK_SOFT = "#5B6878"
INK_FAINT = "#8592A3"
RULE = "#CBD3DC"
ARCHIVE = "#1F3A5F"  # acción principal
ARCHIVE_HOVER = "#2B4F7E"
STAMP = "#B3261E"  # sello «Resuelto»
TAG = "#FFF6D6"  # etiqueta de evidencia (selección)
TAG_EDGE = "#E3C766"
SUCCESS = "#2F7D4F"
WARNING = "#9A6B00"
DANGER = STAMP

# Solo familias empaquetadas en ui/fonts: nombrar fuentes ausentes obliga a Qt a
# construir alias en cada arranque (aviso "Populating font family aliases").
SANS = '"IBM Plex Sans"'
SERIF = '"Source Serif 4"'
MONO = '"IBM Plex Mono"'

DIFFICULTY_COLORS: dict[Difficulty, str] = {
    Difficulty.FACIL: "#2F7D4F",
    Difficulty.MEDIO: "#9A6B00",
    Difficulty.DIFICIL: "#B4531A",
    Difficulty.EXPERTO: "#6B3FA0",
}


def load_fonts() -> None:
    """Registra las fuentes empaquetadas (OFL) para un aspecto idéntico en todo SO."""
    for font in sorted(FONTS_DIR.glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(font))


STYLESHEET = f"""
* {{ color: {INK}; font-family: {SANS}; font-size: 10pt; }}
QMainWindow, QWidget#central, QScrollArea,
QScrollArea > QWidget > QWidget {{ background: {PAPER}; }}
QMenuBar {{ background: {PAPER}; border-bottom: 1px solid {RULE}; }}
QMenuBar::item {{ padding: 4px 10px; background: transparent; }}
QMenuBar::item:selected, QMenu::item:selected {{ background: {TAG}; color: {INK}; }}
QMenu {{ background: {SHEET}; border: 1px solid {RULE}; padding: 4px; }}
QMenu::item {{ padding: 6px 18px; }}
QStatusBar {{ background: {PAPER}; color: {INK_SOFT}; border-top: 1px solid {RULE}; }}

QFrame#sidebar {{ background: {PAPER}; border-right: 1px solid {RULE}; }}
QFrame#sheet {{ background: {SHEET}; border: 1px solid {RULE}; }}
QFrame#section {{ background: transparent; border-top: 1px solid {RULE}; }}

QLabel#brand {{ font-family: {SERIF}; font-size: 19pt; font-weight: 600; }}
QLabel#case_number {{ color: {INK_SOFT}; font-size: 10pt; }}
QLabel#h1 {{ font-family: {SERIF}; font-size: 24pt; font-weight: 600; }}
QLabel#h2 {{ font-family: {SERIF}; font-size: 14pt; font-weight: 600; }}
QLabel#lede {{ font-family: {SERIF}; font-size: 13pt; color: {INK_SOFT}; }}
QLabel#muted {{ color: {INK_SOFT}; }}
QLabel#faint {{ color: {INK_FAINT}; font-size: 9pt; }}
QLabel#feedback_ok {{ color: {SUCCESS}; font-weight: 600; }}
QLabel#feedback_err {{ color: {DANGER}; font-weight: 600; }}
QLabel#feedback_warn {{ color: {WARNING}; font-weight: 600; }}

QTextBrowser#report {{
    background: {SHEET}; border: none; font-family: {SERIF}; font-size: 12pt;
    selection-background-color: {TAG}; selection-color: {INK};
}}
QLineEdit, QComboBox {{
    background: {SHEET}; border: 1px solid {RULE}; border-radius: 3px; padding: 6px 8px;
    selection-background-color: {TAG}; selection-color: {INK};
}}
QLineEdit:focus, QComboBox:focus {{ border: 1px solid {ARCHIVE}; }}
QLineEdit:disabled {{ background: {PAPER}; color: {INK_FAINT}; }}
QLineEdit#flag {{
    font-family: {MONO}; font-size: 11pt; border: none; border-bottom: 2px solid {INK};
    border-radius: 0; padding: 6px 2px; background: transparent;
}}
QLineEdit#flag:focus {{ border-bottom: 2px solid {ARCHIVE}; }}
QLineEdit#command {{ font-family: {MONO}; background: {PAPER}; color: {INK}; }}
QComboBox QAbstractItemView {{
    background: {SHEET}; border: 1px solid {RULE};
    selection-background-color: {TAG}; selection-color: {INK};
}}

QPushButton {{
    background: {SHEET}; border: 1px solid {RULE}; border-radius: 3px; padding: 7px 14px;
}}
QPushButton:hover {{ border-color: {INK_SOFT}; }}
QPushButton:focus {{ border: 1px solid {ARCHIVE}; }}
QPushButton:disabled {{ color: {INK_FAINT}; background: {PAPER}; border-color: {RULE}; }}
QPushButton#primary {{
    background: {ARCHIVE}; color: {SHEET}; border: 1px solid {ARCHIVE}; font-weight: 600;
}}
QPushButton#primary:hover {{ background: {ARCHIVE_HOVER}; }}
QPushButton#primary:focus {{ border: 2px solid {INK}; }}
QPushButton#primary:disabled {{ background: {RULE}; border-color: {RULE}; color: {INK_SOFT}; }}
QPushButton#link {{
    border: none; background: transparent; color: {ARCHIVE}; padding: 4px 0; text-align: left;
}}
QPushButton#link:hover {{ text-decoration: underline; }}
QPushButton#link:disabled {{ color: {INK_FAINT}; background: transparent; }}
QPushButton#danger {{ color: {STAMP}; border-color: {STAMP}; }}

QListView#cases {{ background: transparent; border: none; outline: none; }}
QProgressBar {{ background: {RULE}; border: none; border-radius: 0; max-height: 6px; }}
QProgressBar::chunk {{ background: {INK}; }}
QSplitter::handle {{ background: {RULE}; width: 1px; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: {RULE}; border-radius: 4px; min-height: 28px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; }}
QScrollBar::handle:horizontal {{ background: {RULE}; border-radius: 4px; min-width: 28px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QToolTip {{ background: {SHEET}; color: {INK}; border: 1px solid {RULE}; padding: 4px; }}
QMessageBox {{ background: {SHEET}; }}
"""
