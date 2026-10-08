"""High-fidelity extraction and rendering of the JR Spider Emblem.

Extracts the futuristic JR Spider Emblem from 'logo set 2 Futuristic JR Spider Emblem Showcase.png',
cleans the background to full transparency with smooth anti-aliased alpha borders,
and renders all icon sizes for Web HUD, Mobile PWA, Android APK mipmaps, and Windows EXE.
"""

from __future__ import annotations

import collections
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
SOURCE_IMAGE = BASE_DIR / "logo set 2 Futuristic JR Spider Emblem Showcase.png"
MOBILE_ASSETS = BASE_DIR / "edith" / "ui" / "public" / "mobile" / "assets"
WEB_PUBLIC = BASE_DIR / "edith" / "ui" / "public"


def extract_master_emblem() -> Image.Image:
    """Extract clean transparent RGBA master emblem from source showcase image."""
    if not SOURCE_IMAGE.exists():
        raise FileNotFoundError(f"Source emblem image not found at: {SOURCE_IMAGE}")

    im = Image.open(SOURCE_IMAGE).convert("RGBA")
    # Top emblem bounding box
    xmin, ymin, xmax, ymax = 282, 30, 966, 754
    margin = 20
    crop = im.crop((xmin - margin, ymin - margin, xmax + margin, ymax + margin))
    w, h = crop.size
    arr = np.array(crop).astype(np.float32)

    rgb = arr[:, :, :3]
    max_c = np.max(rgb, axis=2)

    # Any pixel with brightness <= 12 is dark background
    # Smooth transition between 12 and 22 for anti-aliased edge
    alpha = np.clip((max_c - 12.0) / 10.0, 0.0, 1.0) * 255.0

    out_arr = np.zeros((h, w, 4), dtype=np.uint8)
    out_arr[:, :, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    out_arr[:, :, 3] = alpha.astype(np.uint8)

    emblem_im = Image.fromarray(out_arr, "RGBA")

    # Crop tightly to non-zero alpha
    bbox = emblem_im.getbbox()
    if bbox:
        emblem_im = emblem_im.crop(bbox)

    # Pad to square with balanced margin
    ew, eh = emblem_im.size
    sq_size = max(ew, eh) + 24
    sq_im = Image.new("RGBA", (sq_size, sq_size), (0, 0, 0, 0))
    sq_im.paste(emblem_im, ((sq_size - ew) // 2, (sq_size - eh) // 2), emblem_im)

    return sq_im


_CACHED_MASTER: Optional[Image.Image] = None

def get_master_emblem() -> Image.Image:
    global _CACHED_MASTER
    if _CACHED_MASTER is None:
        _CACHED_MASTER = extract_master_emblem()
    return _CACHED_MASTER


def make_launcher_icon(size: int) -> Image.Image:
    """Render circular HUD icon with subtle cyber-ring backdrop and master JR emblem."""
    master = get_master_emblem()
    scale = 2
    cs = size * scale
    im = Image.new("RGBA", (cs, cs), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    center = cs / 2.0
    r = cs / 2.0 - 4 * scale

    # Dark cyber metallic disc
    for step in range(int(r), 0, -1):
        ratio = step / r
        r_c = int(6 + 10 * ratio)
        g_c = int(10 + 14 * ratio)
        b_c = int(22 + 28 * ratio)
        d.ellipse(
            (center - step, center - step, center + step, center + step),
            fill=(r_c, g_c, b_c, 255),
        )

    # Tactical rings
    d.ellipse(
        (center - r, center - r, center + r, center + r),
        outline=(0, 229, 255, 180),
        width=max(1, int(1.5 * scale)),
    )
    inner_r = r * 0.92
    d.ellipse(
        (center - inner_r, center - inner_r, center + inner_r, center + inner_r),
        outline=(255, 23, 68, 140),
        width=max(1, int(1 * scale)),
    )

    # Paste spider emblem
    emb_target = int(inner_r * 1.6)
    scaled_emb = master.resize((emb_target, emb_target), Image.Resampling.LANCZOS)
    ox = int(center - emb_target / 2.0)
    oy = int(center - emb_target / 2.0)
    im.paste(scaled_emb, (ox, oy), scaled_emb)

    return im.resize((size, size), Image.Resampling.LANCZOS)


def draw_spiderman_icon(size: int) -> Image.Image:
    """Compatibility alias for Android APK builder."""
    return make_launcher_icon(size)


def render_all_icons() -> None:
    """Generate all application icons across web, mobile, and desktop formats."""
    master = get_master_emblem()
    MOBILE_ASSETS.mkdir(parents=True, exist_ok=True)
    WEB_PUBLIC.mkdir(parents=True, exist_ok=True)

    # 1. Master PNG and center core asset
    master_path = MOBILE_ASSETS / "spiderman_logo.png"
    master.save(master_path, format="PNG")
    print(f"Saved master emblem: {master_path} ({master.size})")

    # 3. Mobile PWA Icons
    icon_512 = make_launcher_icon(512)
    icon_512.save(MOBILE_ASSETS / "icon-512.png", format="PNG")

    icon_192 = make_launcher_icon(192)
    icon_192.save(MOBILE_ASSETS / "icon-192.png", format="PNG")

    icon_64 = make_launcher_icon(64)
    icon_64.save(MOBILE_ASSETS / "favicon.png", format="PNG")

    # 4. Multi-size Windows & Browser Favicon (.ico)
    ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    ico_images = [make_launcher_icon(s[0]) for s in ico_sizes]

    # Save to mobile and web public
    master_ico_path = WEB_PUBLIC / "favicon.ico"
    ico_images[-1].save(
        master_ico_path,
        format="ICO",
        sizes=ico_sizes,
        append_images=ico_images[:-1],
    )
    ico_images[-1].save(
        MOBILE_ASSETS / "favicon.ico",
        format="ICO",
        sizes=ico_sizes,
        append_images=ico_images[:-1],
    )
    print(f"Saved multi-resolution Windows/Web favicon: {master_ico_path}")


if __name__ == "__main__":
    render_all_icons()
