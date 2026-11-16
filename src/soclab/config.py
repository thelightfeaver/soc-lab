"""Rutas y constantes de la aplicación."""

import os
import sys
from pathlib import Path

APP_NAME = "soclab"
PACKAGE_DIR = Path(__file__).resolve().parent
BUILTIN_CHALLENGES_DIR = PACKAGE_DIR / "builtin_challenges"
BASE_IMAGE_DIR = PACKAGE_DIR / "containers" / "base"
BASE_IMAGE_TAG = "localhost/soclab-base:1"


def data_dir() -> Path:
    """Directorio de datos del usuario (BD y retos importados).

    Se puede forzar con la variable de entorno ``SOCLAB_HOME``.
    """
    override = os.environ.get("SOCLAB_HOME")
    if override:
        base = Path(override).expanduser()
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / APP_NAME
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        xdg = os.environ.get("XDG_DATA_HOME")
        base = (Path(xdg) if xdg else Path.home() / ".local" / "share") / APP_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def db_path() -> Path:
    return data_dir() / "soclab.db"


def imported_challenges_dir() -> Path:
    path = data_dir() / "challenges"
    path.mkdir(parents=True, exist_ok=True)
    return path
