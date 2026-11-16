"""Arranque de la aplicación gráfica."""

import sys

from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from soclab import __version__
from soclab.config import BUILTIN_CHALLENGES_DIR, db_path, imported_challenges_dir
from soclab.db import init_database
from soclab.podman import PodmanClient
from soclab.services import LabService
from soclab.ui.main_window import MainWindow
from soclab.ui.theme import STYLESHEET, load_fonts


def build_window() -> MainWindow:
    db = init_database(db_path())
    service = LabService(db)
    errors = service.load_directory(BUILTIN_CHALLENGES_DIR, "builtin")
    errors += service.load_directory(imported_challenges_dir(), "imported")
    window = MainWindow(service, PodmanClient())
    if errors:
        QMessageBox.warning(
            window,
            "Retos con errores",
            "Algunos retos no se cargaron:\n\n" + "\n".join(str(e) for e in errors[:10]),
        )
    return window


def run() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("SOC Lab")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("soclab")
    app.setStyle("Fusion")
    load_fonts()
    app.setFont(QFont("IBM Plex Sans", 10))  # evita buscar la fuente por defecto del SO
    app.setStyleSheet(STYLESHEET)
    app.setWindowIcon(QIcon.fromTheme("security-high"))
    window = build_window()
    window.show()
    return app.exec()
