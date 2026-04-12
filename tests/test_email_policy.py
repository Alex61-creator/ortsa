import pytest

from app.utils.email_policy import (
    is_placeholder_account_email,
    resolve_receipt_and_report_email,
)


@pytest.mark.parametrize(
    "email,expected",
    [
        (None, True),
        ("", True),
        ("tg_1@telegram.local", True),
        ("x@oauth.google.local", True),
        ("id@oauth.apple.local", True),
        ("id@oauth.yandex.local", True),
        ("real@example.com", False),
    ],
)
def test_placeholder_detection(email, expected):
    assert is_placeholder_account_email(email) == expected


def test_resolve_receipt_prioritizes_delivery():
    assert (
        resolve_receipt_and_report_email("tg_1@telegram.local", "pay@mail.com")
        == "pay@mail.com"
    )


def test_resolve_receipt_falls_back_to_real_user_email():
    assert (
        resolve_receipt_and_report_email("user@example.com", None) == "user@example.com"
    )


def test_resolve_none_when_placeholder_and_no_delivery():
    assert resolve_receipt_and_report_email("tg_1@telegram.local", None) is None
