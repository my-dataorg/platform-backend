"""RSA key pair + JWKS for platform-issued JWTs."""

from __future__ import annotations

import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwk

KEYS_DIR = Path(__file__).resolve().parents[2] / ".keys"
PRIVATE_PATH = KEYS_DIR / "jwt_private.pem"
PUBLIC_PATH = KEYS_DIR / "jwt_public.pem"
KID = "platform-1"

_private_pem: bytes | None = None
_public_pem: bytes | None = None


def ensure_keys() -> None:
    global _private_pem, _public_pem
    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    if not PRIVATE_PATH.exists() or not PUBLIC_PATH.exists():
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private_pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_pem = key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        PRIVATE_PATH.write_bytes(private_pem)
        PUBLIC_PATH.write_bytes(public_pem)
    _private_pem = PRIVATE_PATH.read_bytes()
    _public_pem = PUBLIC_PATH.read_bytes()


def private_pem() -> bytes:
    if _private_pem is None:
        ensure_keys()
    assert _private_pem is not None
    return _private_pem


def public_pem() -> bytes:
    if _public_pem is None:
        ensure_keys()
    assert _public_pem is not None
    return _public_pem


def jwks() -> dict:
    key = jwk.construct(public_pem(), algorithm="RS256")
    data = key.to_dict()
    if isinstance(data, str):
        data = json.loads(data)
    data["kid"] = KID
    data["use"] = "sig"
    data["alg"] = "RS256"
    return {"keys": [data]}
