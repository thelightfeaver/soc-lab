from pathlib import Path

import pytest

from soclab.podman import PodmanError
from soclab.services import LabService
from soclab.ui.main_window import MainWindow
from tests.conftest import FakeClock, write_challenge

pytest.importorskip("pytestqt")


class FakePodman:
    def __init__(self, *, available: bool = True) -> None:
        self.available = available
        self.running: set[str] = set()

    def version(self) -> str:
        if not self.available:
            raise PodmanError("sin máquina")
        return "6.0.0"

    def is_running(self, container) -> bool:
        return container.name in self.running

    def start(self, container) -> None:
        self.running.add(container.name)

    def stop(self, container) -> None:
        self.running.discard(container.name)

    def ensure_base_image(self, *, rebuild: bool = False) -> None:
        pass


@pytest.fixture
def window(qtbot, service: LabService, tmp_path: Path):
    win = MainWindow(service, FakePodman(), import_dir=tmp_path / "imp", confirm=False)  # type: ignore[arg-type]
    qtbot.addWidget(win)
    qtbot.waitUntil(lambda: win.podman_ok)
    yield win
    win.tasks.wait()


def test_lists_all_challenges(window: MainWindow) -> None:
    assert window.proxy.rowCount() == 20
    assert window.stack.currentWidget() is window.dashboard
    assert "0 de 20" in window.progress_label.text()


def test_filters(window: MainWindow) -> None:
    window.search.setText("ssh")
    assert window.proxy.rowCount() == 1
    window.search.clear()
    window.difficulty_filter.setCurrentIndex(4)  # Experto
    assert 0 < window.proxy.rowCount() < 20
    window.difficulty_filter.setCurrentIndex(0)
    window.status_filter.setCurrentIndex(2)  # Resueltos
    assert window.proxy.rowCount() == 0


def test_select_and_submit_flow(qtbot, window: MainWindow, clock: FakeClock) -> None:
    window.case_list.setCurrentIndex(window.proxy.index(0, 0))
    assert window.stack.currentWidget() is window.detail
    slug = window.detail.slug
    assert slug == "01-ssh-bruteforce"

    window.detail.flag_input.setText("no valida")
    assert not window.detail.submit_btn.isEnabled()
    window.detail.flag_input.setText("SOC{1.1.1.1}")
    window.detail.submit_btn.click()
    assert "incorrecta" in window.detail.feedback.text()

    clock.advance(5)
    window.detail.flag_input.setText("SOC{203.0.113.77}")
    window.detail.submit_btn.click()
    assert "Correcto" in window.detail.feedback.text()
    assert not window.detail.flag_input.isEnabled()
    assert "1 de 20" in window.progress_label.text()
    assert "100 de 4800" in window.dashboard.lede.text()
    assert window.detail.stamp.isVisibleTo(window.detail)


def test_hint_reveal_updates_detail(window: MainWindow) -> None:
    window.select_challenge("02-phishing-headers")
    window.reveal_hint("02-phishing-headers", 1)
    assert window.service.get("02-phishing-headers").hints[0][1] is not None


def test_container_start_stop(qtbot, window: MainWindow) -> None:
    window.select_challenge("01-ssh-bruteforce")
    qtbot.waitUntil(window.detail.start_btn.isEnabled)
    window.detail.start_btn.click()
    qtbot.waitUntil(window.detail.stop_btn.isEnabled)
    assert "en ejecución" in window.detail.status.text()
    window.detail.stop_btn.click()
    qtbot.waitUntil(window.detail.start_btn.isEnabled)
    assert "detenido" in window.detail.status.text()


def test_import_and_delete(window: MainWindow, tmp_path: Path) -> None:
    src = write_challenge(tmp_path / "src")
    assert window.import_path(src) == "custom-reto"
    assert window.proxy.rowCount() == 21
    assert window.detail.delete_btn.isVisibleTo(window.detail)
    window.delete_challenge("custom-reto")
    assert window.proxy.rowCount() == 20


def test_import_invalid_shows_error(window: MainWindow, tmp_path: Path) -> None:
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "challenge.toml").write_text("schema_version = 1\n")
    assert window.import_path(bad) is None
    assert "inválido" in window.statusBar().currentMessage()


def test_podman_unavailable(qtbot, service: LabService, tmp_path: Path) -> None:
    win = MainWindow(service, FakePodman(available=False), import_dir=tmp_path, confirm=False)  # type: ignore[arg-type]
    qtbot.addWidget(win)
    qtbot.waitUntil(lambda: "no disponible" in win.podman_label.text())
    win.select_challenge("01-ssh-bruteforce")
    assert not win.detail.start_btn.isEnabled()
