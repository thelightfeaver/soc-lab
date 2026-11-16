# Desarrollo

## Entorno

```bash
uv sync                    # crea .venv con Python 3.14 y dependencias de desarrollo
uv run prek install        # hooks pre-commit, commit-msg y pre-push
uv run soclab              # lanza la UI
```

## Calidad

| Herramienta | Uso |
|---|---|
| **ruff** | Lint (reglas amplias: seguridad `S`, tipos `ANN`, `PL`, `B`, `UP`…) y formato |
| **prek** | Ejecuta los hooks de `.pre-commit-config.yaml` (ruff, TOML/YAML, claves privadas, tamaño de archivos, commitizen) |
| **commitizen** | Valida Conventional Commits, genera versión y CHANGELOG |
| **pytest / pytest-qt** | Tests unitarios, de UI (offscreen) y de integración con Podman |

```bash
uv run ruff check . && uv run ruff format --check .
uv run prek run --all-files
uv run pytest --cov                   # sin Podman
uv run pytest -m podman               # integración real con Podman
```

## Commits, versiones y releases

Ver [versionado.md](versionado.md): Conventional Commits, `cz bump`, hooks de prek y
publicación de binarios para Linux y Windows.

## Regenerar los retos incluidos

```bash
uv run python scripts/generate_challenges.py
uv run pytest tests/test_challenges.py
```

⚠ `scripts/generate_challenges.py` y `tests/solvers.py` contienen las soluciones.

## Pipeline (GitHub Actions)

| Job | SO | Qué hace |
|---|---|---|
| `quality` | Ubuntu | `ruff check`, `ruff format --check`, `prek run --all-files`, `cz check` en PRs |
| `test` | Ubuntu · macOS · Windows | `soclab validate`, pytest + cobertura (UI offscreen), `uv build` |
| `podman` | Ubuntu | Construye la imagen base y **los 20 retos**, prueba el ciclo de vida real de un contenedor (sin red, solo lectura) |
| `release` | Ubuntu · Windows | Manual o por tag `v*`: `cz bump`, tests, binarios PyInstaller y GitHub Release |

Dependabot actualiza semanalmente las acciones y las dependencias de uv.
