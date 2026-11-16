# Crear e importar retos

## Estructura

```
mi-reto/
├── challenge.toml     # obligatorio
├── Containerfile      # opcional (si existe [container])
└── files/             # artefactos que verá el analista en /challenge
    └── evidencia.log
```

## `challenge.toml`

```toml
schema_version = 1
slug = "mi-reto-dns"                 # minúsculas, dígitos y guiones (3-64)
title = "Mi reto de DNS"             # 3-120
category = "Red"                     # 2-60 (agrupa en el filtro)
difficulty = "medio"                 # facil | medio | dificil | experto
points = 200                         # 1-1000
author = "Tu nombre"                 # opcional
summary = "Una línea para la lista." # 5-240
flag_format = "SOC{dominio}"         # pista de formato para el analista
flag_hash = "scrypt$16384$8$1$..."   # generado con `soclab hash-flag`
case_sensitive = false               # opcional (por defecto false)
description = '''
## Escenario
Markdown con el contexto, objetivo y artefactos.
'''

[container]
containerfile = "Containerfile"      # ruta relativa dentro del reto

[[hints]]                            # 0-5 pistas
text = "Mira las consultas TXT."
cost = 20                            # 0..points
```

Reglas de validación: claves desconocidas = error; todos los errores se reportan a la vez.

## Generar el hash de la flag

```bash
uv run soclab hash-flag            # la pide sin mostrarla (recomendado)
uv run soclab hash-flag 'SOC{mi_respuesta}' --case-sensitive
```

**Nunca** pongas la flag en claro en el manifiesto ni en los artefactos (salvo que
encontrarla sea el reto).

## Containerfile

Parte de la imagen base para que el reto pese solo lo que sus artefactos:

```dockerfile
FROM localhost/soclab-base:1
COPY files/ /challenge/
```

La base incluye `bash coreutils file gawk grep jq less python3 tcpdump xxd` y el usuario
`analyst`. Si necesitas más herramientas añade `USER root`, `RUN apk add --no-cache ...` y
`USER analyst`. Recuerda: el contenedor se ejecutará **sin red** y en **solo lectura**.

## Validar e importar

```bash
uv run soclab validate ./mi-reto
cd mi-reto/.. && zip -r mi-reto.zip mi-reto
```

En la app: **⬆ Importar reto** (ZIP) o **Archivo → Importar reto (carpeta)**. Si el slug ya
existe como importado, se ofrece reemplazarlo conservando el progreso. Los retos importados
se pueden eliminar desde su detalle.

Límites: 50 MiB descomprimidos, 500 archivos, sin enlaces simbólicos.

## Checklist de calidad de un reto

- [ ] La respuesta es **única** y derivable solo de los artefactos.
- [ ] Hay **distractores** realistas (ruido, falsos positivos).
- [ ] La descripción dice qué buscar y el **formato exacto** de la flag.
- [ ] Las pistas guían sin regalar la respuesta; la última es la más cara.
- [ ] Datos ficticios: IPs RFC 5737 (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`),
      dominios inventados, sin datos personales reales.
