# Guía de uso

## Pantalla principal

```
┌──────────────── barra lateral ────────────────┬──────────── panel / detalle ────────────┐
│ 🛡 SOC Lab        3/20 resueltos · 500 pts     │  Panel del analista                     │
│ [Buscar reto… (Ctrl+F)               ]        │  ┌ Puntuación ┐ ┌ Retos completados ───┐ │
│ [Dificultad ▾] [Estado ▾]                     │  │    500     │ │ ███████░░░░░  15%    │ │
│ [Categoría ▾]                                 │  └────────────┘ └──────────────────────┘ │
│ ✔ Fuerza bruta SSH       Logs   Fácil   100   │  Progreso por dificultad                │
│ • Cabeceras de phishing  ...    Fácil   100   │  Siguiente reto sugerido  [Ir al reto]  │
│ ...                                           │                                         │
│ [📊 Panel]                 [⬆ Importar reto]  │                                         │
└───────────────────────────────────────────────┴─────────────────────────────────────────┘
```

- **Panel** (`Ctrl+D`): puntuación, progreso total y por dificultad, y el siguiente reto
  sugerido (el pendiente más fácil).
- **Lista de retos**: ordenable por columna. `✔` = resuelto. Filtros combinables.
- **Detalle** (al seleccionar un reto): escenario, objetivo, artefactos y formato de flag.

## Resolver un reto

1. **Iniciar contenedor**: la primera vez construye la imagen base (~60 MB, una sola vez)
   y la capa del reto (KB). Después arranca en segundos.
2. **Copiar** el comando y pegarlo en tu terminal:
   ```bash
   podman exec -it soclab-01-ssh-bruteforce bash -l
   ```
   Herramientas disponibles: `bash grep awk jq python3 tcpdump xxd file less coreutils`.
   `/challenge` es de solo lectura; usa `/tmp` para tus archivos.
3. **Enviar flag**: el campo valida el formato `SOC{...}` en vivo. `Enter` envía.

| Resultado | Significado |
|---|---|
| ✅ Correcto | Reto resuelto, se suman los puntos |
| ❌ Incorrecta | Se registra el intento (no el valor) |
| ⚠ Formato inválido | No cuenta como intento |
| ⏳ Espera | Tras un fallo hay 2 s de enfriamiento (anti fuerza bruta) |

Las flags **no distinguen mayúsculas/minúsculas** salvo que el reto indique lo contrario,
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
| Importar reto ZIP / carpeta | `Ctrl+I` / `Ctrl+Shift+I` |
| Panel | `Ctrl+D` |
| Buscar | `Ctrl+F` |
| Documentación | `F1` |
| Reiniciar progreso | Menú Laboratorio |

## Dónde se guardan los datos

| SO | Ruta |
|---|---|
| Linux | `~/.local/share/soclab/` (o `$XDG_DATA_HOME/soclab`) |
| macOS | `~/Library/Application Support/soclab/` |
| Windows | `%APPDATA%\soclab\` |

Contiene `soclab.db` (progreso) y `challenges/` (retos importados). La variable
`SOCLAB_HOME` cambia esta ruta.
