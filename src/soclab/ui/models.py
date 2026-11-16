"""Modelos Qt para la tabla de retos."""

from typing import Any, override

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    QSortFilterProxyModel,
    Qt,
)
from PySide6.QtGui import QColor, QFont

from soclab.manifest import Difficulty
from soclab.services import ChallengeView
from soclab.ui.theme import DIFFICULTY_COLORS, MUTED, SUCCESS

type Index = QModelIndex | QPersistentModelIndex

VIEW_ROLE = Qt.ItemDataRole.UserRole + 1
SORT_ROLE = Qt.ItemDataRole.UserRole + 2


class ChallengeTableModel(QAbstractTableModel):
    HEADERS = ("", "Reto", "Categoría", "Dificultad", "Pts")

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._rows: list[ChallengeView] = []

    def set_challenges(self, rows: list[ChallengeView]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    def row_of(self, slug: str) -> int:
        return next((i for i, v in enumerate(self._rows) if v.slug == slug), -1)

    @override
    def rowCount(self, parent: Index = QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else len(self._rows)

    @override
    def columnCount(self, parent: Index = QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else len(self.HEADERS)

    @override
    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        return None

    @override
    def data(self, index: Index, role: int = Qt.ItemDataRole.DisplayRole) -> Any:  # noqa: PLR0911
        if not index.isValid():
            return None
        view = self._rows[index.row()]
        col = index.column()
        match role:
            case Qt.ItemDataRole.DisplayRole:
                return (
                    "✔" if view.solved else "•",
                    view.title,
                    view.category,
                    view.difficulty.label,
                    view.awarded_points if view.solved else view.points,
                )[col]
            case Qt.ItemDataRole.ForegroundRole:
                if col == 0:
                    return QColor(SUCCESS if view.solved else MUTED)
                if col == 3:  # noqa: PLR2004
                    return QColor(DIFFICULTY_COLORS[view.difficulty])
                return None
            case Qt.ItemDataRole.FontRole if col in {1, 3}:
                font = QFont()
                font.setBold(col == 3 or not view.solved)  # noqa: PLR2004
                return font
            case Qt.ItemDataRole.TextAlignmentRole if col in {0, 4}:
                return Qt.AlignmentFlag.AlignCenter
            case Qt.ItemDataRole.ToolTipRole:
                state = "Resuelto" if view.solved else "Pendiente"
                return f"{view.title} — {state}\n{view.summary}"
            case Qt.ItemDataRole.AccessibleTextRole:
                state = "resuelto" if view.solved else "pendiente"
                return f"{view.title}, {view.difficulty.label}, {view.points} puntos, {state}"
            case _ if role == VIEW_ROLE:
                return view
            case _ if role == SORT_ROLE:
                return (
                    int(view.solved),
                    view.title,
                    view.category,
                    view.difficulty.rank,
                    view.points,
                )[col]
        return None


class ChallengeFilterProxy(QSortFilterProxyModel):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.setSortRole(SORT_ROLE)
        self._text = ""
        self._difficulty: Difficulty | None = None
        self._category: str | None = None
        self._status: str = "all"

    def set_filters(
        self, *, text: str, difficulty: str | None, category: str | None, status: str
    ) -> None:
        self.beginFilterChange()
        self._text = text.strip().casefold()
        # Qt convierte los StrEnum guardados como itemData en str: se reconstruye.
        self._difficulty = Difficulty(difficulty) if difficulty else None
        self._category, self._status = category, status
        self.endFilterChange()

    @override
    def filterAcceptsRow(self, source_row: int, source_parent: Index) -> bool:
        view: ChallengeView = self.sourceModel().index(source_row, 0, source_parent).data(VIEW_ROLE)
        if self._difficulty and view.difficulty is not self._difficulty:
            return False
        if self._category and view.category != self._category:
            return False
        if self._status == "solved" and not view.solved:
            return False
        if self._status == "pending" and view.solved:
            return False
        haystack = f"{view.title} {view.category} {view.slug} {view.summary}".casefold()
        return not self._text or self._text in haystack
