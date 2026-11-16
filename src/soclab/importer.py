"""Importación segura de retos desde carpeta o ZIP."""

import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from soclab.manifest import MANIFEST_NAME, Manifest, load_manifest

MAX_TOTAL_BYTES = 50 * 1024 * 1024
MAX_FILES = 500
MAX_RATIO = 100  # descompresión máxima permitida por archivo (anti zip-bomb)


class ChallengeImportError(ValueError):
    """Error al importar un reto."""


def _check_member(info: zipfile.ZipInfo) -> None:
    name = PurePosixPath(info.filename)
    if name.is_absolute() or ".." in name.parts or "\\" in info.filename or ":" in info.filename:
        raise ChallengeImportError(f"ruta no permitida en el ZIP: {info.filename}")
    if stat.S_ISLNK(info.external_attr >> 16):
        raise ChallengeImportError(f"enlaces simbólicos no permitidos: {info.filename}")
    if info.compress_size and info.file_size / info.compress_size > MAX_RATIO:
        raise ChallengeImportError(f"ratio de compresión sospechoso: {info.filename}")


def safe_extract(archive: Path, target: Path) -> None:
    """Extrae un ZIP validando rutas, tamaño, número de archivos y symlinks."""
    try:
        zf = zipfile.ZipFile(archive)
    except zipfile.BadZipFile as exc:
        raise ChallengeImportError("el archivo no es un ZIP válido") from exc
    with zf:
        members = zf.infolist()
        if len(members) > MAX_FILES:
            raise ChallengeImportError(f"el ZIP tiene más de {MAX_FILES} entradas")
        total = 0
        for info in members:
            _check_member(info)
            total += info.file_size
            if total > MAX_TOTAL_BYTES:
                raise ChallengeImportError("el contenido descomprimido supera 50 MiB")
        root = target.resolve()
        for info in members:
            dest = (root / info.filename).resolve()
            if not dest.is_relative_to(root):
                raise ChallengeImportError(f"ruta fuera del destino: {info.filename}")
            if info.is_dir():
                dest.mkdir(parents=True, exist_ok=True)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, dest.open("wb") as out:
                shutil.copyfileobj(src, out)


def _find_root(extracted: Path) -> Path:
    if (extracted / MANIFEST_NAME).is_file():
        return extracted
    candidates = [p for p in extracted.iterdir() if p.is_dir() and (p / MANIFEST_NAME).is_file()]
    if len(candidates) != 1:
        raise ChallengeImportError("el paquete debe contener un único challenge.toml")
    return candidates[0]


def _check_tree(root: Path) -> None:
    count, total = 0, 0
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ChallengeImportError(f"enlaces simbólicos no permitidos: {path.name}")
        if path.is_file():
            count += 1
            total += path.stat().st_size
    if count > MAX_FILES or total > MAX_TOTAL_BYTES:
        raise ChallengeImportError("el reto supera los límites (500 archivos / 50 MiB)")


def stage_challenge(source: Path, workdir: Path) -> Manifest:
    """Copia/extrae ``source`` en ``workdir`` y valida el manifiesto."""
    if source.is_dir():
        _check_tree(source)
        staged = workdir / "pkg"
        shutil.copytree(source, staged, symlinks=True)
    elif source.is_file() and source.suffix.lower() == ".zip":
        staged = workdir / "pkg"
        staged.mkdir()
        safe_extract(source, staged)
    else:
        raise ChallengeImportError("selecciona una carpeta o un archivo .zip")
    root = _find_root(staged)
    _check_tree(root)
    return load_manifest(root)


def install_challenge(
    source: Path,
    destination_root: Path,
    *,
    reserved_slugs: set[str],
    replace: bool = False,
) -> Manifest:
    """Valida e instala un reto en ``destination_root/<slug>``.

    ``reserved_slugs`` son slugs que no pueden sobrescribirse (retos incluidos).
    """
    with tempfile.TemporaryDirectory(prefix="soclab-import-") as tmp:
        manifest = stage_challenge(source, Path(tmp))
        if manifest.slug in reserved_slugs:
            raise ChallengeImportError(f"el slug '{manifest.slug}' pertenece a un reto incluido")
        dest = destination_root / manifest.slug
        if dest.exists():
            if not replace:
                raise ChallengeImportError(
                    f"ya existe un reto importado con slug '{manifest.slug}'"
                )
            shutil.rmtree(dest)
        shutil.copytree(manifest.root, dest)
    return load_manifest(dest)
