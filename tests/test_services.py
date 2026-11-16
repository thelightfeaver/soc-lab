from pathlib import Path

import pytest

from soclab.services import LabService, SubmitResult
from tests.conftest import FakeClock, write_challenge

SLUG = "custom-reto"


@pytest.fixture
def custom(service: LabService, tmp_path: Path) -> LabService:
    service.import_challenge(write_challenge(tmp_path / "src"), tmp_path / "imported")
    return service


def test_builtin_loaded(service: LabService) -> None:
    stats = service.stats()
    assert stats.total == 20
    assert stats.solved == 0
    assert stats.points_available == sum(v.points for v in service.list())
    assert service.categories()


def test_correct_flag_awards_points(custom: LabService) -> None:
    assert custom.submit_flag(SLUG, "SOC{hola_mundo}") is SubmitResult.CORRECT
    view = custom.get(SLUG)
    assert view.solved
    assert view.awarded_points == 150
    assert custom.submit_flag(SLUG, "SOC{hola_mundo}") is SubmitResult.ALREADY_SOLVED


def test_hint_penalty(custom: LabService) -> None:
    assert custom.reveal_hint(SLUG, 1) == "Mira el archivo"
    custom.reveal_hint(SLUG, 1)  # idempotente: no se cobra dos veces
    custom.submit_flag(SLUG, "SOC{hola_mundo}")
    assert custom.get(SLUG).awarded_points == 145
    with pytest.raises(KeyError):
        custom.reveal_hint(SLUG, 9)


def test_wrong_flag_and_rate_limit(custom: LabService, clock: FakeClock) -> None:
    assert custom.submit_flag(SLUG, "SOC{mal}") is SubmitResult.INCORRECT
    assert custom.submit_flag(SLUG, "SOC{hola_mundo}") is SubmitResult.RATE_LIMITED
    clock.advance(3)
    assert custom.submit_flag(SLUG, "SOC{hola_mundo}") is SubmitResult.CORRECT
    assert custom.get(SLUG).attempts == 2


def test_invalid_format_is_not_counted(custom: LabService) -> None:
    assert custom.submit_flag(SLUG, "hola") is SubmitResult.INVALID_FORMAT
    assert custom.get(SLUG).attempts == 0


def test_resync_keeps_progress(custom: LabService, tmp_path: Path) -> None:
    custom.submit_flag(SLUG, "SOC{hola_mundo}")
    assert custom.load_directory(tmp_path / "imported", "imported") == []
    assert custom.get(SLUG).solved


def test_reset_progress(custom: LabService) -> None:
    custom.reveal_hint(SLUG, 1)
    custom.submit_flag(SLUG, "SOC{hola_mundo}")
    custom.reset_progress()
    view = custom.get(SLUG)
    assert not view.solved
    assert view.attempts == 0
    assert view.hints[0][1] is None


def test_delete_only_imported(custom: LabService) -> None:
    builtin = custom.list()[0].slug
    with pytest.raises(PermissionError):
        custom.delete_imported(builtin)
    root = custom.get(SLUG).root
    custom.delete_imported(SLUG)
    assert not root.exists()
    with pytest.raises(KeyError):
        custom.get(SLUG)


def test_import_cannot_shadow_builtin(service: LabService, tmp_path: Path) -> None:
    from soclab.importer import ChallengeImportError  # noqa: PLC0415

    builtin = service.list()[0].slug
    with pytest.raises(ChallengeImportError):
        service.import_challenge(write_challenge(tmp_path / "s", slug=builtin), tmp_path / "i")
