# 🛡 SOC Lab

[![CI](https://github.com/thelightfeaver/soc-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/thelightfeaver/soc-lab/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.14-blue)
![Podman](https://img.shields.io/badge/podman-rootless-892CA0)
[![Conventional Commits](https://img.shields.io/badge/commits-conventional-fe5196)](https://www.conventionalcommits.org)

Laboratorio de **analista SOC / Blue Team** con **20 retos** de dificultad creciente
(Fácil → Experto). Cada reto se analiza en un **contenedor Podman liviano, sin red y de
solo lectura**, y se completa enviando una **flag `SOC{...}`** desde una interfaz de
escritorio hecha con **PySide6** con estilo de expediente forense.

| Dificultad | Retos | Puntos c/u |
|---|---|---|
| 🟢 Fácil | 6 | 100 |
| 🟡 Medio | 6 | 200 |
| 🟠 Difícil | 5 | 300 |
| 🟣 Experto | 3 | 500 |

Temas: logs SSH y web, phishing, PowerShell ofuscado, IOCs, DNS (blocklist y túneles),
beaconing de C2, SQLi, eventos de Windows, persistencia en Linux, árboles de procesos,
movimiento lateral, exfiltración, ransomware, XOR, JWT, PCAP, incidentes multietapa y
manipulación de logs. Catálogo completo: [docs/retos.md](docs/retos.md).

## Inicio rápido

Requisitos: [uv](https://docs.astral.sh/uv/), Python 3.14 y
[Podman](https://podman.io/docs/installation) (en macOS/Windows: `podman machine init && podman machine start`).

```bash
git clone https://github.com/thelightfeaver/soc-lab.git
cd soc-lab
uv sync
uv run soclab
```

1. Elige un caso de la lista (filtra por dificultad, categoría o estado).
2. Pulsa **Iniciar entorno de análisis** y copia el comando `podman exec -it soclab-<caso> bash -l`
   en una terminal. Las evidencias están en `/challenge`.
3. Analiza, escribe tu conclusión como flag y pulsa **Cerrar caso**. Las pistas restan puntos.

> ¿Sin Podman? Usa **Abrir carpeta de evidencias** y analiza los archivos con tus propias
> herramientas: la flag se valida igual.

La interfaz usa el estilo *expediente forense*: cada reto es un caso con su informe, y al
resolverlo recibe un sello «Resuelto».

## Documentación

| Documento | Contenido |
|---|---|
| [docs/uso.md](docs/uso.md) | Guía de la interfaz, puntuación, pistas y contenedores |
| [docs/arquitectura.md](docs/arquitectura.md) | Cómo funciona por dentro (capas, BD, seguridad) |
| [docs/crear-retos.md](docs/crear-retos.md) | Formato `challenge.toml`, crear e importar tus retos |
| [docs/desarrollo.md](docs/desarrollo.md) | Entorno de desarrollo, calidad, commits y CI |
| [docs/retos.md](docs/retos.md) | Catálogo de retos (sin spoilers) |

## Stack

Python 3.14 · PySide6 · peewee + SQLite · Podman · ruff · prek · commitizen · pytest ·
GitHub Actions (Linux, macOS y Windows).

## Licencia

[MIT](LICENSE). Todos los datos de los retos son ficticios; las IPs usan rangos de
documentación (RFC 5737).
