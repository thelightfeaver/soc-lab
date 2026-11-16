"""Lectura y validación estricta de manifiestos ``challenge.toml``."""

import re
import tomllib
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from soclab import flags

MANIFEST_NAME = "challenge.toml"
FILES_DIR = "files"
SCHEMA_VERSION = 1
SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
MAX_HINTS = 5
HINT_TEXT_LIMITS = (3, 1000)
MAX_MANIFEST_BYTES = 256 * 1024


class Difficulty(StrEnum):
    FACIL = "facil"
    MEDIO = "medio"
    DIFICIL = "dificil"
    EXPERTO = "experto"

    @property
    def label(self) -> str:
        return {"facil": "Fácil", "medio": "Medio", "dificil": "Difícil", "experto": "Experto"}[
            self.value
        ]

    @property
    def rank(self) -> int:
        return list(Difficulty).index(self)


class ManifestError(ValueError):
    """Manifiesto inválido. ``errors`` contiene todos los problemas encontrados."""

    def __init__(self, path: Path, errors: list[str]) -> None:
        self.path = path
        self.errors = errors
        super().__init__(f"{path}: " + "; ".join(errors))


@dataclass(frozen=True, slots=True)
class HintSpec:
    text: str
    cost: int


@dataclass(frozen=True, slots=True)
class Manifest:
    slug: str
    title: str
    category: str
    difficulty: Difficulty
    points: int
    summary: str
    description: str
    flag_format: str
    flag_hash: str
    case_sensitive: bool
    author: str
    root: Path
    containerfile: str | None = None
    hints: tuple[HintSpec, ...] = field(default_factory=tuple)

    @property
    def files_dir(self) -> Path:
        return self.root / FILES_DIR

    @property
    def containerfile_path(self) -> Path | None:
        return self.root / self.containerfile if self.containerfile else None


_TOP_KEYS = {
    "schema_version", "slug", "title", "category", "difficulty", "points", "summary",
    "description", "flag_format", "flag_hash", "case_sensitive", "author", "container", "hints",
}  # fmt: skip


class _Validator:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data
        self.errors: list[str] = []

    def text(self, key: str, *, min_len: int = 1, max_len: int = 200) -> str:
        value = self.data.get(key)
        if not isinstance(value, str):
            self.errors.append(f"'{key}' es obligatorio y debe ser texto")
            return ""
        value = value.strip()
        if not min_len <= len(value) <= max_len:
            self.errors.append(f"'{key}' debe tener entre {min_len} y {max_len} caracteres")
        return value

    def integer(self, key: str, low: int, high: int) -> int:
        value = self.data.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
            self.errors.append(f"'{key}' debe ser un entero entre {low} y {high}")
            return low
        return value


def _safe_relative(root: Path, rel: str) -> bool:
    candidate = (root / rel).resolve()
    return candidate.is_relative_to(root.resolve()) and not Path(rel).is_absolute()


def parse_manifest(data: dict[str, Any], root: Path) -> Manifest:
    """Valida el contenido de un manifiesto ya cargado. Lanza ``ManifestError``."""
    v = _Validator(data)
    unknown = sorted(set(data) - _TOP_KEYS)
    if unknown:
        v.errors.append(f"claves desconocidas: {', '.join(unknown)}")
    if data.get("schema_version") != SCHEMA_VERSION:
        v.errors.append(f"'schema_version' debe ser {SCHEMA_VERSION}")

    slug = v.text("slug", min_len=3, max_len=64)
    if slug and not SLUG_PATTERN.fullmatch(slug):
        v.errors.append("'slug' solo admite minúsculas, dígitos y guiones (3-64)")
    title = v.text("title", min_len=3, max_len=120)
    category = v.text("category", min_len=2, max_len=60)
    summary = v.text("summary", min_len=5, max_len=240)
    description = v.text("description", min_len=10, max_len=20_000)
    flag_format = v.text("flag_format", min_len=5, max_len=120)
    author = v.text("author", min_len=2, max_len=80) if "author" in data else "Anónimo"
    points = v.integer("points", 1, 1000)

    difficulty = Difficulty.FACIL
    try:
        difficulty = Difficulty(data.get("difficulty"))
    except ValueError:
        v.errors.append("'difficulty' debe ser: " + ", ".join(d.value for d in Difficulty))

    flag_hash = data.get("flag_hash")
    if not isinstance(flag_hash, str) or not flags.is_valid_hash(flag_hash):
        v.errors.append("'flag_hash' inválido (genéralo con `soclab hash-flag`)")
        flag_hash = ""

    case_sensitive = data.get("case_sensitive", False)
    if not isinstance(case_sensitive, bool):
        v.errors.append("'case_sensitive' debe ser true/false")
        case_sensitive = False

    containerfile: str | None = None
    container = data.get("container")
    if container is not None:
        if not isinstance(container, dict) or set(container) - {"containerfile"}:
            v.errors.append("'[container]' solo admite la clave 'containerfile'")
        else:
            cf = container.get("containerfile", "Containerfile")
            if not isinstance(cf, str) or not _safe_relative(root, cf):
                v.errors.append("'container.containerfile' debe ser una ruta relativa al reto")
            elif not (root / cf).is_file():
                v.errors.append(f"no existe el Containerfile '{cf}'")
            else:
                containerfile = cf

    hints: list[HintSpec] = []
    raw_hints = data.get("hints", [])
    if not isinstance(raw_hints, list) or len(raw_hints) > MAX_HINTS:
        v.errors.append(f"'hints' debe ser una lista de máximo {MAX_HINTS} pistas")
        raw_hints = []
    for index, hint in enumerate(raw_hints, start=1):
        if (
            not isinstance(hint, dict)
            or set(hint) != {"text", "cost"}
            or not isinstance(hint["text"], str)
            or not HINT_TEXT_LIMITS[0] <= len(hint["text"].strip()) <= HINT_TEXT_LIMITS[1]
            or not isinstance(hint["cost"], int)
            or isinstance(hint["cost"], bool)
            or not 0 <= hint["cost"] <= points
        ):
            v.errors.append(f"pista {index}: requiere 'text' (3-1000) y 'cost' (0..points)")
            continue
        hints.append(HintSpec(text=hint["text"].strip(), cost=hint["cost"]))

    if v.errors:
        raise ManifestError(root / MANIFEST_NAME, v.errors)
    return Manifest(
        slug=slug,
        title=title,
        category=category,
        difficulty=difficulty,
        points=points,
        summary=summary,
        description=description,
        flag_format=flag_format,
        flag_hash=flag_hash,
        case_sensitive=case_sensitive,
        author=author,
        root=root,
        containerfile=containerfile,
        hints=tuple(hints),
    )


def load_manifest(challenge_dir: Path) -> Manifest:
    path = challenge_dir / MANIFEST_NAME
    if not path.is_file():
        raise ManifestError(path, ["no existe challenge.toml"])
    if path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ManifestError(path, ["el manifiesto supera 256 KiB"])
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise ManifestError(path, [f"TOML inválido: {exc}"]) from exc
    return parse_manifest(data, challenge_dir.resolve())


def discover(root: Path) -> tuple[list[Manifest], list[ManifestError]]:
    """Carga todos los retos (subdirectorios con challenge.toml) de ``root``."""
    manifests: list[Manifest] = []
    errors: list[ManifestError] = []
    if not root.is_dir():
        return manifests, errors
    for child in sorted(p for p in root.iterdir() if p.is_dir()):
        if not (child / MANIFEST_NAME).exists():
            continue
        try:
            manifests.append(load_manifest(child))
        except ManifestError as exc:
            errors.append(exc)
    return manifests, errors
