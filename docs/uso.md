# Guía de uso

## Pantalla principal

La interfaz imita un expediente de investigación: a la izquierda la carpeta de casos y a la
derecha la hoja del caso abierto.

```
┌──────── carpeta de casos ──────────┬───────────────── hoja del caso ─────────────────┐
│ SOC Lab                            │  Caso 07                          ┌──────────┐  │
│ 2 de 20 casos cerrados, 190 puntos │  Túnel DNS                        │ Resuelto │  │
│ [Buscar caso, categoría o tema]    │  Medio   Red   200 puntos         └──────────┘  │
│ [Dificultad ▾] [Estado ▾]          │  Reconstruye datos exfiltrados en DNS.          │
│ [Categoría ▾]                      │  Escenario / Objetivo / Evidencias / Formato    │
│ 01 Fuerza bruta SSH     [Cerrado]  │  ── Evidencias ───────────────────────────────  │
│    Fácil  Análisis de logs         │  [Abrir carpeta] [Iniciar entorno] [Detener]    │
│ 07 Túnel DNS              200 pts  │  podman exec -it soclab-07-dns-tunneling bash   │
│    Medio  Red                      │  ── Pistas ───────────────────────────────────  │
│ ...                                │  ── Conclusión ── SOC{...}______ [Cerrar caso]  │
│ [Ver resumen]  [Importar caso]     │                                                 │
└────────────────────────────────────┴─────────────────────────────────────────────────┘
```

- **Resumen** (`Ctrl+D`): casos cerrados, puntos, avance por dificultad y el siguiente caso
  sugerido (el abierto más fácil).
- **Carpeta de casos**: número de caso, título, dificultad (color) y categoría. Los casos
  resueltos muestran «Cerrado»; el seleccionado se marca como una etiqueta de evidencia.
- **Hoja del caso**: informe (escenario, objetivo, evidencias y formato de la flag),
  entorno de análisis, pistas y conclusión. Al cerrarlo aparece el sello «Resuelto».

## Resolver un caso

1. **Iniciar entorno de análisis**: la primera vez construye la imagen base (~75 MB, una
   sola vez) y la capa del caso (KB). Después arranca en segundos.
2. **Copiar comando** y pegarlo en tu terminal:
   ```bash
   podman exec -it soclab-01-ssh-bruteforce bash -l
   ```
   Herramientas disponibles: `bash grep awk jq python3 tcpdump xxd file less coreutils`.
   `/challenge` es de solo lectura; usa `/tmp` para tus archivos.
3. **Conclusión**: el campo valida el formato `SOC{...}` mientras escribes. `Enter` o
   **Cerrar caso** envía la flag.

| Resultado | Significado |
|---|---|
| Correcto. Caso cerrado | Se suman los puntos y aparece el sello |
| Flag incorrecta | Se registra el intento (no el valor) |
| Formato inválido | No cuenta como intento |
| Espera dos segundos | Enfriamiento tras un fallo (anti fuerza bruta) |

Las flags **no distinguen mayúsculas/minúsculas** salvo que el caso indique lo contrario,
y se ignoran espacios al inicio y al final.

## Pistas y puntuación

Cada reto tiene hasta 5 pistas con coste. Revelar una pide confirmación y el coste se
descuenta **al resolver**: `puntos obtenidos = puntos del reto − suma de pistas reveladas`
(mínimo 0). Las pistas reveladas después de resolver no restan.

## Contenedores

Todos los contenedores se ejecutan con el mismo endurecimiento, también los importados:

| Opción | Efecto |
|---|---|
| `--network=none` | Sin red: los artefactos no pueden "llamar a casa" |
| `--read-only` + `--tmpfs /tmp` | Sistema de archivos inmutable |
| `--cap-drop=ALL`, `no-new-privileges` | Sin capacidades privilegiadas |
| `--memory=256m`, `--pids-limit=128` | Límite de recursos |
| usuario `analyst` (uid 1000) | Sin root dentro del contenedor |
| `--rm`, `--init` | Se elimina al detener; parada inmediata |

Menú **Laboratorio → Reconstruir imagen base** fuerza un rebuild (p. ej. tras actualizar).

## Menús y atajos

| Acción | Atajo |
|---|---|
| Importar caso ZIP / carpeta | `Ctrl+I` / `Ctrl+Shift+I` |
| Resumen | `Ctrl+D` |
| Buscar | `Ctrl+F` |
| Documentación | `F1` |
| Reiniciar progreso | Menú Laboratorio |

## Dónde se guardan los datos

| SO | Ruta |
|---|---|
| Linux | `~/.local/share/soclab/` (o `$XDG_DATA_HOME/soclab`) |
| macOS | `~/Library/Application Support/soclab/` |
| Windows | `%APPDATA%\soclab\` |

Contiene `soclab.db` (progreso) y `challenges/` (casos importados). La variable
`SOCLAB_HOME` cambia esta ruta.
