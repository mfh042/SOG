"""JWT + 密码哈希（纯标准库实现，无第三方依赖）。"""
import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone


_PBKDF2_ITERATIONS = 120_000
_PBKDF2_ALGO = "sha256"
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    """PBKDF2-HMAC-SHA256 密码哈希，格式：pbkdf2$iterations$salt_hex$hash_hex"""
    salt = os.urandom(_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(_PBKDF2_ALGO, password.encode(), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2${_PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt_hex, hash_hex = stored.split("$")
        iters_int = int(iters)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        dk = hashlib.pbkdf2_hmac(_PBKDF2_ALGO, password.encode(), salt, iters_int)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + padding)


def create_access_token(
    *,
    sub: str,
    role: str,
    secret: str,
    algorithm: str = "HS256",
    expire_minutes: int = 120,
) -> str:
    now = datetime.now(timezone.utc)
    header = {"alg": algorithm, "typ": "JWT"}
    payload = {
        "sub": sub,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expire_minutes)).timestamp()),
    }
    h = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{h}.{p}".encode()
    sig = hmac.new(secret.encode(), signing_input, hashlib.sha256 if algorithm == "HS256" else hashlib.sha512).digest()
    return f"{h}.{p}.{_b64url_encode(sig)}"


def decode_access_token(token: str, secret: str, algorithm: str = "HS256") -> dict | None:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        h_b64, p_b64, s_b64 = parts
        signing_input = f"{h_b64}.{p_b64}".encode()
        expected_sig = hmac.new(secret.encode(), signing_input, hashlib.sha256 if algorithm == "HS256" else hashlib.sha512).digest()
        actual_sig = _b64url_decode(s_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        header = json.loads(_b64url_decode(h_b64))
        if header.get("alg") != algorithm:
            return None
        payload = json.loads(_b64url_decode(p_b64))
        exp = payload.get("exp")
        if exp and datetime.now(timezone.utc).timestamp() > exp:
            return None
        return payload
    except Exception:
        return None