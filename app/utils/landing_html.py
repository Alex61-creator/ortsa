"""Подстановка SEO-плейсхолдеров в статический HTML лендинга."""

from html import escape

from app.core.config import Settings


def apply_seo_placeholders(html: str, settings: Settings) -> str:
    base = settings.site_base_url
    html = html.replace("__SITE_BASE_URL__", base)

    meta_lines: list[str] = []
    if settings.GOOGLE_SITE_VERIFICATION:
        meta_lines.append(
            f'<meta name="google-site-verification" content="{escape(settings.GOOGLE_SITE_VERIFICATION, quote=True)}" />'
        )
    if settings.YANDEX_VERIFICATION:
        meta_lines.append(
            f'<meta name="yandex-verification" content="{escape(settings.YANDEX_VERIFICATION, quote=True)}" />'
        )
    if settings.BING_SITE_VERIFICATION:
        meta_lines.append(
            f'<meta name="msvalidate.01" content="{escape(settings.BING_SITE_VERIFICATION, quote=True)}" />'
        )
    html = html.replace("__META_VERIFICATIONS__", "\n".join(meta_lines))
    return html
