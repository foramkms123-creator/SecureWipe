"""Password hashing with scrypt (Python standard library, memory-hard, salted)."""
import base64
import hashlib
import hmac
import os

_N, _R, _P, _DKLEN = 2 ** 14, 8, 1, 32
_MAXMEM = 64 * 1024 * 1024


def _derive(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p,
                          dklen=_DKLEN, maxmem=_MAXMEM)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    key = _derive(password, salt, _N, _R, _P)
    return "scrypt${}${}${}${}${}".format(
        _N, _R, _P, base64.b64encode(salt).decode(), base64.b64encode(key).decode())


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt_b64, key_b64 = stored.split("$")
        if algo != "scrypt":
            return False
        key = _derive(password, base64.b64decode(salt_b64), int(n), int(r), int(p))
        return hmac.compare_digest(key, base64.b64decode(key_b64))
    except (ValueError, TypeError):
        return False


# Used to keep login timing identical for unknown usernames.
DUMMY_HASH = hash_password("timing-equaliser")
