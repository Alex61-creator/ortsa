#!/usr/bin/env python3
"""Пересобрать static/images/og-default.png (1200×630). Требуется Pillow: pip install Pillow."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_OUT = _ROOT / "static" / "images" / "og-default.png"


def main() -> None:
    from PIL import Image, ImageDraw

    w, h = 1200, 630
    img = Image.new("RGB", (w, h), color="#0a1628")
    draw = ImageDraw.Draw(img)
    for i in range(w):
        r = int(10 + (26 - 10) * i / w)
        g = int(22 + (58 - 22) * i / w)
        b = int(40 + (92 - 40) * i / w)
        draw.line([(i, 0), (i, h)], fill=(r, g, b))
    draw.text((80, 220), "Astrogen", fill="#ffffff")
    draw.text((80, 320), "Natal chart online", fill="#a8c4e8")
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(_OUT, "PNG", optimize=True)
    print("Wrote", _OUT, _OUT.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
