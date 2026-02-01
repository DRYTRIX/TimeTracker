#!/usr/bin/env python3
"""
Generate mobile app icon (app_icon.png) matching the web app's timetracker-logo-icon.svg.
Creates a 1024x1024 PNG: gradient rounded rect, white clock circle, hour marks, checkmark.
Requires: pip install Pillow
"""
import os
import sys

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    out_dir = os.path.join(project_root, "mobile", "assets", "icon")
    out_path = os.path.join(out_dir, "app_icon.png")

    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("Pillow not installed. Run: pip install Pillow")
        print("Or use ImageMagick: magick app/static/images/timetracker-logo-icon.svg -resize 1024x1024 mobile/assets/icon/app_icon.png")
        return 1

    os.makedirs(out_dir, exist_ok=True)

    # Match SVG: 512 viewBox scaled to 1024 (scale 2)
    size = 1024
    r_rect = 256   # 128 * 2
    cx, cy = size // 2, size // 2
    r_clock = 360  # 180 * 2
    stroke_circle = 64   # 32 * 2
    stroke_mark = 48     # 24 * 2
    stroke_check = 80    # 40 * 2

    # 1) Gradient image (linear top-left #4A90E2 to bottom-right #50E3C2)
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

    # 2) Rounded rect mask
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=r_rect, fill=255)

    # 3) Base image: gradient only inside rounded rect
    base = Image.new("RGB", (size, size), (0x4A, 0x90, 0xE2))
    base.paste(grad, (0, 0), mask)
    draw = ImageDraw.Draw(base)

    # 4) White circle (stroke only): outer circle white, inner circle = mid gradient
    draw.ellipse([cx - r_clock, cy - r_clock, cx + r_clock, cy + r_clock], fill="white", outline=None)
    inner_r = r_clock - stroke_circle
    mid = ((0x4A + 0x50) // 2, (0x90 + 0xE3) // 2, (0xE2 + 0xC2) // 2)
    draw.ellipse([cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r], fill=mid, outline=None)

    # 5) Hour marks (4 white lines) - SVG positions scaled *2
    draw.line([(cx, cy - r_clock), (cx, cy - r_clock + stroke_mark)], fill="white", width=stroke_mark)
    draw.line([(cx, cy + r_clock - stroke_mark), (cx, cy + r_clock)], fill="white", width=stroke_mark)
    draw.line([(cx - r_clock, cy), (cx - r_clock + stroke_mark, cy)], fill="white", width=stroke_mark)
    draw.line([(cx + r_clock - stroke_mark, cy), (cx + r_clock, cy)], fill="white", width=stroke_mark)

    # 6) Checkmark: M 195 270 L 255 330 L 365 220, stroke 40, round. Scale *2
    draw.line([(390, 540), (510, 660), (730, 440)], fill="white", width=stroke_check, joint="curve")

    base.save(out_path)
    print(f"Created {out_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
