"""Piezas visuales propias del tema expediente: sello y fila de caso."""

from typing import override

from PySide6.QtCore import QModelIndex, QPersistentModelIndex, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem, QWidget

from soclab.services import ChallengeView
from soclab.ui.models import VIEW_ROLE
from soclab.ui.theme import (
    DIFFICULTY_COLORS,
    INK,
    INK_FAINT,
    INK_SOFT,
    RULE,
    STAMP,
    TAG,
    TAG_EDGE,
)


def case_number(slug: str) -> str:
    """Los retos incluidos empiezan por su número de caso (``07-dns...``)."""
    head = slug.split("-", 1)[0]
    return head if head.isdigit() else "—"


def _font(family: str, point: float, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    font = QFont(family)
    font.setPointSizeF(point)
    font.setWeight(weight)
    return font


class Stamp(QWidget):
    """Sello de goma rotado que marca un caso resuelto."""

    def __init__(self, text: str = "Resuelto", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.text = text
        self.setFixedSize(150, 64)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAccessibleName(f"Sello: {text}")

    @override
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(-7)
        color = QColor(STAMP)
        color.setAlphaF(0.88)
        box = QRectF(-62, -20, 124, 40)
        painter.setPen(QPen(color, 2.5))
        painter.drawRoundedRect(box, 4, 4)
        painter.setPen(QPen(color, 1))
        painter.drawRoundedRect(box.adjusted(4, 4, -4, -4), 2, 2)
        painter.setFont(_font("Source Serif 4", 15, QFont.Weight.DemiBold))
        painter.setPen(color)
        painter.drawText(box, Qt.AlignmentFlag.AlignCenter, self.text)
        painter.end()


type Index = QModelIndex | QPersistentModelIndex


class CaseDelegate(QStyledItemDelegate):
    """Fila de dos líneas: número de caso, título, dificultad/categoría y estado."""

    ROW_HEIGHT = 60

    @override
    def sizeHint(self, option: QStyleOptionViewItem, index: Index) -> QSize:
        return QSize(0, self.ROW_HEIGHT)  # el ancho lo decide la lista

    @override
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: Index) -> None:
        view: ChallengeView = index.data(VIEW_ROLE)
        rect = option.rect
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if selected:
            painter.fillRect(rect, QColor(TAG))
            painter.fillRect(rect.x(), rect.y(), 3, rect.height(), QColor(TAG_EDGE))
        elif hovered:
            painter.fillRect(rect, QColor("#F2F4F7"))
        painter.setPen(QPen(QColor(RULE), 1))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        if option.state & QStyle.StateFlag.State_HasFocus:
            painter.setPen(QPen(QColor(INK), 1, Qt.PenStyle.DotLine))
            painter.drawRect(rect.adjusted(1, 1, -2, -2))

        left = rect.x() + 14
        painter.setFont(_font("IBM Plex Sans", 10))
        painter.setPen(QColor(INK_FAINT))
        painter.drawText(
            QRectF(left, rect.y() + 10, 28, 20), Qt.AlignmentFlag.AlignLeft, case_number(view.slug)
        )

        text_left = left + 34
        right_space = 86
        width = rect.right() - text_left - right_space
        title_font = _font("IBM Plex Sans", 10.5, QFont.Weight.Medium)
        painter.setFont(title_font)
        painter.setPen(QColor(INK_SOFT if view.solved else INK))
        title = painter.fontMetrics().elidedText(view.title, Qt.TextElideMode.ElideRight, width)
        painter.drawText(
            QRectF(text_left, rect.y() + 9, width, 22), Qt.AlignmentFlag.AlignLeft, title
        )

        painter.setFont(_font("IBM Plex Sans", 9))
        painter.setPen(QColor(DIFFICULTY_COLORS[view.difficulty]))
        diff = view.difficulty.label
        painter.drawText(
            QRectF(text_left, rect.y() + 32, width, 18), Qt.AlignmentFlag.AlignLeft, diff
        )
        offset = painter.fontMetrics().horizontalAdvance(diff) + 12
        painter.setPen(QColor(INK_SOFT))
        category = painter.fontMetrics().elidedText(
            view.category, Qt.TextElideMode.ElideRight, int(width - offset)
        )
        painter.drawText(
            QRectF(text_left + offset, rect.y() + 32, width - offset, 18),
            Qt.AlignmentFlag.AlignLeft,
            category,
        )

        status = QRectF(rect.right() - right_space, rect.y(), right_space - 14, rect.height())
        if view.solved:
            painter.setFont(_font("Source Serif 4", 9.5, QFont.Weight.DemiBold))
            painter.setPen(QPen(QColor(STAMP), 1.2))
            badge = QRectF(status.right() - 64, rect.center().y() - 10, 64, 20)
            painter.drawRoundedRect(badge, 3, 3)
            painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, "Cerrado")
        else:
            painter.setFont(_font("IBM Plex Sans", 9.5))
            painter.setPen(QColor(INK_SOFT))
            align = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            painter.drawText(status, align, f"{view.points} pts")
        painter.restore()
