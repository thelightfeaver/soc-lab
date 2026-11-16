"""Hoja del caso: informe, evidencias, pistas y conclusión (flag)."""

import html

from PySide6.QtCore import QSizeF, Qt, QUrl, Signal, SignalInstance
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from soclab import flags
from soclab.services import ChallengeView, SubmitResult
from soclab.ui.theme import DIFFICULTY_COLORS
from soclab.ui.widgets import Stamp, case_number

SHEET_MAX_WIDTH = 760  # ~75 caracteres por línea en el informe

FEEDBACK = {
    SubmitResult.CORRECT: ("feedback_ok", "Correcto. Caso cerrado."),
    SubmitResult.INCORRECT: (
        "feedback_err",
        "Flag incorrecta. Revisa la evidencia y vuelve a intentarlo.",
    ),
    SubmitResult.INVALID_FORMAT: (
        "feedback_warn",
        "La flag debe tener el formato SOC{...} sin espacios.",
    ),
    SubmitResult.ALREADY_SOLVED: ("feedback_ok", "Este caso ya está cerrado."),
    SubmitResult.RATE_LIMITED: ("feedback_warn", "Espera dos segundos antes de reintentar."),
}


def label(text: str = "", name: str = "", *, wrap: bool = False) -> QLabel:
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(wrap)
    return widget


def section(title: str) -> tuple[QFrame, QVBoxLayout]:
    """Bloque del informe separado por una línea fina, como en un expediente."""
    frame = QFrame()
    frame.setObjectName("section")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(0, 18, 0, 0)
    layout.setSpacing(10)
    layout.addWidget(label(title, "h2"))
    return frame, layout


class SheetScroll(QScrollArea):
    """Área desplazable que centra una hoja blanca de ancho máximo legible."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        outer = QWidget()
        self.setWidget(outer)
        row = QHBoxLayout(outer)
        row.setContentsMargins(28, 24, 28, 28)
        self.sheet = QFrame()
        self.sheet.setObjectName("sheet")
        self.sheet.setMaximumWidth(SHEET_MAX_WIDTH)
        row.addStretch(1)
        row.addWidget(self.sheet, 100)
        row.addStretch(1)
        self.body = QVBoxLayout(self.sheet)
        self.body.setContentsMargins(40, 32, 40, 32)
        self.body.setSpacing(8)


class ChallengeDetailWidget(SheetScroll):
    start_requested = Signal(str)
    stop_requested = Signal(str)
    open_files_requested = Signal(str)
    hint_requested = Signal(str, int)
    flag_submitted = Signal(str, str)
    delete_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._view: ChallengeView | None = None
        body = self.body

        header = QHBoxLayout()
        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        self.case_label = label("", "case_number")
        self.title = label("", "h1", wrap=True)
        self.meta_row = QHBoxLayout()
        self.meta_row.setSpacing(16)
        self.difficulty = label()
        self.category = label("", "muted")
        self.points = label("", "muted")
        for w in (self.difficulty, self.category, self.points):
            self.meta_row.addWidget(w)
        self.meta_row.addStretch(1)
        text_col.addWidget(self.case_label)
        text_col.addWidget(self.title)
        text_col.addLayout(self.meta_row)
        header.addLayout(text_col, 1)
        self.stamp = Stamp()
        header.addWidget(self.stamp, 0, Qt.AlignmentFlag.AlignTop)
        body.addLayout(header)

        self.summary = label("", "lede", wrap=True)
        body.addSpacing(6)
        body.addWidget(self.summary)

        self.description = QTextBrowser()
        self.description.setObjectName("report")
        self.description.setOpenLinks(False)
        self.description.anchorClicked.connect(self._open_link)
        self.description.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.description.setAccessibleName("Informe del caso")
        self.description.document().setDocumentMargin(0)
        self.description.document().documentLayout().documentSizeChanged.connect(self._fit_report)
        body.addSpacing(8)
        body.addWidget(self.description)

        # --- evidencias y entorno
        env, env_layout = section("Evidencias")
        actions = QHBoxLayout()
        self.files_btn = QPushButton("Abrir carpeta de evidencias")
        self.start_btn = QPushButton("Iniciar entorno de análisis")
        self.stop_btn = QPushButton("Detener entorno")
        self.files_btn.clicked.connect(lambda: self._emit(self.open_files_requested))
        self.start_btn.clicked.connect(lambda: self._emit(self.start_requested))
        self.stop_btn.clicked.connect(lambda: self._emit(self.stop_requested))
        for btn in (self.files_btn, self.start_btn, self.stop_btn):
            actions.addWidget(btn)
        actions.addStretch(1)
        env_layout.addLayout(actions)
        self.status = label("Entorno: desconocido", "muted")
        env_layout.addWidget(self.status)
        cmd_row = QHBoxLayout()
        self.command = QLineEdit()
        self.command.setObjectName("command")
        self.command.setReadOnly(True)
        self.command.setAccessibleName("Comando para abrir una terminal en el entorno")
        self.copy_btn = QPushButton("Copiar comando")
        self.copy_btn.clicked.connect(self._copy_command)
        cmd_row.addWidget(self.command, 1)
        cmd_row.addWidget(self.copy_btn)
        env_layout.addLayout(cmd_row)
        self.env_help = label(
            "Pega el comando en una terminal. El entorno no tiene red y las evidencias "
            "están en /challenge, en solo lectura.",
            "faint",
            wrap=True,
        )
        env_layout.addWidget(self.env_help)
        body.addWidget(env)

        # --- pistas
        hints, self.hints_layout = section("Pistas")
        self.hints_box = QVBoxLayout()
        self.hints_box.setSpacing(8)
        self.hints_layout.addLayout(self.hints_box)
        body.addWidget(hints)

        # --- conclusión
        conclusion, flag_layout = section("Conclusión")
        self.flag_help = label("", "muted")
        flag_layout.addWidget(self.flag_help)
        row = QHBoxLayout()
        row.setSpacing(16)
        self.flag_input = QLineEdit()
        self.flag_input.setObjectName("flag")
        self.flag_input.setMaxLength(flags.MAX_FLAG_LENGTH)
        self.flag_input.setAccessibleName("Flag")
        self.flag_input.returnPressed.connect(self._submit)
        self.flag_input.textChanged.connect(self._validate_input)
        self.submit_btn = QPushButton("Cerrar caso")
        self.submit_btn.setObjectName("primary")
        self.submit_btn.clicked.connect(self._submit)
        row.addWidget(self.flag_input, 1)
        row.addWidget(self.submit_btn)
        flag_layout.addLayout(row)
        self.feedback = label("", wrap=True)
        self.feedback.setAccessibleName("Resultado")
        flag_layout.addWidget(self.feedback)
        body.addWidget(conclusion)

        body.addSpacing(18)
        footer = QHBoxLayout()
        self.meta = label("", "faint")
        self.delete_btn = QPushButton("Eliminar caso importado")
        self.delete_btn.setObjectName("danger")
        self.delete_btn.clicked.connect(lambda: self._emit(self.delete_requested))
        footer.addWidget(self.meta, 1)
        footer.addWidget(self.delete_btn)
        body.addLayout(footer)
        body.addStretch(1)

    # ------------------------------------------------------------ internos
    @property
    def slug(self) -> str | None:
        return self._view.slug if self._view else None

    def _emit(self, signal: SignalInstance) -> None:
        if self._view:
            signal.emit(self._view.slug)

    def _fit_report(self, size: QSizeF) -> None:
        self.description.setFixedHeight(int(size.height()) + 8)

    @staticmethod
    def _open_link(url: QUrl) -> None:
        # Solo enlaces web: un manifiesto importado no puede abrir rutas locales.
        if url.scheme() in {"http", "https"}:
            QDesktopServices.openUrl(url)

    def _copy_command(self) -> None:
        QGuiApplication.clipboard().setText(self.command.text())
        self.copy_btn.setText("Copiado")

    def _validate_input(self, text: str) -> None:
        valid = flags.is_valid_format(text)
        solved = bool(self._view and self._view.solved)
        self.submit_btn.setEnabled(valid and not solved)
        if text and not valid:
            self._set_feedback("feedback_warn", "Formato esperado: SOC{...} sin espacios.")
        elif self.feedback.objectName() == "feedback_warn":
            self._set_feedback("", "")

    def _submit(self) -> None:
        if self._view and self.submit_btn.isEnabled():
            self.flag_submitted.emit(self._view.slug, self.flag_input.text())

    def _set_feedback(self, style: str, text: str) -> None:
        self.feedback.setObjectName(style)
        self.feedback.setText(text)
        self.feedback.style().unpolish(self.feedback)
        self.feedback.style().polish(self.feedback)

    @staticmethod
    def _clear(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

    # ------------------------------------------------------------ API pública
    def show_challenge(self, view: ChallengeView) -> None:
        same = self._view is not None and self._view.slug == view.slug
        self._view = view
        number = case_number(view.slug)
        self.case_label.setText(f"Caso {number}" if number != "—" else "Caso importado")
        self.title.setText(view.title)
        color = DIFFICULTY_COLORS[view.difficulty]
        self.difficulty.setText(view.difficulty.label)
        self.difficulty.setStyleSheet(f"color: {color}; font-weight: 600;")
        self.category.setText(view.category)
        self.points.setText(
            f"{view.awarded_points} de {view.points} puntos"
            if view.solved
            else f"{view.points} puntos"
        )
        self.stamp.setVisible(view.solved)
        self.summary.setText(view.summary)
        self.description.setMarkdown(view.description)

        for w in (self.start_btn, self.stop_btn, self.command, self.copy_btn, self.env_help):
            w.setVisible(view.has_container)
        self.status.setVisible(view.has_container)
        self.command.setText(f"podman exec -it soclab-{view.slug} bash -l")
        self.copy_btn.setText("Copiar comando")
        self._render_hints(view)

        self.flag_help.setText(f"Formato esperado: {view.flag_format}")
        self.flag_input.setPlaceholderText(view.flag_format)
        self.flag_input.setEnabled(not view.solved)
        if not same:
            self.flag_input.clear()
            self._set_feedback("", "")
            self.verticalScrollBar().setValue(0)
        if view.solved:
            self._set_feedback("feedback_ok", f"Caso cerrado con {view.awarded_points} puntos.")
        self._validate_input(self.flag_input.text())
        source = "importado" if view.source == "imported" else "incluido en el laboratorio"
        attempts = "1 intento" if view.attempts == 1 else f"{view.attempts} intentos"
        self.meta.setText(f"Autor: {view.author}. Caso {source}. {attempts}.")
        self.delete_btn.setVisible(view.source == "imported")

    def _render_hints(self, view: ChallengeView) -> None:
        self._clear(self.hints_box)
        if not view.hints:
            self.hints_box.addWidget(label("Este caso no tiene pistas.", "muted"))
        for position, text, cost in view.hints:
            if text is not None:
                hint = label(
                    f"<b>Pista {position}</b> (−{cost} pts). {html.escape(text)}", wrap=True
                )
                hint.setTextFormat(Qt.TextFormat.RichText)
                hint.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                self.hints_box.addWidget(hint)
                continue
            btn = QPushButton(f"Ver pista {position} (resta {cost} puntos)")
            btn.setObjectName("link")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setEnabled(not view.solved)
            btn.clicked.connect(
                lambda _=False, p=position: (
                    self._view and self.hint_requested.emit(self._view.slug, p)
                )
            )
            self.hints_box.addWidget(btn)

    def show_result(self, result: SubmitResult) -> None:
        style, text = FEEDBACK[result]
        self._set_feedback(style, text)
        if result is SubmitResult.INCORRECT:
            self.flag_input.selectAll()
            self.flag_input.setFocus()

    def set_container_state(self, text: str, *, running: bool | None, busy: bool = False) -> None:
        self.status.setText(f"Entorno: {text}")
        self.start_btn.setEnabled(not busy and running is False)
        self.stop_btn.setEnabled(not busy and running is True)
