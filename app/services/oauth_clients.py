"""OAuth2-клиенты, отсутствующие в httpx-oauth >= 0.14 (Яндекс, Apple)."""
from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import List, Optional, Tuple, cast

import httpx
from jose import jwt as jose_jwt
from httpx_oauth.exceptions import GetIdEmailError
from httpx_oauth.oauth2 import BaseOAuth2, GetAccessTokenError, OAuth2Token

from app.services.apple_id_token import verify_apple_identity_token

_YANDEX_AUTHORIZE = "https://oauth.yandex.ru/authorize"
_YANDEX_TOKEN = "https://oauth.yandex.ru/token"
_YANDEX_LOGIN_INFO = "https://login.yandex.ru/info"
_YANDEX_SCOPES = ["login:email", "login:info"]

_APPLE_AUTHORIZE = "https://appleid.apple.com/auth/authorize"
_APPLE_TOKEN = "https://appleid.apple.com/auth/token"
_APPLE_SCOPES = ["name", "email"]


class YandexOAuth2(BaseOAuth2[dict]):
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        scopes: Optional[List[str]] = None,
        name: str = "yandex",
    ):
        super().__init__(
            client_id,
            client_secret,
            _YANDEX_AUTHORIZE,
            _YANDEX_TOKEN,
            refresh_token_endpoint=_YANDEX_TOKEN,
            revoke_token_endpoint=None,
            name=name,
            base_scopes=scopes or _YANDEX_SCOPES,
        )

    async def get_id_email(self, token: str) -> Tuple[str, Optional[str]]:
        async with self.get_httpx_client() as client:
            response = await client.get(
                _YANDEX_LOGIN_INFO,
                headers={"Authorization": f"OAuth {token}"},
            )
            if response.status_code >= 400:
                raise GetIdEmailError(response=response)
            data = cast(dict, response.json())
        uid = str(data.get("id", ""))
        email = data.get("default_email") or data.get("login")
        if isinstance(email, str):
            return uid, email
        return uid, None


class AppleOAuth2(BaseOAuth2[dict]):
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        team_id: Optional[str],
        key_id: Optional[str],
        private_key_path: Optional[Path],
        scopes: Optional[List[str]] = None,
        name: str = "apple",
    ):
        self._team_id = team_id or ""
        self._key_id = key_id or ""
        self._key_path = private_key_path
        super().__init__(
            client_id,
            client_secret,
            _APPLE_AUTHORIZE,
            _APPLE_TOKEN,
            refresh_token_endpoint=_APPLE_TOKEN,
            revoke_token_endpoint=None,
            name=name,
            base_scopes=scopes or _APPLE_SCOPES,
        )

    def _make_client_secret(self) -> str:
        if not (self._team_id and self.client_id and self._key_id and self._key_path):
            raise ValueError(
                "Apple OAuth: задайте OAUTH_APPLE_TEAM_ID, OAUTH_APPLE_KEY_ID, "
                "OAUTH_APPLE_CLIENT_ID и OAUTH_APPLE_PRIVATE_KEY_PATH"
            )
        key = Path(self._key_path).expanduser().read_text(encoding="utf-8")
        now = int(time.time())
        headers = {"kid": self._key_id, "alg": "ES256"}
        payload = {
            "iss": self._team_id,
            "iat": now,
            "exp": now + 86400 * 150,
            "aud": "https://appleid.apple.com",
            "sub": self.client_id,
            "jti": str(uuid.uuid4()),
        }
        return jose_jwt.encode(payload, key, algorithm="ES256", headers=headers)

    async def get_access_token(
        self, code: str, redirect_uri: str, code_verifier: Optional[str] = None
    ) -> OAuth2Token:
        client_secret = self._make_client_secret()
        async with self.get_httpx_client() as client:
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": self.client_id,
                "client_secret": client_secret,
            }
            if code_verifier:
                data["code_verifier"] = code_verifier
            response = await client.post(
                _APPLE_TOKEN, data=data, headers=self.request_headers
            )
            if response.status_code >= 400:
                raise GetAccessTokenError(response.text, response=response)
            return OAuth2Token(cast(dict, response.json()))

    async def get_id_email(self, id_token: Optional[str]) -> Tuple[str, Optional[str]]:
        if not id_token:
            raise GetIdEmailError("Apple id_token отсутствует", response=None)
        try:
            claims = verify_apple_identity_token(id_token, self.client_id)
        except Exception as exc:
            raise GetIdEmailError("Невалидный Apple id_token", response=None) from exc
        return str(claims.get("sub", "")), claims.get("email")
