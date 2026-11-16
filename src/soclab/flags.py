"""Normalización, hash y verificación de flags.

Las flags nunca se guardan en claro: el manifiesto almacena un hash scrypt
con sal (``scrypt$n$r$p$salt_hex$hash_hex``). scrypt es lento a propósito para
que no sea trivial obtener la flag por fuerza bruta leyendo el manifiesto.
"""

import hashlib
import hmac
import re
import secrets
import unicodedata

FLAG_PATTERN = re.compile(r"^SOC\{[^\s{}]{1,200}\}$", re.IGNORECASE)
HASH_PATTERN = re.compile(r"^scrypt\$(\d+)\$(\d+)\$(\d+)\$([0-9a-f]{32})\$([0-9a-f]{64})$")
MAX_FLAG_LENGTH = 210

_N, _R, _P = 2**14, 8, 1
_MIN_N, _MAX_N, _MAX_R, _MAX_P = 2, 2**17, 16, 4


class FlagError(ValueError):
    """Flag o hash con formato inválido."""


def normalize(flag: str, *, case_sensitive: bool) -> str:
    value = unicodedata.normalize("NFC", flag.strip())
    return value if case_sensitive else value.lower()


def is_valid_format(flag: str) -> bool:
    value = flag.strip()
    return len(value) <= MAX_FLAG_LENGTH and FLAG_PATTERN.fullmatch(value) is not None


def _derive(value: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(
        value.encode(), salt=salt, n=n, r=r, p=p, maxmem=64 * 1024 * 1024, dklen=32
    )


def hash_flag(flag: str, *, case_sensitive: bool = False, salt: bytes | None = None) -> str:
    if not is_valid_format(flag):
        raise FlagError("La flag debe tener el formato SOC{...} sin espacios.")
    salt = salt if salt is not None else secrets.token_bytes(16)
    if len(salt) != 16:  # noqa: PLR2004
        raise FlagError("La sal debe tener 16 bytes.")
    digest = _derive(normalize(flag, case_sensitive=case_sensitive), salt, _N, _R, _P)
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${digest.hex()}"


def _parse_hash(flag_hash: str) -> tuple[int, int, int, bytes, bytes]:
    match = HASH_PATTERN.fullmatch(flag_hash)
    if match is None:
        raise FlagError("Hash de flag inválido.")
    n, r, p = (int(match.group(i)) for i in (1, 2, 3))
    # Límites para evitar que un manifiesto malicioso agote memoria/CPU.
    if not (_MIN_N <= n <= _MAX_N and (n & (n - 1)) == 0 and 1 <= r <= _MAX_R and 1 <= p <= _MAX_P):
        raise FlagError("Parámetros scrypt fuera de rango.")
    return n, r, p, bytes.fromhex(match.group(4)), bytes.fromhex(match.group(5))


def is_valid_hash(flag_hash: str) -> bool:
    try:
        _parse_hash(flag_hash)
    except FlagError:
        return False
    return True


def verify(flag: str, flag_hash: str, *, case_sensitive: bool = False) -> bool:
    """Compara en tiempo constante la flag enviada con el hash almacenado."""
    n, r, p, salt, expected = _parse_hash(flag_hash)
    if not is_valid_format(flag):
        return False
    actual = _derive(normalize(flag, case_sensitive=case_sensitive), salt, n, r, p)
    return hmac.compare_digest(actual, expected)
