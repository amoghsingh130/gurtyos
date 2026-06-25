"""Generate the App Home banner (assets/home-banner.png).

A 1200x300 title card on Slack aubergine (#4A154B): the gurtYos wordmark, a green
accent rule, and the tagline. Reproducible — re-run after tweaking copy/colors:

    python assets/make_banner.py
"""
from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 300
AUBERGINE = (74, 21, 75)        # #4A154B  Slack brand
AUBERGINE_LIGHT = (92, 42, 93)  # subtle depth circle
GREEN = (46, 182, 125)          # #2EB67D  accent
WHITE = (255, 255, 255)
MUTED = (216, 198, 218)         # tagline

TITLE_FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
BODY_FONT = "/System/Library/Fonts/Helvetica.ttc"

OUT = os.path.join(os.path.dirname(__file__), "home-banner.png")


def main() -> None:
    img = Image.new("RGB", (W, H), AUBERGINE)
    d = ImageDraw.Draw(img)

    # Subtle lighter circle bleeding off the right edge for depth.
    d.ellipse([W - 260, -120, W + 180, H + 120], fill=AUBERGINE_LIGHT)

    title = ImageFont.truetype(TITLE_FONT, 112)
    tag = ImageFont.truetype(BODY_FONT, 40)

    x = 90
    d.text((x, 70), "gurtYos", font=title, fill=WHITE)

    # Green accent rule under the wordmark.
    tw = d.textlength("gurtYos", font=title)
    d.rounded_rectangle([x + 2, 198, x + 2 + min(tw, 300), 206], radius=4, fill=GREEN)

    d.text((x + 2, 224), "Accessibility co-pilot for Slack", font=tag, fill=MUTED)

    img.save(OUT, "PNG")
    print("wrote", OUT, img.size)


if __name__ == "__main__":
    main()
