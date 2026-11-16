from pathlib import Path

import pytest

from soclab.config import BUILTIN_CHALLENGES_DIR
from soclab.manifest import Difficulty, ManifestError, discover, load_manifest
from tests.conftest import write_challenge


def test_builtin_catalog_is_complete() -> None:
    manifests, errors = discover(BUILTIN_CHALLENGES_DIR)
    assert errors == []
    assert len(manifests) == 20
    assert len({m.slug for m in manifests}) == 20
    counts = {d: sum(m.difficulty is d for m in manifests) for d in Difficulty}
    assert all(counts.values()), counts
    for m in manifests:
        assert m.containerfile_path and m.containerfile_path.is_file()
        assert m.files_dir.is_dir() and any(m.files_dir.iterdir())
        assert m.hints


def test_valid_manifest(tmp_path: Path) -> None:
    m = load_manifest(write_challenge(tmp_path))
    assert m.slug == "custom-reto"
    assert m.difficulty is Difficulty.MEDIO
    assert m.hints[0].cost == 5


@pytest.mark.parametrize(
    ("replace", "expected"),
    [
        ('slug = "custom-reto"', "slug"),
        ('difficulty = "medio"', "difficulty"),
        ("points = 150", "points"),
        ("schema_version = 1", "schema_version"),
    ],
)
def test_invalid_fields_are_reported(tmp_path: Path, replace: str, expected: str) -> None:
    root = write_challenge(tmp_path)
    toml = root / "challenge.toml"
    bad = {
        "slug": 'slug = "Con Espacios!"',
        "difficulty": 'difficulty = "imposible"',
        "points": "points = 99999",
        "schema_version": "schema_version = 7",
    }[expected]
    toml.write_text(toml.read_text().replace(replace, bad))
    with pytest.raises(ManifestError) as exc:
        load_manifest(root)
    assert any(expected in e for e in exc.value.errors)


def test_unknown_keys_and_bad_hash(tmp_path: Path) -> None:
    root = write_challenge(tmp_path, extra='flag = "SOC{en_claro}"\n')
    toml = root / "challenge.toml"
    toml.write_text(toml.read_text().replace('flag_hash = "scrypt', 'flag_hash = "md5'))
    with pytest.raises(ManifestError) as exc:
        load_manifest(root)
    joined = " ".join(exc.value.errors)
    assert "claves desconocidas" in joined
    assert "flag_hash" in joined


def test_containerfile_path_traversal(tmp_path: Path) -> None:
    root = write_challenge(tmp_path)
    toml = root / "challenge.toml"
    toml.write_text(toml.read_text().replace('"Containerfile"', '"../../etc/passwd"'))
    with pytest.raises(ManifestError, match="ruta relativa"):
        load_manifest(root)


def test_missing_and_broken_files(tmp_path: Path) -> None:
    with pytest.raises(ManifestError, match="no existe"):
        load_manifest(tmp_path)
    (tmp_path / "challenge.toml").write_text("esto no = = es toml")
    with pytest.raises(ManifestError, match="TOML"):
        load_manifest(tmp_path)


def test_hint_cost_cannot_exceed_points(tmp_path: Path) -> None:
    root = write_challenge(tmp_path)
    toml = root / "challenge.toml"
    toml.write_text(toml.read_text().replace("cost = 5", "cost = 500"))
    with pytest.raises(ManifestError, match="pista 1"):
        load_manifest(root)
