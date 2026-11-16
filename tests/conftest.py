import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from soclab import flags
from soclab.config import BUILTIN_CHALLENGES_DIR
from soclab.db import init_database
from soclab.services import LabService


class FakeClock:
    def __init__(self) -> None:
        self.now = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += timedelta(seconds=seconds)


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SOCLAB_HOME", str(tmp_path / "home"))


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def db(tmp_path: Path):
    database = init_database(tmp_path / "test.db")
    yield database
    database.close()


@pytest.fixture
def service(db, clock: FakeClock) -> LabService:
    svc = LabService(db, clock=clock)
    assert svc.load_directory(BUILTIN_CHALLENGES_DIR, "builtin") == []
    return svc


def write_challenge(
    root: Path,
    slug: str = "custom-reto",
    flag: str = "SOC{hola_mundo}",
    *,
    extra: str = "",
    container: bool = True,
) -> Path:
    """Crea un reto mínimo válido en ``root/slug``."""
    target = root / slug
    (target / "files").mkdir(parents=True)
    (target / "files" / "evidencia.txt").write_text("datos\n")
    hint_block = '\n[[hints]]\ntext = "Mira el archivo"\ncost = 5\n'
    container_block = '\n[container]\ncontainerfile = "Containerfile"\n' if container else ""
    if container:
        (target / "Containerfile").write_text(
            "FROM localhost/soclab-base:1\nCOPY files/ /challenge/\n"
        )
    (target / "challenge.toml").write_text(
        f"""schema_version = 1
slug = "{slug}"
title = "Reto personalizado"
category = "Pruebas"
difficulty = "medio"
points = 150
summary = "Un reto creado para los tests."
description = "Descripción de prueba del reto."
flag_format = "SOC{{texto}}"
flag_hash = "{flags.hash_flag(flag)}"
{extra}{container_block}{hint_block}"""
    )
    return target
