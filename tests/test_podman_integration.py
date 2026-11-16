"""Prueba real contra Podman: `uv run pytest -m podman`."""

import shutil
import subprocess

import pytest

from soclab.config import BUILTIN_CHALLENGES_DIR
from soclab.manifest import load_manifest
from soclab.podman import ChallengeContainer, PodmanClient, PodmanError

pytestmark = pytest.mark.podman


@pytest.fixture(scope="module")
def client() -> PodmanClient:
    if not shutil.which("podman"):
        pytest.skip("podman no instalado")
    c = PodmanClient()
    try:
        c.version()
    except PodmanError as exc:
        pytest.skip(f"podman no disponible: {exc}")
    return c


def test_challenge_container_lifecycle(client: PodmanClient) -> None:
    m = load_manifest(BUILTIN_CHALLENGES_DIR / "01-ssh-bruteforce")
    container = ChallengeContainer(m.slug, m.root, m.containerfile_path)  # type: ignore[arg-type]
    client.start(container, rebuild=True)
    try:
        assert client.is_running(container)
        script = "id -un; wc -l < /challenge/auth.log; touch /challenge/x 2>/dev/null || echo ro"
        out = subprocess.run(
            ["podman", "exec", container.name, "sh", "-c", script],
            capture_output=True, text=True, check=True,
        ).stdout.split()  # fmt: skip
        assert out[0] == "analyst"
        assert int(out[1]) > 100
        assert out[-1] == "ro"  # sistema de archivos de solo lectura
        net = subprocess.run(
            ["podman", "exec", container.name, "python3", "-c",
             "import socket; socket.create_connection(('1.1.1.1', 53), 2)"],
            capture_output=True, text=True, check=False,
        )  # fmt: skip
        assert net.returncode != 0  # sin red
    finally:
        client.stop(container)
    assert not client.is_running(container)
