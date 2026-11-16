import subprocess
from pathlib import Path

import pytest

from soclab.podman import HARDENING_ARGS, ChallengeContainer, PodmanClient, PodmanError


class FakeRunner:
    def __init__(self, responses: dict[str, tuple[int, str]] | None = None) -> None:
        self.calls: list[list[str]] = []
        self.responses = responses or {}

    def __call__(self, args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert kwargs["check"] is False
        assert "shell" not in kwargs
        self.calls.append(args)
        key = " ".join(args[1:3])
        code, out = self.responses.get(key, (0, ""))
        return subprocess.CompletedProcess(args, code, out, "boom" if code else "")


CONTAINER = ChallengeContainer("01-test", Path("/tmp/ctx"), Path("/tmp/ctx/Containerfile"))


def test_start_builds_missing_images_and_hardens() -> None:
    runner = FakeRunner({"image exists": (1, ""), "container inspect": (1, "")})
    PodmanClient("podman", runner=runner).start(CONTAINER)
    verbs = [c[1] for c in runner.calls]
    assert verbs.count("build") == 2  # base + reto
    run = next(c for c in runner.calls if c[1] == "run")
    for flag in HARDENING_ARGS:
        assert flag in run
    assert run[-1] == CONTAINER.image


def test_start_is_noop_when_running() -> None:
    runner = FakeRunner({"container inspect": (0, "true\n")})
    PodmanClient("podman", runner=runner).start(CONTAINER)
    assert [c[1] for c in runner.calls] == ["container"]


def test_stop_and_status() -> None:
    runner = FakeRunner({"container inspect": (0, "true")})
    client = PodmanClient("podman", runner=runner)
    assert client.is_running(CONTAINER)
    client.stop(CONTAINER)
    assert runner.calls[-1][:2] == ["podman", "stop"]


def test_errors_are_wrapped() -> None:
    with pytest.raises(PodmanError, match="no está instalado"):
        PodmanClient("", runner=FakeRunner()).version()
    with pytest.raises(PodmanError, match="boom"):
        PodmanClient("podman", runner=FakeRunner({"version --format": (125, "")})).version()

    def timeout(*_a: object, **_k: object) -> None:
        raise subprocess.TimeoutExpired("podman", 1)

    with pytest.raises(PodmanError, match="a tiempo"):
        PodmanClient("podman", runner=timeout).version()  # type: ignore[arg-type]


def test_container_names() -> None:
    assert CONTAINER.name == "soclab-01-test"
    assert CONTAINER.exec_command == "podman exec -it soclab-01-test bash -l"
