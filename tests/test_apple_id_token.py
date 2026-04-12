import pytest

from app.services.apple_id_token import verify_apple_identity_token


def test_apple_verify_rejects_garbage_token():
    with pytest.raises(Exception):
        verify_apple_identity_token("not-a-valid-jwt", "any.client.id")
