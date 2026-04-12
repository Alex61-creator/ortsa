def test_public_app_base_url_prefers_public_app_url(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "PUBLIC_APP_URL", "https://spa.example/")
    assert config.settings.public_app_base_url == "https://spa.example"


def test_public_app_base_url_falls_back_to_yookassa_return(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "PUBLIC_APP_URL", None)
    monkeypatch.setattr(
        config.settings, "YOOKASSA_RETURN_URL", "https://legacy.example/success/"
    )
    assert config.settings.public_app_base_url == "https://legacy.example/success"


def test_site_base_url_prefers_site_url(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "SITE_URL", "https://canonical.example/")
    monkeypatch.setattr(config.settings, "PUBLIC_APP_URL", "https://spa.example/")
    assert config.settings.site_base_url == "https://canonical.example"
