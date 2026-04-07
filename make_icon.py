"""Generates icon.png and icon.ico for BarcodOmatic."""
import os
from PIL import Image, ImageDraw


def _round_rect(draw, x1, y1, x2, y2, r, color):
    if y2 - y1 < 2 * r:
        r = max(1, (y2 - y1) // 2)
    if x2 - x1 < 2 * r:
        r = max(1, (x2 - x1) // 2)
    draw.rectangle([x1 + r, y1, x2 - r, y2], fill=color)
    draw.rectangle([x1, y1 + r, x2, y2 - r], fill=color)
    draw.ellipse([x1, y1, x1 + 2 * r, y1 + 2 * r], fill=color)
    draw.ellipse([x2 - 2 * r, y1, x2, y1 + 2 * r], fill=color)
    draw.ellipse([x1, y2 - 2 * r, x1 + 2 * r, y2], fill=color)
    draw.ellipse([x2 - 2 * r, y2 - 2 * r, x2, y2], fill=color)


def create_icon(size=256):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    s = size
    r = max(4, s // 9)

    # ── Background gradient (dark purple → dark navy) ──────────────────
    top_c = (26, 26, 46)
    bot_c = (15, 52, 96)
    for y in range(s):
        t = y / s
        rc = int(top_c[0] * (1 - t) + bot_c[0] * t)
        gc = int(top_c[1] * (1 - t) + bot_c[1] * t)
        bc = int(top_c[2] * (1 - t) + bot_c[2] * t)
        draw.line([(0, y), (s - 1, y)], fill=(rc, gc, bc, 255))

    # Convert to RGBA and apply rounded mask
    mask = Image.new("L", (s, s), 0)
    md = ImageDraw.Draw(mask)
    _round_rect(md, 0, 0, s - 1, s - 1, r, 255)
    img.putalpha(mask)

    draw = ImageDraw.Draw(img)

    # ── Orange top accent bar ───────────────────────────────────────────
    bar_h = max(6, s // 18)
    _round_rect(draw, 0, 0, s - 1, bar_h * 2, r, "#FF6B35")
    draw.rectangle([0, bar_h, s, bar_h * 2], fill="#FF6B35")

    # ── Green bottom accent bar ─────────────────────────────────────────
    _round_rect(draw, 0, s - bar_h * 2 - 1, s - 1, s - 1, r, "#00C853")
    draw.rectangle([0, s - bar_h * 2, s, s - bar_h], fill="#00C853")

    # ── Barcode bars ────────────────────────────────────────────────────
    by1 = bar_h * 2 + max(4, s // 32)
    by2 = s - bar_h * 2 - max(4, s // 32)

    if by1 < by2:
        bar_defs = [
            (0.072, 0.031, "#FFFFFF"),
            (0.117, 0.012, "#FF6B35"),
            (0.145, 0.024, "#FFFFFF"),
            (0.184, 0.039, "#FFFFFF"),
            (0.238, 0.016, "#FF6B35"),
            (0.269, 0.027, "#FFFFFF"),
            (0.313, 0.012, "#9C27B0"),
            (0.340, 0.035, "#FFFFFF"),
            (0.391, 0.020, "#FF6B35"),
            (0.426, 0.012, "#FFFFFF"),
            (0.453, 0.031, "#FFFFFF"),
            (0.500, 0.016, "#9C27B0"),
            (0.531, 0.043, "#FFFFFF"),
            (0.590, 0.012, "#FF6B35"),
            (0.617, 0.027, "#FFFFFF"),
            (0.660, 0.020, "#FFFFFF"),
            (0.695, 0.035, "#9C27B0"),
            (0.746, 0.016, "#FF6B35"),
            (0.778, 0.024, "#FFFFFF"),
            (0.816, 0.031, "#FFFFFF"),
            (0.863, 0.012, "#FF6B35"),
            (0.890, 0.035, "#FFFFFF"),
            (0.941, 0.020, "#FFFFFF"),
        ]
        for xf, wf, color in bar_defs:
            bx = int(xf * s)
            bw = max(1, int(wf * s))
            if bx + bw < s:
                draw.rectangle([bx, by1, bx + bw, by2], fill=color)

    return img


if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))

    icon_256 = create_icon(256)

    png_path = os.path.join(out_dir, "icon.png")
    icon_256.save(png_path)
    print(f"PNG saved: {png_path}")

    ico_path = os.path.join(out_dir, "icon.ico")
    icons = [create_icon(s) for s in (256, 128, 64, 48, 32, 16)]
    icons[0].save(
        ico_path,
        format="ICO",
        append_images=icons[1:],
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
    )
    print(f"ICO saved: {ico_path}")
