"""Cliente mínimo de Podman basado en la CLI (sin shell, argumentos en lista)."""

import shutil
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from soclab.config import BASE_IMAGE_DIR, BASE_IMAGE_TAG

Runner = Callable[..., subprocess.CompletedProcess[str]]

# Endurecimiento aplicado a TODOS los contenedores, incluidos los importados.
HARDENING_ARGS: tuple[str, ...] = (
    "--network=none",
    "--cap-drop=ALL",
    "--security-opt=no-new-privileges",
    "--read-only",
    "--tmpfs=/tmp:rw,size=32m,mode=1777",
    "--memory=256m",
    "--pids-limit=128",
    "--init",
)


class PodmanError(RuntimeError):
    """Fallo al invocar Podman."""


@dataclass(frozen=True, slots=True)
class ChallengeContainer:
    slug: str
    context: Path
    containerfile: Path

    @property
    def image(self) -> str:
        return f"localhost/soclab/{self.slug}:latest"

    @property
    def name(self) -> str:
        return f"soclab-{self.slug}"

    @property
    def exec_command(self) -> str:
        return f"podman exec -it {self.name} bash -l"


class PodmanClient:
    def __init__(
        self,
        binary: str | None = None,
        *,
        runner: Runner = subprocess.run,
        build_timeout: int = 900,
        timeout: int = 60,
    ) -> None:
        self.binary = shutil.which("podman") if binary is None else binary
        self._runner = runner
        self.build_timeout = build_timeout
        self.timeout = timeout

    def _run(
        self, args: Sequence[str], *, timeout: int | None = None, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        if not self.binary:
            raise PodmanError("Podman no está instalado o no está en el PATH.")
        try:
            result = self._runner(
                [self.binary, *args],
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise PodmanError(f"Podman no respondió a tiempo: {' '.join(args[:2])}") from exc
        except OSError as exc:
            raise PodmanError(f"No se pudo ejecutar Podman: {exc}") from exc
        if check and result.returncode != 0:
            detail = (result.stderr or result.stdout).strip().splitlines()
            raise PodmanError(detail[-1] if detail else f"podman {args[0]} falló")
        return result

    # ------------------------------------------------------------ estado
    def version(self) -> str:
        """Versión del servidor; falla si la máquina/servicio no está disponible."""
        return self._run(["version", "--format", "{{.Server.Version}}"]).stdout.strip()

    def image_exists(self, tag: str) -> bool:
        return self._run(["image", "exists", tag], check=False).returncode == 0

    def is_running(self, container: ChallengeContainer) -> bool:
        result = self._run(
            ["container", "inspect", "--format", "{{.State.Running}}", container.name],
            check=False,
        )
        return result.returncode == 0 and result.stdout.strip() == "true"

    # ------------------------------------------------------------ acciones
    def build(self, tag: str, context: Path, containerfile: Path) -> None:
        self._run(
            ["build", "--pull=missing", "-t", tag, "-f", str(containerfile), str(context)],
            timeout=self.build_timeout,
        )

    def ensure_base_image(self, *, rebuild: bool = False) -> None:
        if rebuild or not self.image_exists(BASE_IMAGE_TAG):
            self.build(BASE_IMAGE_TAG, BASE_IMAGE_DIR, BASE_IMAGE_DIR / "Containerfile")

    def start(self, container: ChallengeContainer, *, rebuild: bool = False) -> None:
        if self.is_running(container):
            return
        self.ensure_base_image()
        if rebuild or not self.image_exists(container.image):
            self.build(container.image, container.context, container.containerfile)
        self._run(
            [
                "run",
                "-d",
                "--rm",
                "--name",
                container.name,
                "--hostname",
                container.slug[:63],
                "--label",
                "soclab=1",
                *HARDENING_ARGS,
                container.image,
            ]
        )

    def stop(self, container: ChallengeContainer) -> None:
        if self.is_running(container):
            self._run(["stop", "-t", "3", container.name])
