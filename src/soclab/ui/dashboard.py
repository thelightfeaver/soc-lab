"""Resumen del expediente: progreso global y siguiente caso."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QProgressBar, QPushButton, QWidget

from soclab.manifest import Difficulty
from soclab.services import ChallengeView, Stats
from soclab.ui.detail import SheetScroll, label, section
from soclab.ui.theme import DIFFICULTY_COLORS


class DashboardWidget(SheetScroll):
    open_challenge = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        body = self.body
        body.addWidget(label("Resumen", "case_number"))
        body.addWidget(label("Expediente del analista", "h1"))
        self.lede = label("", "lede", wrap=True)
        self.lede.setAccessibleName("Progreso")
        body.addSpacing(4)
        body.addWidget(self.lede)

        ledger, ledger_layout = section("Casos por dificultad")
        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(12)
        self._rows: dict[Difficulty, tuple[QProgressBar, QWidget]] = {}
        for row, difficulty in enumerate(Difficulty):
            name = label(difficulty.label)
            name.setStyleSheet(f"color: {DIFFICULTY_COLORS[difficulty]}; font-weight: 600;")
            bar = QProgressBar()
            bar.setTextVisible(False)
            bar.setAccessibleName(f"Casos {difficulty.label} cerrados")
            bar.setStyleSheet(
                f"QProgressBar::chunk {{ background: {DIFFICULTY_COLORS[difficulty]}; }}"
            )
            count = label("", "muted")
            grid.addWidget(name, row, 0)
            grid.addWidget(bar, row, 1)
            grid.addWidget(count, row, 2)
            self._rows[difficulty] = (bar, count)
        grid.setColumnStretch(1, 1)
        ledger_layout.addLayout(grid)
        body.addWidget(ledger)

        nxt, next_layout = section("Siguiente caso")
        self.next_title = label("", "h2", wrap=True)
        self.next_title.setStyleSheet("font-size: 12pt;")
        self.next_summary = label("", "muted", wrap=True)
        next_layout.addWidget(self.next_title)
        next_layout.addWidget(self.next_summary)
        row = QHBoxLayout()
        self.next_button = QPushButton("Abrir caso")
        self.next_button.setObjectName("primary")
        self.next_button.clicked.connect(self._emit_next)
        row.addWidget(self.next_button)
        row.addStretch(1)
        next_layout.addLayout(row)
        body.addWidget(nxt)

        guide, guide_layout = section("Cómo se trabaja un caso")
        guide_layout.addWidget(
            label(
                "Lee el informe, abre las evidencias o inicia el entorno de análisis, "
                "y escribe tu conclusión como flag SOC{...}. Las pistas ayudan, pero "
                "restan puntos al cerrar el caso.",
                "muted",
                wrap=True,
            )
        )
        body.addWidget(guide)
        body.addStretch(1)
        self._next_slug: str | None = None

    def _emit_next(self) -> None:
        if self._next_slug:
            self.open_challenge.emit(self._next_slug)

    def update_stats(self, stats: Stats, challenges: list[ChallengeView]) -> None:
        self.lede.setText(
            f"Has cerrado {stats.solved} de {stats.total} casos y sumas "
            f"{stats.points_earned} de {stats.points_available} puntos."
        )
        for item in stats.by_difficulty:
            bar, count = self._rows[item.difficulty]
            bar.setRange(0, max(item.total, 1))
            bar.setValue(item.solved)
            count.setText(f"{item.solved} de {item.total}")  # type: ignore[attr-defined]
        pending = [c for c in challenges if not c.solved]
        if pending:
            nxt = pending[0]
            self._next_slug = nxt.slug
            self.next_title.setText(nxt.title)
            self.next_summary.setText(f"{nxt.difficulty.label}, {nxt.points} puntos. {nxt.summary}")
            self.next_button.setVisible(True)
        else:
            self._next_slug = None
            self.next_title.setText("Expediente completo")
            self.next_summary.setText(
                "Cerraste todos los casos. Importa casos nuevos o crea los tuyos."
            )
            self.next_button.setVisible(False)
