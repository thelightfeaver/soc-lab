"""Soluciones de referencia (¡SPOILERS!). Derivan cada flag desde los artefactos.

Sirven para garantizar en CI que todos los retos son resolubles y que el
hash del manifiesto coincide con la respuesta que se obtiene analizando.
"""

import base64
import email
import gzip
import ipaddress
import itertools
import json
import re
import statistics
import struct
from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

Solver = Callable[[Path], str]
SOLVERS: dict[str, Solver] = {}


def solver(slug: str) -> Callable[[Solver], Solver]:
    def deco(fn: Solver) -> Solver:
        SOLVERS[slug] = fn
        return fn

    return deco


def lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in lines(path) if x.strip()]


def ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@solver("01-ssh-bruteforce")
def s01(d: Path) -> str:
    fails: Counter[str] = Counter()
    accepted = set()
    for line in lines(d / "auth.log"):
        if m := re.search(r"Failed password for (?:invalid user )?\S+ from (\S+)", line):
            fails[m.group(1)] += 1
        if m := re.search(r"Accepted \w+ for \S+ from (\S+)", line):
            accepted.add(m.group(1))
    (ip,) = [ip for ip, n in fails.items() if n >= 20 and ip in accepted]
    return f"SOC{{{ip}}}"


@solver("02-phishing-headers")
def s02(d: Path) -> str:
    msg = email.message_from_string((d / "correo_sospechoso.eml").read_text())
    first_hop = msg.get_all("Received")[-1]
    return "SOC{" + re.search(r"\[(\d+(?:\.\d+){3})\]", first_hop).group(1) + "}"


@solver("03-powershell-encoded")
def s03(d: Path) -> str:
    for ev in jsonl(d / "process_events.jsonl"):
        if m := re.search(r"-(?:enc|EncodedCommand)\s+(\S+)", ev["CommandLine"], re.IGNORECASE):
            decoded = base64.b64decode(m.group(1)).decode("utf-16-le")
            if url := re.search(r"https?://([^/'\"]+)", decoded):
                return f"SOC{{{url.group(1)}}}"
    raise AssertionError


@solver("04-ioc-hash-match")
def s04(d: Path) -> str:
    feed = {
        row.split(",")[0].lower() for row in lines(d / "feed_iocs.csv")[1:] if ",sha256," in row
    }
    (path,) = [
        r.split(",")[0] for r in lines(d / "inventario_binarios.csv")[1:] if r.split(",")[1] in feed
    ]
    return "SOC{" + path.split("\\")[-1] + "}"


@solver("05-hidden-admin-panel")
def s05(d: Path) -> str:
    hits = {
        m.group(1)
        for line in lines(d / "access.log")
        if "gobuster" in line and (m := re.search(r'"GET (\S+) HTTP/1.1" 200', line))
    }
    (path,) = hits
    return f"SOC{{{path}}}"


@solver("06-dns-blocklist")
def s06(d: Path) -> str:
    blocked = [x.strip() for x in lines(d / "blocklist.txt") if x.strip() and not x.startswith("#")]
    clients = set()
    for line in lines(d / "dns.log"):
        fields = dict(f.split("=", 1) for f in line.split()[1:])
        q = fields["query"]
        if any(q == b or q.endswith("." + b) for b in blocked):
            clients.add(fields["client"])
    (client,) = clients
    return f"SOC{{{client}}}"


@solver("07-dns-tunneling")
def s07(d: Path) -> str:
    chunks = {}
    for line in lines(d / "dns.log"):
        if m := re.search(r"query=([0-9a-f]+)\.(\d+)\.t\.exfil-cdn\.org", line):
            chunks[int(m.group(2))] = m.group(1)
    data = bytes.fromhex("".join(chunks[i] for i in sorted(chunks))).decode()
    return re.search(r"SOC\{[^}]+\}", data).group(0)


@solver("08-c2-beaconing")
def s08(d: Path) -> str:
    groups: dict[tuple[str, str, str], list[datetime]] = defaultdict(list)
    for row in lines(d / "conexiones.csv")[1:]:
        t, src, dst, port, *_ = row.split(",")
        groups[src, dst, port].append(ts(t))
    found = []
    for (_, dst, port), times in groups.items():
        if len(times) < 50:
            continue
        gaps = [(b - a).total_seconds() for a, b in itertools.pairwise(times)]
        if statistics.pstdev(gaps) < 5:
            found.append(f"{dst}:{port}")
    (beacon,) = found
    return f"SOC{{{beacon}}}"


@solver("09-sql-injection")
def s09(d: Path) -> str:
    tables = set()
    for line in lines(d / "access.log"):
        m = re.search(r'"GET (\S+) HTTP/1.1" (\d{3})', line)
        if not m or m.group(2) != "200":
            continue
        url = unquote(m.group(1))
        t = re.search(r"UNION\s+SELECT\s+.+?\s+FROM\s+([\w.]+)", url, re.IGNORECASE)
        if t and not t.group(1).startswith("information_schema"):
            tables.add(t.group(1))
    (table,) = tables
    return f"SOC{{{table}}}"


@solver("10-rogue-account")
def s10(d: Path) -> str:
    events = jsonl(d / "security_events.jsonl")
    attacker_logons = {
        e["TargetLogonId"]
        for e in events
        if e["EventID"] == 4624 and e["LogonType"] == 10 and not e["IpAddress"].startswith("10.")
    }
    (user,) = [
        e["TargetUserName"]
        for e in events
        if e["EventID"] == 4720 and e["SubjectLogonId"] in attacker_logons
    ]
    return f"SOC{{{user}}}"


@solver("11-cron-persistence")
def s11(d: Path) -> str:
    for path in (d / "rootfs").rglob("*"):
        if not (path.is_file() and "cron" in str(path)):
            continue
        if m := re.search(r"echo ([A-Za-z0-9+/=]{20,}) \| base64 -d", path.read_text()):
            cmd = base64.b64decode(m.group(1)).decode()
            return "SOC{" + re.search(r"(\d+(?:\.\d+){3}:\d+)", cmd).group(1) + "}"
    raise AssertionError


@solver("12-macro-process-tree")
def s12(d: Path) -> str:
    procs = {p["ProcessId"]: p for p in jsonl(d / "sysmon_process_create.jsonl")}
    current = next(
        p
        for p in procs.values()
        if p["Image"].endswith("powershell.exe") and "iwr" in p["CommandLine"]
    )
    while not current["Image"].upper().endswith("WINWORD.EXE"):
        current = procs[current["ParentProcessId"]]
    doc = re.findall(r'"([^"]+)"', current["CommandLine"])[-1]
    return "SOC{" + doc.split("\\")[-1] + "}"


@solver("13-lateral-movement")
def s13(d: Path) -> str:
    ip_to_host = {r.split(",")[1]: r.split(",")[0] for r in lines(d / "activos.csv")[1:]}
    hops = [
        e for e in jsonl(d / "logons.jsonl")
        if e["user"] == "adm_backup" and ip_to_host.get(e["src_ip"]) != "BKP-01"
    ]  # fmt: skip
    hops.sort(key=lambda e: e["time"])
    path = [ip_to_host[hops[0]["src_ip"]]]
    for hop in hops:
        assert ip_to_host[hop["src_ip"]] == path[-1]
        path.append(hop["host"])
    return "SOC{" + ">".join(path) + "}"


@solver("14-offhours-exfiltration")
def s14(d: Path) -> str:
    internal = ipaddress.ip_network("10.0.0.0/8")
    totals: Counter[str] = Counter()
    for row in lines(d / "netflow.csv")[1:]:
        t, src, dst, _port, _proto, size = row.split(",")
        hour = ts(t).hour
        if (hour < 7 or hour >= 20) and ipaddress.ip_address(dst) not in internal:
            totals[src] += int(size)
    return f"SOC{{{totals.most_common(1)[0][0]}}}"


@solver("15-ransomware-pid-reuse")
def s15(d: Path) -> str:
    first = next(
        e for e in jsonl(d / "file_events.jsonl") if e.get("new_path", "").endswith(".locked")
    )
    alive = None
    for p in jsonl(d / "process_events.jsonl"):
        if p["pid"] != first["pid"] or p["time"] > first["time"]:
            continue
        alive = p if p["event"] == "start" else None
    return "SOC{" + alive["image"].split("\\")[-1] + "}"


@solver("16-xor-malware-config")
def s16(d: Path) -> str:
    blob = (d / "config.bin").read_bytes()
    for key in range(256):
        plain = bytes(b ^ key for b in blob)
        if plain.startswith(b"C2="):
            return "SOC{" + plain.split(b";")[0][3:].decode() + "}"
    raise AssertionError


def _b64url_json(part: str) -> dict:
    return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))


@solver("17-jwt-alg-none")
def s17(d: Path) -> str:
    subs = set()
    for line in lines(d / "api_access.log"):
        _t, _ip, _method, path, status, bearer = line.split()
        header, payload, _sig = bearer.removeprefix("bearer=").split(".")
        if (
            path == "/api/admin/export"
            and status == "200"
            and _b64url_json(header)["alg"].lower() == "none"
        ):
            subs.add(_b64url_json(payload)["sub"])
    (sub,) = subs
    return f"SOC{{{sub}}}"


@solver("18-pcap-http-exfil")
def s18(d: Path) -> str:
    raw = (d / "captura.pcap").read_bytes()
    offset, streams = 24, defaultdict(dict)
    while offset < len(raw):
        _s, _us, incl, _orig = struct.unpack_from("<IIII", raw, offset)
        frame = raw[offset + 16 : offset + 16 + incl]
        offset += 16 + incl
        ip = frame[14:]
        if ip[9] != 6:
            continue
        ihl = (ip[0] & 0x0F) * 4
        tcp = ip[ihl:]
        sport, dport, seq = struct.unpack_from("!HHI", tcp)
        payload = tcp[(tcp[12] >> 4) * 4 :]
        if dport == 80 and payload:
            streams[sport][seq] = payload
    for segments in streams.values():
        data = b"".join(segments[s] for s in sorted(segments))
        if data.startswith(b"POST"):
            _head, body = data.split(b"\r\n\r\n", 1)
            text = gzip.decompress(body).decode()
            return re.search(r"SOC\{[^}]+\}", text).group(0)
    raise AssertionError


@solver("19-multi-stage-incident")
def s19(d: Path) -> str:
    msg = email.message_from_string((d / "correo_factura.eml").read_text())
    hta = next(p for p in msg.walk() if p.get_filename()).get_payload(decode=True).decode()
    blob = re.search(r'var d = "([^"]+)"', hta).group(1)
    command = base64.b64decode(blob[::-1]).decode()
    url = re.search(r"(https?://\S+)", command).group(1)
    hit = next(x.split() for x in lines(d / "proxy.log") if f" {url} 200 " in x)
    when, ip = hit[0], hit[1]
    owner = None
    for line in lines(d / "dhcp.log"):
        t, kind, *fields = line.split()
        info = dict(f.split("=", 1) for f in fields)
        if info["ip"] == ip and t <= when:
            owner = info["hostname"] if kind == "DHCPACK" else None
    return f"SOC{{{owner}}}"


@solver("20-log-tampering")
def s20(d: Path) -> str:
    local = {" ".join(x.split()[2:]) for x in lines(d / "auth.log")}
    central = set()
    for line in lines(d / "syslog_central.log"):
        _pri, stamp, *rest = line.split()
        central.add(stamp[11:19] + " " + " ".join(rest))
    removed = central - local
    (m,) = [re.search(r"new user: name=(\w+), UID=(\d+)", x) for x in removed if "new user" in x]
    return f"SOC{{{m.group(1)}:{m.group(2)}}}"
