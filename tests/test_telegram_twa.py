"""Проверка алгоритма initData по core.telegram.org/bots/webapps."""

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest
from fastapi import HTTPException

from app.services.auth_twa import TWAAuthService


def _make_valid_init_data(bot_token: str) -> str:
    user = {"id": 4242, "first_name": "Test", "is_bot": False}
    auth_date = str(int(time.time()))
    fields = {"user": json.dumps(user), "auth_date": auth_date, "query_id": "q1"}
    sorted_keys = sorted(fields.keys())
    data_check_string = "\n".join(f"{k}={fields[k]}" for k in sorted_keys)
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    data_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    params = {**fields, "hash": data_hash}
    return urlencode(params)


def test_twa_validate_init_data_ok():
    token = "123456:ABC-DEF"
    init_data = _make_valid_init_data(token)
    svc = TWAAuthService(token)
    user = svc.validate_init_data(init_data)
    assert user["id"] == 4242


def test_twa_validate_init_data_wrong_bot_token():
    token = "123456:ABC-DEF"
    init_data = _make_valid_init_data(token)
    svc = TWAAuthService("999999:WRONG")
    with pytest.raises(HTTPException) as exc:
        svc.validate_init_data(init_data)
    assert exc.value.status_code == 401
