"""Верификация Apple identity token (id_token) по JWKS Apple."""

from __future__ import annotations

import jwt
from jwt import PyJWKClient

APPLE_ISSUER = "https://appleid.apple.com"
APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"

_jwks_client: PyJWKClient | None = None


def _jwks() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(APPLE_JWKS_URL)
    return _jwks_client


def verify_apple_identity_token(id_token: str, client_id: str) -> dict:
    """
    Проверяет подпись RS256, iss, aud, exp.
    Возвращает payload (claims), включая sub и опционально email.
    """
    signing_key = _jwks().get_signing_key_from_jwt(id_token)
    return jwt.decode(
        id_token,
        signing_key.key,
        algorithms=["RS256"],
        audience=client_id,
        issuer=APPLE_ISSUER,
    )
