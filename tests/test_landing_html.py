"""Тесты подстановки SEO в HTML."""

from types import SimpleNamespace

import pytest

from app.utils.landing_html import apply_seo_placeholders


@pytest.fixture
def fake_settings():
    return SimpleNamespace(
        site_base_url="https://example.com",
        GOOGLE_SITE_VERIFICATION="gverify123",
        YANDEX_VERIFICATION=None,
        BING_SITE_VERIFICATION=None,
    )


def test_apply_seo_replaces_site_base_url(fake_settings):
    html = '<link rel="canonical" href="__SITE_BASE_URL__/" />'
    out = apply_seo_placeholders(html, fake_settings)
    assert "__SITE_BASE_URL__" not in out
    assert 'href="https://example.com/"' in out


def test_apply_seo_inserts_google_verification_meta(fake_settings):
    html = "<head>__META_VERIFICATIONS__</head>"
    out = apply_seo_placeholders(html, fake_settings)
    assert 'name="google-site-verification"' in out
    assert "gverify123" in out
    assert "__META_VERIFICATIONS__" not in out


def test_apply_seo_escapes_verification_content():
    settings = SimpleNamespace(
        site_base_url="https://x.test",
        GOOGLE_SITE_VERIFICATION='x"y&',
        YANDEX_VERIFICATION=None,
        BING_SITE_VERIFICATION=None,
    )
    out = apply_seo_placeholders("__META_VERIFICATIONS__", settings)
    assert "google-site-verification" in out
    assert "&quot;" in out
    assert "&amp;" in out


def test_apply_seo_all_verifications():
    settings = SimpleNamespace(
        site_base_url="https://a.ru",
        GOOGLE_SITE_VERIFICATION="g",
        YANDEX_VERIFICATION="y",
        BING_SITE_VERIFICATION="b",
    )
    out = apply_seo_placeholders("__META_VERIFICATIONS__", settings)
    assert "google-site-verification" in out
    assert "yandex-verification" in out
    assert "msvalidate.01" in out
