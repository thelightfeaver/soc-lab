# Versionado y releases

SOC Lab sigue [versionado semántico](https://semver.org/lang/es/) calculado
automáticamente por **commitizen** a partir de los mensajes de commit
([Conventional Commits](https://www.conventionalcommits.org/es/)).

## De commit a versión

| Commit | Ejemplo | Incremento (mientras sea 0.x) |
|---|---|---|
| `fix:` | `fix(ui): el sello no se ocultaba` | PATCH `0.2.0 → 0.2.1` |
| `feat:` | `feat: reto de Kerberoasting` | MINOR `0.2.1 → 0.3.0` |
| `feat!:` o `BREAKING CHANGE:` | cambio de formato de `challenge.toml` | MINOR (por `major_version_zero`) |
| `docs:`, `test:`, `ci:`, `refactor:`, `chore:` | `docs: guía de retos` | Sin release |

La versión vive en un solo sitio, `pyproject.toml`. `cz bump` la propaga a `uv.lock` y
a `src/soclab/__init__.py`, actualiza `CHANGELOG.md`, crea el commit
`bump: version X → Y` y el tag `vY`.

## Calidad antes de cada commit (prek)

```bash
uv run prek install        # una vez: instala los hooks pre-commit, commit-msg y pre-push
```

| Momento | Hooks |
|---|---|
| `git commit` | espacios/fin de línea, TOML/YAML, archivos grandes, claves privadas, **ruff check** y **ruff format**, `uv.lock` sincronizado, validación de retos |
| mensaje de commit | **commitizen**: rechaza mensajes que no sigan Conventional Commits |
| `git push` | commitizen sobre todos los commits de la rama y **pytest** |

Para escribir el mensaje con asistente: `uv run cz commit`.

## Publicar una release

**Opción A — desde GitHub (recomendada).** *Actions → Release → Run workflow* y elige
`auto` (commitizen decide según los commits) o fuerza `PATCH`/`MINOR`/`MAJOR`.

**Opción B — desde tu equipo.**

```bash
uv run cz bump              # calcula versión, CHANGELOG, commit y tag
git push --follow-tags      # sube el commit y el tag anotado; el tag dispara la release
```

En ambos casos el workflow [`release.yml`](../.github/workflows/release.yml):

1. Comprueba que el tag coincide con la versión del proyecto.
2. Ejecuta los tests en Linux y Windows.
3. Empaqueta la app con PyInstaller (`scripts/build_app.py`): Python, Qt, fuentes y los
   20 retos en una carpeta autónoma.
4. Publica la GitHub Release con las notas del CHANGELOG, los binarios y `SHA256SUMS.txt`.

| Archivo | Sistema |
|---|---|
| `soclab-X.Y.Z-linux-x86_64.tar.gz` | Linux x86_64 (glibc 2.39+, p. ej. Ubuntu 24.04+) |
| `soclab-X.Y.Z-windows-x86_64.zip` | Windows 10/11 x86_64 |

Los binarios incluyen todo salvo **Podman**, que se instala aparte para usar los
entornos de análisis.

## Empaquetar en local

```bash
uv sync --group release
uv run python scripts/build_app.py   # → dist/soclab-<versión>-<so>-<arquitectura>.*
```

Funciona también en macOS para pruebas locales (`macos-arm64`).
