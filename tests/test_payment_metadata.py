import pytest

from app.services.payment import (
    parse_order_id_from_metadata,
    parse_subscription_id_from_metadata,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("42", 42),
        (42, 42),
        (42.0, 42),
        (" 7 ", 7),
    ],
)
def test_parse_order_id_from_metadata_ok(raw, expected):
    assert parse_order_id_from_metadata(raw) == expected


def test_parse_order_id_from_metadata_rejects():
    assert parse_order_id_from_metadata(None) is None
    assert parse_order_id_from_metadata(True) is None
    assert parse_order_id_from_metadata(False) is None
    assert parse_order_id_from_metadata("not-int") is None
    assert parse_order_id_from_metadata([1]) is None
    assert parse_order_id_from_metadata({}) is None


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("5", 5),
        (99, 99),
    ],
)
def test_parse_subscription_id_from_metadata_ok(raw, expected):
    assert parse_subscription_id_from_metadata(raw) == expected


def test_parse_subscription_id_from_metadata_rejects():
    assert parse_subscription_id_from_metadata(None) is None
    assert parse_subscription_id_from_metadata(True) is None
    assert parse_subscription_id_from_metadata("x") is None
