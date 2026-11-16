"""Garantiza que los 20 retos son resolubles y reproducibles."""

import filecmp
import subprocess
import sys
from pathlib import Path

import pytest

from soclab import flags
from soclab.config import BUILTIN_CHALLENGES_DIR
from soclab.manifest import discover
from tests.solvers import SOLVERS

ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = {m.slug: m for m in discover(BUILTIN_CHALLENGES_DIR)[0]}


def test_every_challenge_has_solver() -> None:
    assert set(SOLVERS) == set(MANIFESTS)


@pytest.mark.parametrize("slug", sorted(MANIFESTS))
def test_challenge_is_solvable(slug: str) -> None:
    manifest = MANIFESTS[slug]
    answer = SOLVERS[slug](manifest.files_dir)
    assert flags.is_valid_format(answer), answer
    assert flags.verify(answer, manifest.flag_hash, case_sensitive=manifest.case_sensitive), (
        f"{slug}: la solución {answer!r} no coincide con flag_hash"
    )


def _compare(a: Path, b: Path) -> list[str]:
    cmp = filecmp.dircmp(a, b)
    diffs = [str(Path(a, n)) for n in cmp.left_only + cmp.right_only + cmp.diff_files]
    for sub in cmp.common_dirs:
        diffs += _compare(a / sub, b / sub)
    return diffs


def test_generator_is_deterministic(tmp_path: Path) -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate_challenges.py"), str(tmp_path)],
        check=True,
        capture_output=True,
    )
    assert _compare(BUILTIN_CHALLENGES_DIR, tmp_path) == []
