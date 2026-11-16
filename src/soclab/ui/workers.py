"""Ejecución de tareas bloqueantes (Podman) fuera del hilo de la UI."""

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal


class _Signals(QObject):
    finished = Signal(object)
    failed = Signal(str)


class _Task(QRunnable):
    def __init__(self, fn: Callable[[], Any], signals: _Signals) -> None:
        super().__init__()
        self.fn = fn
        self.signals = signals

    def run(self) -> None:
        try:
            result = self.fn()
        except Exception as exc:  # noqa: BLE001 - se reporta a la UI
            self.signals.failed.emit(str(exc) or exc.__class__.__name__)
        else:
            self.signals.finished.emit(result)


class TaskRunner(QObject):
    """Lanza funciones en un QThreadPool y entrega el resultado en el hilo principal."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(2)
        self._alive: set[_Signals] = set()

    def submit(
        self,
        fn: Callable[[], Any],
        on_done: Callable[[Any], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        signals = _Signals(self)  # vive en el hilo principal -> callbacks en el hilo principal
        self._alive.add(signals)
        queued = Qt.ConnectionType.QueuedConnection

        def _cleanup(*_: object) -> None:
            self._alive.discard(signals)
            signals.deleteLater()

        if on_done:
            signals.finished.connect(on_done, queued)
        if on_error:
            signals.failed.connect(on_error, queued)
        signals.finished.connect(_cleanup, queued)
        signals.failed.connect(_cleanup, queued)
        self.pool.start(_Task(fn, signals))

    def wait(self, msecs: int = 30_000) -> bool:
        return self.pool.waitForDone(msecs)
