"""Punto de entrada: ``soclab`` abre la UI; subcomandos para autores de retos."""

import argparse
import getpass
import sys
from pathlib import Path

from soclab import __version__, flags
from soclab.manifest import ManifestError, discover, load_manifest


def _cmd_hash(args: argparse.Namespace) -> int:
    value = args.flag or getpass.getpass("Flag (no se mostrará): ")
    try:
        print(flags.hash_flag(value, case_sensitive=args.case_sensitive))  # noqa: T201
    except flags.FlagError as exc:
        print(f"error: {exc}", file=sys.stderr)  # noqa: T201
        return 2
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    path: Path = args.path
    if (path / "challenge.toml").is_file():
        try:
            manifest = load_manifest(path)
        except ManifestError as exc:
            print(f"✗ {exc}", file=sys.stderr)  # noqa: T201
            return 1
        print(f"✓ {manifest.slug}: {manifest.title}")  # noqa: T201
        return 0
    manifests, errors = discover(path)
    for m in manifests:
        print(f"✓ {m.slug}: {m.title}")  # noqa: T201
    for err in errors:
        print(f"✗ {err}", file=sys.stderr)  # noqa: T201
    if not manifests and not errors:
        print("No se encontraron retos.", file=sys.stderr)  # noqa: T201
        return 1
    return 1 if errors else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="soclab", description="Laboratorio SOC con Podman.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    gui = sub.add_parser("gui", help="abrir la interfaz gráfica (por defecto)")
    gui.set_defaults(func=None)

    hasher = sub.add_parser("hash-flag", help="generar el flag_hash para challenge.toml")
    hasher.add_argument("flag", nargs="?", help="flag SOC{...} (si se omite, se pide oculta)")
    hasher.add_argument("--case-sensitive", action="store_true")
    hasher.set_defaults(func=_cmd_hash)

    validate = sub.add_parser("validate", help="validar un reto o una carpeta de retos")
    validate.add_argument("path", type=Path)
    validate.set_defaults(func=_cmd_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # consolas Windows sin UTF-8 no deben romper
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(errors="replace")
    args = build_parser().parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        from soclab.ui.app import run  # noqa: PLC0415 - Qt solo se carga para la UI

        return run()
    return func(args)
