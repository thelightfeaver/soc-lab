"""Empaqueta SOC Lab como aplicación autónoma con PyInstaller.

Uso:  uv run --group release python scripts/build_app.py

Genera dist/soclab-<versión>-<so>-<arquitectura>.(zip|tar.gz) con la carpeta
de la aplicación (incluye Python, Qt, fuentes y los 20 retos). Podman sigue
siendo necesario en el equipo para los entornos de análisis.
"""

import platform
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soclab import __version__  # noqa: E402

DIST = ROOT / "dist"
BUILD = ROOT / "build"
NAME = "soclab"
# Módulos Qt que la app no usa: excluirlos reduce el paquete a la mitad.
EXCLUDED_QT = [
    "QtWebEngineCore", "QtWebEngineWidgets", "QtWebEngineQuick", "QtWebChannel",
    "Qt3DCore", "Qt3DRender", "QtCharts", "QtDataVisualization", "QtGraphs",
    "QtMultimedia", "QtMultimediaWidgets", "QtQuick", "QtQuick3D", "QtQml",
    "QtPdf", "QtPdfWidgets", "QtBluetooth", "QtNfc", "QtPositioning", "QtLocation",
    "QtSensors", "QtSerialPort", "QtSql", "QtTest", "QtDesigner", "QtSpatialAudio",
    "QtRemoteObjects", "QtScxml", "QtTextToSpeech", "QtHttpServer", "QtWebSockets",
]  # fmt: skip


def platform_tag() -> str:
    system = {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux")
    machine = platform.machine().lower().replace("amd64", "x86_64").replace("aarch64", "arm64")
    return f"{system}-{machine}"


def build() -> Path:
    shutil.rmtree(BUILD, ignore_errors=True)
    shutil.rmtree(DIST / NAME, ignore_errors=True)
    args = [
        sys.executable, "-m", "PyInstaller", str(ROOT / "packaging" / "soclab_app.py"),
        "--name", NAME, "--noconfirm", "--clean", "--onedir",
        "--distpath", str(DIST), "--workpath", str(BUILD), "--specpath", str(BUILD),
        "--collect-data", "soclab",
        "--paths", str(ROOT / "src"),
    ]  # fmt: skip
    if sys.platform in {"win32", "darwin"}:
        args.append("--windowed")
    for module in EXCLUDED_QT:
        args += ["--exclude-module", f"PySide6.{module}"]
    subprocess.run(args, check=True, cwd=ROOT)
    return DIST / NAME


def verify(app_dir: Path) -> None:
    """Comprueba que los datos imprescindibles viajan dentro del paquete."""
    internal = app_dir / "_internal" / "soclab"
    required = [
        internal / "builtin_challenges" / "01-ssh-bruteforce" / "challenge.toml",
        internal / "builtin_challenges" / "11-cron-persistence" / "files" / "rootfs" / "etc"
        / "cron.d" / ".sysupdate",
        internal / "containers" / "base" / "Containerfile",
        internal / "ui" / "fonts" / "IBMPlexSans-Regular.ttf",
    ]  # fmt: skip
    missing = [str(p.relative_to(app_dir)) for p in required if not p.is_file()]
    challenges = list((internal / "builtin_challenges").glob("*/challenge.toml"))
    if missing or len(challenges) != 20:
        raise SystemExit(f"Paquete incompleto: faltan {missing}, retos={len(challenges)}")


def archive(app_dir: Path) -> Path:
    base = f"{NAME}-{__version__}-{platform_tag()}"
    if sys.platform == "win32":
        out = Path(shutil.make_archive(str(DIST / base), "zip", DIST, NAME))
    else:  # tar conserva permisos de ejecución
        out = DIST / f"{base}.tar.gz"
        with tarfile.open(out, "w:gz") as tar:
            tar.add(app_dir, arcname=NAME)
    return out


def main() -> None:
    app_dir = build()
    verify(app_dir)
    out = archive(app_dir)
    print(f"Paquete listo: {out} ({out.stat().st_size / 1_048_576:.0f} MiB)")


if __name__ == "__main__":
    main()
