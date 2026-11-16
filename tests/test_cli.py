from pathlib import Path

import pytest

from soclab import flags
from soclab.cli import main
from soclab.config import BUILTIN_CHALLENGES_DIR
from tests.conftest import write_challenge


def test_hash_flag(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["hash-flag", "SOC{abc}"]) == 0
    assert flags.verify("SOC{abc}", capsys.readouterr().out.strip())


def test_hash_flag_invalid(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["hash-flag", "abc"]) == 2
    assert "error" in capsys.readouterr().err


def test_validate_builtin(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate", str(BUILTIN_CHALLENGES_DIR)]) == 0
    assert capsys.readouterr().out.count("✓") == 20


def test_validate_single_and_broken(tmp_path: Path) -> None:
    root = write_challenge(tmp_path)
    assert main(["validate", str(root)]) == 0
    (root / "challenge.toml").write_text("schema_version = 1\n")
    assert main(["validate", str(root)]) == 1
    assert main(["validate", str(tmp_path / "vacio")]) == 1
