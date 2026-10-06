"""Render high-resolution Spider-Man app icons for Mobile PWA."""

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

def draw_spiderman_icon(size: int) -> Image.Image:
    # 4x supersampling for ultra crisp anti-aliasing
    scale = 4
    canvas_size = size * scale
    im = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    center = canvas_size / 2.0
    radius = (canvas_size / 2.0) - (8 * scale)

    # 1. Dark metallic Stark HUD background circle
    for r in range(int(radius), 0, -1):
        ratio = r / radius
        r_col = int(8 + 12 * ratio)
        g_col = int(12 + 16 * ratio)
        b_col = int(24 + 32 * ratio)
        d.ellipse(
            (center - r, center - r, center + r, center + r),
            fill=(r_col, g_col, b_col, 255)
        )

    # 2. Outer HUD Tech Rings
    d.ellipse(
        (center - radius, center - radius, center + radius, center + radius),
        outline=(25, 45, 80, 255),
        width=max(1, int(3 * scale))
    )
    cyan_r = radius * 0.94
    d.ellipse(
        (center - cyan_r, center - cyan_r, center + cyan_r, center + cyan_r),
        outline=(0, 229, 255, 220),
        width=max(1, int(2 * scale))
    )
    red_r = radius * 0.88
    d.ellipse(
        (center - red_r, center - red_r, center + red_r, center + red_r),
        outline=(255, 23, 68, 160),
        width=max(1, int(1.5 * scale))
    )

    # 3. Spider-Web Radar Lines in the background
    web_color = (0, 229, 255, 45)
    for angle_deg in range(0, 360, 30):
        rad = math.radians(angle_deg)
        x2 = center + math.cos(rad) * red_r
        y2 = center + math.sin(rad) * red_r
        d.line((center, center, x2, y2), fill=web_color, width=int(1 * scale))

    for ring_f in [0.25, 0.5, 0.75]:
        wr = red_r * ring_f
        d.ellipse(
            (center - wr, center - wr, center + wr, center + wr),
            outline=web_color,
            width=int(1 * scale)
        )

    # 4. Spider-Man Insignia Emblem (Scaled to 512 base)
    def s(coord):
        return (coord / 512.0) * canvas_size

    # Color palette
    red_fill = (255, 23, 68, 255)
    red_glow = (255, 61, 90, 255)
    cyan_accent = (0, 229, 255, 255)

    # Head and Fangs
    head_pts = [(s(256), s(155)), (s(268), s(185)), (s(260), s(205)), (s(252), s(205)), (s(244), s(185))]
    d.polygon(head_pts, fill=red_fill)
    fang_pts = [(s(252), s(150)), (s(256), s(136)), (s(260), s(150)), (s(256), s(156))]
    d.polygon(fang_pts, fill=(255, 255, 255, 255))

    # Thorax and Abdomen
    body_pts = [(s(256), s(205)), (s(274), s(235)), (s(266), s(285)), (s(256), s(338)), (s(246), s(285)), (s(238), s(235))]
    d.polygon(body_pts, fill=red_fill)

    # Legs (upper and lower pairs)
    legs_left = [
        [(s(248), s(212)), (s(200), s(165)), (s(145), s(130)), (s(140), s(126)), (s(150), s(118)), (s(195), s(145)), (s(245), s(200))],
        [(s(244), s(226)), (s(180), s(200)), (s(115), s(195)), (s(108), s(195)), (s(112), s(185)), (s(175), s(188)), (s(242), s(216))],
        [(s(245), s(248)), (s(170), s(270)), (s(120), s(330)), (s(115), s(336)), (s(122), s(342)), (s(170), s(290)), (s(244), s(258))],
        [(s(248), s(270)), (s(185), s(320)), (s(150), s(405)), (s(145), s(416)), (s(155), s(420)), (s(190), s(345)), (s(250), s(285))]
    ]
    for leg in legs_left:
        d.polygon(leg, fill=red_fill)

    legs_right = [
        [(s(264), s(212)), (s(312), s(165)), (s(367), s(130)), (s(372), s(126)), (s(362), s(118)), (s(317), s(145)), (s(267), s(200))],
        [(s(268), s(226)), (s(332), s(200)), (s(397), s(195)), (s(404), s(195)), (s(400), s(185)), (s(337), s(188)), (s(270), s(216))],
        [(s(267), s(248)), (s(342), s(270)), (s(392), s(330)), (s(397), s(336)), (s(390), s(342)), (s(342), s(290)), (s(268), s(258))],
        [(s(264), s(270)), (s(327), s(320)), (s(362), s(405)), (s(367), s(416)), (s(357), s(420)), (s(322), s(345)), (s(262), s(285))]
    ]
    for leg in legs_right:
        d.polygon(leg, fill=red_fill)

    # Center glowing audio wave line
    d.line([(s(210), s(256)), (s(302), s(256))], fill=cyan_accent, width=int(2 * scale))
    d.ellipse([(s(252), s(252)), (s(260), s(260))], fill=(255, 255, 255, 255))

    # Downsample using LANCZOS for high quality anti-aliasing
    final_im = im.resize((size, size), Image.Resampling.LANCZOS)
    return final_im


if __name__ == "__main__":
    assets_dir = Path("edith/ui/public/mobile/assets")
    assets_dir.mkdir(parents=True, exist_ok=True)

    img_512 = draw_spiderman_icon(512)
    img_512.save(assets_dir / "icon-512.png", "PNG")

    img_192 = draw_spiderman_icon(192)
    img_192.save(assets_dir / "icon-192.png", "PNG")

    img_fav = draw_spiderman_icon(64)
    img_fav.save(assets_dir / "favicon.ico", "ICO")
    img_fav.save(assets_dir / "favicon.png", "PNG")

    # Also copy to root public for easy favicon reference
    img_fav.save(Path("edith/ui/public/favicon.ico"), "ICO")

    print("Icons rendered successfully!")
