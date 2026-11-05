#!/usr/bin/env python3
"""Generate android-chrome-192x192.png and android-chrome-512x512.png for PWA (matches timetracker icon style)."""

import os
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Pillow required: pip install Pillow", file=sys.stderr)
    sys.exit(1)


def build_icon(size: int) -> Image.Image:
    """Raster icon matching scripts/generate-mobile-icon.py style, scaled to size."""
    scale = size / 1024.0
    r_rect = int(round(256 * scale))
    cx, cy = size // 2, size // 2
    r_clock = int(round(360 * scale))
    stroke_circle = int(round(64 * scale))
    stroke_mark = int(round(48 * scale))
    stroke_check = int(round(80 * scale))

    grad = Image.new("RGB", (size, size), (0, 0, 0))
    px = grad.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * size)
            t = max(0, min(1, t))
            r = int(0x4A + (0x50 - 0x4A) * t)
            g = int(0x90 + (0xE3 - 0x90) * t)
            b = int(0xE2 + (0xC2 - 0xE2) * t)
            px[x, y] = (r, g, b)

    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=r_rect, fill=255)

    base = Image.new("RGB", (size, size), (0x4A, 0x90, 0xE2))
    base.paste(grad, (0, 0), mask)
    draw = ImageDraw.Draw(base)

    draw.ellipse([cx - r_clock, cy - r_clock, cx + r_clock, cy + r_clock], fill="white", outline=None)
    inner_r = r_clock - stroke_circle
    mid = ((0x4A + 0x50) // 2, (0x90 + 0xE3) // 2, (0xE2 + 0xC2) // 2)
    draw.ellipse([cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r], fill=mid, outline=None)

    draw.line([(cx, cy - r_clock), (cx, cy - r_clock + stroke_mark)], fill="white", width=max(1, stroke_mark))
    draw.line([(cx, cy + r_clock - stroke_mark), (cx, cy + r_clock)], fill="white", width=max(1, stroke_mark))
    draw.line([(cx - r_clock, cy), (cx - r_clock + stroke_mark, cy)], fill="white", width=max(1, stroke_mark))
    draw.line([(cx + r_clock - stroke_mark, cy), (cx + r_clock, cy)], fill="white", width=max(1, stroke_mark))

    draw.line(
        [
            (int(390 * scale), int(540 * scale)),
            (int(510 * scale), int(660 * scale)),
            (int(730 * scale), int(440 * scale)),
        ],
        fill="white",
        width=max(1, stroke_check),
        joint="curve",
    )
    return base


def main() -> int:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    out_dir = os.path.join(project_root, "app", "static", "images")
    os.makedirs(out_dir, exist_ok=True)
    for name, dim in (("android-chrome-192x192.png", 192), ("android-chrome-512x512.png", 512)):
        path = os.path.join(out_dir, name)
        build_icon(dim).save(path, "PNG")
        print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
