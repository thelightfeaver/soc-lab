import stat
import zipfile
from pathlib import Path

import pytest

from soclab.importer import ChallengeImportError, install_challenge, safe_extract
from tests.conftest import write_challenge


def _zip_dir(src: Path, dest: Path) -> Path:
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in src.rglob("*"):
            zf.write(path, path.relative_to(src.parent))
    return dest


def test_install_from_zip(tmp_path: Path) -> None:
    src = write_challenge(tmp_path / "src")
    archive = _zip_dir(src, tmp_path / "reto.zip")
    manifest = install_challenge(archive, tmp_path / "dest", reserved_slugs=set())
    assert manifest.root == (tmp_path / "dest" / "custom-reto").resolve()
    assert (manifest.files_dir / "evidencia.txt").is_file()


def test_install_from_folder_and_replace(tmp_path: Path) -> None:
    src = write_challenge(tmp_path / "src")
    dest = tmp_path / "dest"
    install_challenge(src, dest, reserved_slugs=set())
    with pytest.raises(ChallengeImportError, match="ya existe"):
        install_challenge(src, dest, reserved_slugs=set())
    install_challenge(src, dest, reserved_slugs=set(), replace=True)


def test_reserved_slug(tmp_path: Path) -> None:
    src = write_challenge(tmp_path / "src")
    with pytest.raises(ChallengeImportError, match="incluido"):
        install_challenge(src, tmp_path / "dest", reserved_slugs={"custom-reto"})


@pytest.mark.parametrize("name", ["../escape.txt", "/abs.txt", "a\\..\\b.txt", "C:/x.txt"])
def test_zip_slip_rejected(tmp_path: Path, name: str) -> None:
    archive = tmp_path / "evil.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(name, "x")
    with pytest.raises(ChallengeImportError):
        safe_extract(archive, tmp_path / "out")
    assert not (tmp_path / "escape.txt").exists()


def test_zip_symlink_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "link.zip"
    info = zipfile.ZipInfo("enlace")
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(info, "/etc/passwd")
    with pytest.raises(ChallengeImportError, match="simbólicos"):
        safe_extract(archive, tmp_path / "out")


def test_zip_bomb_ratio_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "bomb.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("ceros.bin", b"\0" * 5_000_000)
    with pytest.raises(ChallengeImportError, match="ratio"):
        safe_extract(archive, tmp_path / "out")


def test_not_a_zip_and_bad_source(tmp_path: Path) -> None:
    fake = tmp_path / "fake.zip"
    fake.write_text("hola")
    with pytest.raises(ChallengeImportError, match="ZIP válido"):
        install_challenge(fake, tmp_path / "d", reserved_slugs=set())
    other = tmp_path / "x.txt"
    other.write_text("x")
    with pytest.raises(ChallengeImportError, match="carpeta"):
        install_challenge(other, tmp_path / "d", reserved_slugs=set())


def test_zip_without_manifest(tmp_path: Path) -> None:
    archive = tmp_path / "vacio.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("readme.txt", "nada")
    with pytest.raises(ChallengeImportError, match=r"único challenge\.toml"):
        install_challenge(archive, tmp_path / "d", reserved_slugs=set())
