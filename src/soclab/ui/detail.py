"""Vista de detalle de un reto: descripción, entorno, pistas y envío de flag."""

import html

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from soclab import flags
from soclab.services import ChallengeView, SubmitResult
from soclab.ui.dashboard import card
from soclab.ui.theme import DIFFICULTY_COLORS, MUTED, SUCCESS, badge_style

FEEDBACK = {
    SubmitResult.CORRECT: ("feedback_ok", "¡Correcto! Reto resuelto."),
    SubmitResult.INCORRECT: ("feedback_err", "Flag incorrecta. Revisa tu análisis."),
    SubmitResult.INVALID_FORMAT: ("feedback_warn", "Formato inválido: usa SOC{...} sin espacios."),
    SubmitResult.ALREADY_SOLVED: ("feedback_ok", "Este reto ya está resuelto."),
    SubmitResult.RATE_LIMITED: ("feedback_warn", "Espera un par de segundos antes de reintentar."),
}


def _badge(text: str, color: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("badge")
    label.setStyleSheet(badge_style(color))
    return label


class ChallengeDetailWidget(QScrollArea):
    start_requested = Signal(str)
    stop_requested = Signal(str)
    open_files_requested = Signal(str)
    hint_requested = Signal(str, int)
    flag_submitted = Signal(str, str)
    delete_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._view: ChallengeView | None = None
        body = QWidget()
        self.setWidget(body)
        root = QVBoxLayout(body)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        self.title = QLabel()
        self.title.setObjectName("h1")
        self.title.setWordWrap(True)
        self.badges = QHBoxLayout()
        self.badges.setSpacing(8)
        self.summary = QLabel()
        self.summary.setObjectName("muted")
        self.summary.setWordWrap(True)
        root.addWidget(self.title)
        root.addLayout(self.badges)
        root.addWidget(self.summary)

        # --- descripción
        self.description = QTextBrowser()
        self.description.setOpenLinks(False)
        self.description.anchorClicked.connect(self._open_link)
        self.description.setMinimumHeight(260)
        self.description.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.description.setAccessibleName("Descripción del reto")
        root.addWidget(self.description, 1)

        # --- entorno
        env_card, env = card()
        env.addWidget(self._heading("Entorno de análisis"))
        status_row = QHBoxLayout()
        self.status = QLabel("Estado del contenedor: desconocido")
        self.start_btn = QPushButton("▶  Iniciar contenedor")
        self.start_btn.setObjectName("primary")
        self.stop_btn = QPushButton("■  Detener")
        self.files_btn = QPushButton("📂  Abrir artefactos")
        self.start_btn.clicked.connect(lambda: self._emit(self.start_requested))
        self.stop_btn.clicked.connect(lambda: self._emit(self.stop_requested))
        self.files_btn.clicked.connect(lambda: self._emit(self.open_files_requested))
        status_row.addWidget(self.status, 1)
        for btn in (self.start_btn, self.stop_btn, self.files_btn):
            status_row.addWidget(btn)
        env.addLayout(status_row)
        cmd_row = QHBoxLayout()
        self.command = QLineEdit()
        self.command.setObjectName("command")
        self.command.setReadOnly(True)
        self.command.setAccessibleName("Comando para abrir una shell en el contenedor")
        self.copy_btn = QPushButton("Copiar")
        self.copy_btn.clicked.connect(self._copy_command)
        cmd_row.addWidget(self.command, 1)
        cmd_row.addWidget(self.copy_btn)
        env.addLayout(cmd_row)
        hint = QLabel("Abre una terminal y pega el comando para entrar al contenedor (sin red).")
        hint.setObjectName("muted")
        env.addWidget(hint)
        root.addWidget(env_card)

        # --- pistas
        hints_card, self.hints_layout = card()
        self.hints_layout.addWidget(self._heading("Pistas"))
        self.hints_box = QVBoxLayout()
        self.hints_layout.addLayout(self.hints_box)
        root.addWidget(hints_card)

        # --- flag
        flag_card, flag_layout = card()
        flag_layout.addWidget(self._heading("Enviar flag"))
        row = QHBoxLayout()
        self.flag_input = QLineEdit()
        self.flag_input.setObjectName("flag")
        self.flag_input.setMaxLength(flags.MAX_FLAG_LENGTH)
        self.flag_input.setAccessibleName("Flag")
        self.flag_input.returnPressed.connect(self._submit)
        self.flag_input.textChanged.connect(self._validate_input)
        self.submit_btn = QPushButton("Enviar")
        self.submit_btn.setObjectName("primary")
        self.submit_btn.clicked.connect(self._submit)
        row.addWidget(self.flag_input, 1)
        row.addWidget(self.submit_btn)
        flag_layout.addLayout(row)
        self.feedback = QLabel()
        self.feedback.setWordWrap(True)
        self.feedback.setAccessibleName("Resultado del envío")
        flag_layout.addWidget(self.feedback)
        root.addWidget(flag_card)

        footer = QHBoxLayout()
        self.meta = QLabel()
        self.meta.setObjectName("muted")
        self.delete_btn = QPushButton("Eliminar reto importado")
        self.delete_btn.setObjectName("danger")
        self.delete_btn.clicked.connect(lambda: self._emit(self.delete_requested))
        footer.addWidget(self.meta, 1)
        footer.addWidget(self.delete_btn)
        root.addLayout(footer)

    @staticmethod
    def _heading(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("h2")
        return label

    @property
    def slug(self) -> str | None:
        return self._view.slug if self._view else None

    def _emit(self, signal: Signal) -> None:  # type: ignore[type-arg]
        if self._view:
            signal.emit(self._view.slug)  # type: ignore[attr-defined]

    @staticmethod
    def _open_link(url: QUrl) -> None:
        # Solo enlaces web: evita que un manifiesto importado abra rutas locales.
        if url.scheme() in {"http", "https"}:
            QDesktopServices.openUrl(url)

    def _copy_command(self) -> None:
        QGuiApplication.clipboard().setText(self.command.text())
        self.copy_btn.setText("¡Copiado!")

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

    # ------------------------------------------------------------ API pública
    def show_challenge(self, view: ChallengeView) -> None:
        same = self._view is not None and self._view.slug == view.slug
        self._view = view
        self.title.setText(view.title)
        while self.badges.count():
            item = self.badges.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self.badges.addWidget(_badge(view.difficulty.label, DIFFICULTY_COLORS[view.difficulty]))
        self.badges.addWidget(_badge(view.category, MUTED))
        pts = f"{view.awarded_points}/{view.points} pts" if view.solved else f"{view.points} pts"
        self.badges.addWidget(_badge(pts, SUCCESS if view.solved else "#22d3ee"))
        if view.solved:
            self.badges.addWidget(_badge("✔ Resuelto", SUCCESS))
        self.badges.addStretch(1)
        self.summary.setText(view.summary)
        self.description.setMarkdown(view.description)
        self.command.setText(f"podman exec -it soclab-{view.slug} bash -l")
        self.copy_btn.setText("Copiar")
        self.start_btn.setVisible(view.has_container)
        self.stop_btn.setVisible(view.has_container)
        self.command.setVisible(view.has_container)
        self.copy_btn.setVisible(view.has_container)
        self._render_hints(view)
        self.flag_input.setPlaceholderText(view.flag_format)
        self.flag_input.setEnabled(not view.solved)
        if not same:
            self.flag_input.clear()
            self._set_feedback("", "")
        if view.solved:
            self._set_feedback("feedback_ok", f"Resuelto · {view.awarded_points} puntos obtenidos.")
        self._validate_input(self.flag_input.text())
        source = "importado" if view.source == "imported" else "incluido"
        self.meta.setText(f"Autor: {view.author} · Reto {source} · Intentos: {view.attempts}")
        self.delete_btn.setVisible(view.source == "imported")

    def _render_hints(self, view: ChallengeView) -> None:
        while self.hints_box.count():
            item = self.hints_box.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        if not view.hints:
            empty = QLabel("Este reto no tiene pistas.")
            empty.setObjectName("muted")
            self.hints_box.addWidget(empty)
        for position, text, cost in view.hints:
            if text is not None:
                label = QLabel(f"<b>Pista {position}</b> (−{cost} pts): {html.escape(text)}")
                label.setTextFormat(Qt.TextFormat.RichText)
                label.setWordWrap(True)
                label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                self.hints_box.addWidget(label)
            else:
                btn = QPushButton(f"Revelar pista {position}  (−{cost} pts)")
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
        self.status.setText(f"Estado del contenedor: {text}")
        self.start_btn.setEnabled(not busy and running is False)
        self.stop_btn.setEnabled(not busy and running is True)
