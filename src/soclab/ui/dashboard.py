"""Panel de progreso general."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from soclab.manifest import Difficulty
from soclab.services import ChallengeView, Stats
from soclab.ui.theme import DIFFICULTY_COLORS


def card() -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(8)
    return frame, layout


class DashboardWidget(QWidget):
    open_challenge = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(18)

        title = QLabel("Panel del analista")
        title.setObjectName("h1")
        subtitle = QLabel(
            "Resuelve los retos, envía la flag SOC{...} y sigue tu progreso. "
            "Selecciona un reto de la lista para empezar."
        )
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        top = QHBoxLayout()
        top.setSpacing(18)
        score_card, score_layout = card()
        self.score = QLabel("0")
        self.score.setObjectName("score")
        self.score.setAccessibleName("Puntuación")
        self.score_detail = QLabel()
        self.score_detail.setObjectName("muted")
        score_layout.addWidget(QLabel("Puntuación"))
        score_layout.addWidget(self.score)
        score_layout.addWidget(self.score_detail)
        top.addWidget(score_card, 1)

        progress_card, progress_layout = card()
        self.solved_label = QLabel()
        self.overall = QProgressBar()
        self.overall.setAccessibleName("Progreso total")
        progress_layout.addWidget(QLabel("Retos completados"))
        progress_layout.addWidget(self.solved_label)
        progress_layout.addWidget(self.overall)
        top.addWidget(progress_card, 2)
        root.addLayout(top)

        diff_card, diff_layout = card()
        heading = QLabel("Progreso por dificultad")
        heading.setObjectName("h2")
        diff_layout.addWidget(heading)
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        self._bars: dict[Difficulty, tuple[QProgressBar, QLabel]] = {}
        for row, difficulty in enumerate(Difficulty):
            color = DIFFICULTY_COLORS[difficulty]
            name = QLabel(difficulty.label)
            name.setStyleSheet(f"color: {color}; font-weight: 700;")
            bar = QProgressBar()
            bar.setTextVisible(False)
            bar.setAccessibleName(f"Progreso {difficulty.label}")
            bar.setStyleSheet(f"QProgressBar::chunk {{ background: {color}; }}")
            count = QLabel()
            count.setObjectName("muted")
            grid.addWidget(name, row, 0)
            grid.addWidget(bar, row, 1)
            grid.addWidget(count, row, 2)
            self._bars[difficulty] = (bar, count)
        grid.setColumnStretch(1, 1)
        diff_layout.addLayout(grid)
        root.addWidget(diff_card)

        next_card, next_layout = card()
        self.next_title = QLabel()
        self.next_title.setObjectName("h2")
        self.next_summary = QLabel()
        self.next_summary.setWordWrap(True)
        self.next_summary.setObjectName("muted")
        self.next_button = QPushButton("Ir al reto sugerido")
        self.next_button.setObjectName("primary")
        self.next_button.clicked.connect(self._emit_next)
        next_layout.addWidget(QLabel("Siguiente reto sugerido"))
        next_layout.addWidget(self.next_title)
        next_layout.addWidget(self.next_summary)
        next_layout.addWidget(self.next_button)
        root.addWidget(next_card)
        root.addStretch(1)
        self._next_slug: str | None = None

    def _emit_next(self) -> None:
        if self._next_slug:
            self.open_challenge.emit(self._next_slug)

    def update_stats(self, stats: Stats, challenges: list[ChallengeView]) -> None:
        self.score.setText(str(stats.points_earned))
        self.score_detail.setText(f"de {stats.points_available} puntos posibles")
        self.solved_label.setText(f"{stats.solved} de {stats.total} retos ({stats.percent}%)")
        self.overall.setRange(0, max(stats.total, 1))
        self.overall.setValue(stats.solved)
        for item in stats.by_difficulty:
            bar, count = self._bars[item.difficulty]
            bar.setRange(0, max(item.total, 1))
            bar.setValue(item.solved)
            count.setText(f"{item.solved}/{item.total}")
        pending = [c for c in challenges if not c.solved]
        if pending:
            nxt = pending[0]
            self._next_slug = nxt.slug
            self.next_title.setText(f"{nxt.title} · {nxt.difficulty.label} · {nxt.points} pts")
            self.next_summary.setText(nxt.summary)
            self.next_button.setEnabled(True)
        else:
            self._next_slug = None
            self.next_title.setText("¡Laboratorio completado! 🎉")
            self.next_summary.setText(
                "Has resuelto todos los retos. Importa nuevos retos o crea los tuyos."
            )
            self.next_button.setEnabled(False)
