from decimal import Decimal

from app.constants.report_options import (
    build_report_options_prompt_addon,
    normalize_report_options,
    report_option_definitions,
)
from app.services.report_option_pricing import (
    compute_toggle_line,
    parse_percent_setting,
    parse_price_setting,
)


def test_normalize_drops_unknown_and_false():
    assert normalize_report_options(
        {"partnership": True, "bogus": True, "career": False}
    ) == {"partnership": True}


def test_compute_toggle_line_zero():
    assert compute_toggle_line(
        selected_keys=set(),
        price_by_key={"partnership": Decimal("199")},
        multi_discount_percent=Decimal(30),
    ) == Decimal("0.00")


def test_compute_toggle_line_one_no_multi():
    assert compute_toggle_line(
        selected_keys={"partnership"},
        price_by_key={"partnership": Decimal("199.00")},
        multi_discount_percent=Decimal(30),
    ) == Decimal("199.00")


def test_compute_toggle_line_two_with_multi():
    # 199 + 199 = 398, * 0.7 = 278.60
    prices = {k: Decimal("199.00") for k in ("partnership", "career")}
    assert compute_toggle_line(
        selected_keys={"partnership", "career"},
        price_by_key=prices,
        multi_discount_percent=Decimal(30),
    ) == Decimal("278.60")


def test_compute_toggle_line_four_with_multi():
    prices = {d.key: Decimal("199.00") for d in report_option_definitions()}
    assert compute_toggle_line(
        selected_keys=set(prices),
        price_by_key=prices,
        multi_discount_percent=Decimal(30),
    ) == Decimal("557.20")


def test_parse_percent_setting():
    assert parse_percent_setting(None, default=Decimal(30)) == Decimal(30)
    assert parse_percent_setting(" 15 ", default=Decimal(30)) == Decimal(15)
    assert parse_percent_setting("150", default=Decimal(30)) == Decimal(100)


def test_parse_price_setting():
    assert parse_price_setting("199.5", default=Decimal("199")) == Decimal("199.50")


def test_build_prompt_addon_empty():
    assert build_report_options_prompt_addon({}) == ""
    assert build_report_options_prompt_addon(None) == ""


def test_build_prompt_addon_contains_markers():
    text = build_report_options_prompt_addon({"partnership": True, "career": True})
    assert "## [ПАРТНЁРСТВО]" in text
    assert "## [КАРЬЕРА И РЕАЛИЗАЦИЯ]" in text
    assert "## [ДЕТИ" not in text
