"""Ventana principal: lista filtrable de retos + panel / detalle."""

from pathlib import Path

from PySide6.QtCore import QItemSelection, QSignalBlocker, Qt, QUrl
from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from soclab import __version__
from soclab.config import imported_challenges_dir
from soclab.importer import ChallengeImportError
from soclab.manifest import Difficulty, ManifestError
from soclab.podman import ChallengeContainer, PodmanClient
from soclab.services import ChallengeView, LabService, SubmitResult
from soclab.ui.dashboard import DashboardWidget
from soclab.ui.detail import ChallengeDetailWidget
from soclab.ui.models import VIEW_ROLE, ChallengeFilterProxy, ChallengeTableModel
from soclab.ui.widgets import CaseDelegate
from soclab.ui.workers import TaskRunner

DOCS_URL = "https://github.com/thelightfeaver/soc-lab/tree/main/docs"


class MainWindow(QMainWindow):
    def __init__(
        self,
        service: LabService,
        podman: PodmanClient,
        *,
        import_dir: Path | None = None,
        confirm: bool = True,
    ) -> None:
        super().__init__()
        self.service = service
        self.podman = podman
        self.import_dir = import_dir or imported_challenges_dir()
        self.confirm = confirm  # False en tests: no se muestran diálogos modales
        self.tasks = TaskRunner(self)
        self.podman_ok = False
        self.setWindowTitle("SOC Lab")
        self.resize(1360, 860)
        self.setMinimumSize(1000, 640)

        self.model = ChallengeTableModel(self)
        self.proxy = ChallengeFilterProxy(self)
        self.proxy.setSourceModel(self.model)

        self._build_ui()
        self._build_menu()
        self.refresh()
        self.show_dashboard()
        self.check_podman()

    # ================================================================ construcción
    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(14, 16, 14, 14)
        side.setSpacing(10)
        brand = QLabel("SOC Lab")
        brand.setObjectName("brand")
        self.progress_label = QLabel()
        self.progress_label.setObjectName("muted")
        side.addWidget(brand)
        side.addWidget(self.progress_label)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar caso, categoría o tema")
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName("Buscar caso")
        self.search.setToolTip("Ctrl+F")
        self.difficulty_filter = QComboBox()
        self.difficulty_filter.addItem("Todas las dificultades", None)
        for d in Difficulty:
            self.difficulty_filter.addItem(d.label, d.value)
        self.category_filter = QComboBox()
        self.status_filter = QComboBox()
        for text, key in (("Todos", "all"), ("Abiertos", "pending"), ("Cerrados", "solved")):
            self.status_filter.addItem(text, key)
        for combo, name in (
            (self.difficulty_filter, "Filtrar por dificultad"),
            (self.category_filter, "Filtrar por categoría"),
            (self.status_filter, "Filtrar por estado"),
        ):
            combo.setAccessibleName(name)
            combo.currentIndexChanged.connect(self._apply_filters)
        self.search.textChanged.connect(self._apply_filters)
        side.addWidget(self.search)
        row = QHBoxLayout()
        row.addWidget(self.difficulty_filter)
        row.addWidget(self.status_filter)
        side.addLayout(row)
        side.addWidget(self.category_filter)

        self.case_list = QListView()
        self.case_list.setObjectName("cases")
        self.case_list.setModel(self.proxy)
        self.case_list.setItemDelegate(CaseDelegate(self.case_list))
        self.case_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.case_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.case_list.setMouseTracking(True)
        self.case_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.case_list.setUniformItemSizes(True)
        self.case_list.setAccessibleName("Lista de casos")
        self.case_list.selectionModel().selectionChanged.connect(self._on_selection)
        side.addWidget(self.case_list, 1)

        buttons = QHBoxLayout()
        dash_btn = QPushButton("Ver resumen")
        dash_btn.clicked.connect(self.show_dashboard)
        import_btn = QPushButton("Importar caso")
        import_btn.clicked.connect(self.import_zip)
        buttons.addWidget(dash_btn)
        buttons.addWidget(import_btn)
        side.addLayout(buttons)

        self.stack = QStackedWidget()
        self.dashboard = DashboardWidget()
        self.dashboard.open_challenge.connect(self.select_challenge)
        self.detail = ChallengeDetailWidget()
        self.detail.start_requested.connect(self.start_container)
        self.detail.stop_requested.connect(self.stop_container)
        self.detail.open_files_requested.connect(self.open_files)
        self.detail.hint_requested.connect(self.reveal_hint)
        self.detail.flag_submitted.connect(self.submit_flag)
        self.detail.delete_requested.connect(self.delete_challenge)
        self.stack.addWidget(self.dashboard)
        self.stack.addWidget(self.detail)

        splitter.addWidget(sidebar)
        splitter.addWidget(self.stack)
        splitter.setSizes([400, 960])
        splitter.setChildrenCollapsible(False)

        self.podman_label = QLabel("Podman: comprobando…")
        self.statusBar().addPermanentWidget(self.podman_label)

    def _build_menu(self) -> None:
        bar = self.menuBar()
        file_menu = bar.addMenu("&Archivo")
        self._action(file_menu, "Importar caso (ZIP)…", self.import_zip, "Ctrl+I")
        self._action(file_menu, "Importar caso (carpeta)…", self.import_folder, "Ctrl+Shift+I")
        file_menu.addSeparator()
        self._action(file_menu, "Salir", self.close, QKeySequence.StandardKey.Quit)

        lab = bar.addMenu("&Laboratorio")
        self._action(lab, "Resumen", self.show_dashboard, "Ctrl+D")
        self._action(lab, "Buscar caso", self.focus_search, QKeySequence.StandardKey.Find)
        self._action(lab, "Comprobar Podman", self.check_podman)
        self._action(lab, "Reconstruir imagen base", self.rebuild_base)
        lab.addSeparator()
        self._action(lab, "Reiniciar progreso…", self.reset_progress)

        help_menu = bar.addMenu("A&yuda")
        self._action(
            help_menu, "Documentación", self.open_docs, QKeySequence.StandardKey.HelpContents
        )
        self._action(help_menu, "Acerca de SOC Lab", self.about)

    def _action(self, menu: object, text: str, slot: object, shortcut: object = None) -> QAction:
        action = QAction(text, self)
        if shortcut is not None:
            action.setShortcut(shortcut)  # type: ignore[arg-type]
        action.triggered.connect(slot)  # type: ignore[arg-type]
        menu.addAction(action)  # type: ignore[attr-defined]
        return action

    # ================================================================ datos
    def refresh(self) -> None:
        selected = self.detail.slug if self.stack.currentWidget() is self.detail else None
        views = self.service.list()
        self.model.set_challenges(views)
        current = self.category_filter.currentData()
        with QSignalBlocker(self.category_filter):
            self.category_filter.clear()
            self.category_filter.addItem("Todas las categorías", None)
            for category in self.service.categories():
                self.category_filter.addItem(category, category)
            index = self.category_filter.findData(current)
            self.category_filter.setCurrentIndex(max(index, 0))
        self._apply_filters()
        stats = self.service.stats()
        self.progress_label.setText(
            f"{stats.solved} de {stats.total} casos cerrados, {stats.points_earned} puntos"
        )
        self.dashboard.update_stats(stats, views)
        if selected:
            self._select_row(selected)

    def _apply_filters(self) -> None:
        self.proxy.set_filters(
            text=self.search.text(),
            difficulty=self.difficulty_filter.currentData(),
            category=self.category_filter.currentData(),
            status=self.status_filter.currentData() or "all",
        )

    def _select_row(self, slug: str) -> None:
        row = self.model.row_of(slug)
        if row < 0:
            return
        index = self.proxy.mapFromSource(self.model.index(row, 0))
        if index.isValid():
            with QSignalBlocker(self.case_list.selectionModel()):
                self.case_list.setCurrentIndex(index)
            self.case_list.scrollTo(index)

    def _on_selection(self, selected: QItemSelection, _deselected: QItemSelection) -> None:
        indexes = selected.indexes()
        if indexes:
            view: ChallengeView = indexes[0].data(VIEW_ROLE)
            self.open_challenge(view.slug)

    def current_view(self) -> ChallengeView | None:
        slug = self.detail.slug
        return self.service.get(slug) if slug else None

    # ================================================================ navegación
    def show_dashboard(self) -> None:
        self.case_list.clearSelection()
        self.stack.setCurrentWidget(self.dashboard)

    def focus_search(self) -> None:
        self.search.setFocus()
        self.search.selectAll()

    def select_challenge(self, slug: str) -> None:
        self._select_row(slug)
        self.open_challenge(slug)

    def open_challenge(self, slug: str) -> None:
        view = self.service.get(slug)
        self.detail.show_challenge(view)
        self.stack.setCurrentWidget(self.detail)
        self.refresh_container_state(view)

    # ================================================================ podman
    def _container(self, view: ChallengeView) -> ChallengeContainer | None:
        if not view.has_container:
            return None
        return ChallengeContainer(view.slug, view.root, view.root / "Containerfile")

    def check_podman(self) -> None:
        def done(version: str) -> None:
            self.podman_ok = True
            self.podman_label.setText(f"Podman {version} ✔")
            view = self.current_view()
            if view:
                self.refresh_container_state(view)

        def fail(error: str) -> None:
            self.podman_ok = False
            self.podman_label.setText("Podman no disponible ✖")
            self.podman_label.setToolTip(error)

        self.tasks.submit(self.podman.version, done, fail)

    def refresh_container_state(self, view: ChallengeView) -> None:
        container = self._container(view)
        if container is None:
            return
        if not self.podman_ok:
            self.detail.set_container_state("Podman no disponible", running=None)
            return
        self.detail.set_container_state("comprobando…", running=None, busy=True)

        def done(running: bool) -> None:  # noqa: FBT001
            if self.detail.slug == view.slug:
                state = "en ejecución" if running else "detenido"
                self.detail.set_container_state(state, running=running)

        self.tasks.submit(lambda: self.podman.is_running(container), done, self._podman_error)

    def _podman_error(self, error: str) -> None:
        self.statusBar().showMessage(f"Error de Podman: {error}", 10_000)
        view = self.current_view()
        if view:
            self.detail.set_container_state("error (ver barra de estado)", running=False)

    def start_container(self, slug: str) -> None:
        view = self.service.get(slug)
        container = self._container(view)
        if container is None:
            return
        self.detail.set_container_state(
            "preparando… la primera vez construye la imagen", running=None, busy=True
        )
        self.statusBar().showMessage(f"Iniciando {container.name}…")

        def done(_: object) -> None:
            self.statusBar().showMessage(f"{container.name} en ejecución", 5_000)
            self.refresh_container_state(view)

        self.tasks.submit(lambda: self.podman.start(container), done, self._podman_error)

    def stop_container(self, slug: str) -> None:
        view = self.service.get(slug)
        container = self._container(view)
        if container is None:
            return
        self.detail.set_container_state("deteniendo…", running=None, busy=True)
        self.tasks.submit(
            lambda: self.podman.stop(container),
            lambda _: self.refresh_container_state(view),
            self._podman_error,
        )

    def rebuild_base(self) -> None:
        self.statusBar().showMessage("Reconstruyendo imagen base…")
        self.tasks.submit(
            lambda: self.podman.ensure_base_image(rebuild=True),
            lambda _: self.statusBar().showMessage("Imagen base lista", 5_000),
            self._podman_error,
        )

    # ================================================================ acciones de reto
    def open_files(self, slug: str) -> None:
        files = self.service.get(slug).files_dir
        if not files.is_dir():
            self._warn("Artefactos no encontrados", f"No existe la carpeta:\n{files}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(files)))

    def reveal_hint(self, slug: str, position: int) -> None:
        view = self.service.get(slug)
        cost = next(c for p, _, c in view.hints if p == position)
        if self.confirm and not self._ask(
            "Revelar pista",
            f"Revelar la pista {position} restará {cost} puntos si resuelves el reto. ¿Continuar?",
        ):
            return
        self.service.reveal_hint(slug, position)
        self.detail.show_challenge(self.service.get(slug))

    def submit_flag(self, slug: str, flag: str) -> None:
        result = self.service.submit_flag(slug, flag)
        view = self.service.get(slug)
        self.detail.show_challenge(view)
        self.detail.show_result(result)
        if result is SubmitResult.CORRECT:
            self.refresh()
            self.statusBar().showMessage(
                f"Caso cerrado: {view.title} (+{view.awarded_points} pts)", 8_000
            )

    def delete_challenge(self, slug: str) -> None:
        view = self.service.get(slug)
        if self.confirm and not self._ask(
            "Eliminar caso",
            f"¿Eliminar «{view.title}» y su progreso? Esta acción no se puede deshacer.",
        ):
            return
        container = self._container(view)
        if container and self.podman_ok:
            self.tasks.submit(lambda: self.podman.stop(container))
        self.service.delete_imported(slug)
        self.refresh()
        self.show_dashboard()

    def reset_progress(self) -> None:
        if self.confirm and not self._ask(
            "Reiniciar progreso",
            "Se borrarán los casos cerrados, los intentos y las pistas vistas. ¿Continuar?",
        ):
            return
        self.service.reset_progress()
        self.refresh()
        view = self.current_view()
        if view and self.stack.currentWidget() is self.detail:
            self.detail.show_challenge(view)

    # ================================================================ importación
    def import_zip(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Importar caso", "", "Caso SOC Lab (*.zip)")
        if path:
            self.import_path(Path(path))

    def import_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Importar carpeta de caso")
        if path:
            self.import_path(Path(path))

    def import_path(self, path: Path, *, replace: bool = False) -> str | None:
        if (
            self.confirm
            and not replace
            and not self._ask(
                "Importar caso",
                "Los casos importados construyen una imagen a partir de su Containerfile. "
                "Importa solo casos de fuentes de confianza.\n\n¿Continuar?",
            )
        ):
            return None
        try:
            slug = self.service.import_challenge(path, self.import_dir, replace=replace)
        except ManifestError as exc:
            self._warn("Manifiesto inválido", "\n".join(f"• {e}" for e in exc.errors))
            return None
        except ChallengeImportError as exc:
            if (
                "ya existe" in str(exc)
                and self.confirm
                and self._ask("Caso existente", f"{exc}.\n¿Reemplazarlo? Se conserva el progreso.")
            ):
                return self.import_path(path, replace=True)
            self._warn("No se pudo importar", str(exc))
            return None
        except OSError as exc:
            self._warn("Error de lectura", str(exc))
            return None
        self.refresh()
        self.select_challenge(slug)
        self.statusBar().showMessage(f"Caso «{slug}» importado", 6_000)
        return slug

    # ================================================================ utilidades
    def open_docs(self) -> None:
        QDesktopServices.openUrl(QUrl(DOCS_URL))

    def about(self) -> None:
        QMessageBox.about(
            self,
            "Acerca de SOC Lab",
            f"<h3>SOC Lab {__version__}</h3><p>Laboratorio de casos SOC y Blue Team con "
            "entornos Podman ligeros.</p><p>Python · PySide6 · peewee · SQLite</p>",
        )

    def _ask(self, title: str, text: str) -> bool:
        answer = QMessageBox.question(self, title, text)
        return answer == QMessageBox.StandardButton.Yes

    def _warn(self, title: str, text: str) -> None:
        if self.confirm:
            QMessageBox.warning(self, title, text)
        self.statusBar().showMessage(f"{title}: {text.splitlines()[0]}", 10_000)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.tasks.wait(5_000)
        super().closeEvent(event)
