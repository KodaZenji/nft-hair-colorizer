# generate_hair_colors_example.py
#
# EXAMPLE SCRIPT — replace placeholder values with your own collection's traits.
# See HAIR_COLORIZER_PROMPT.md for full setup instructions.
#
# Requires:
#   pip install Pillow numpy

from PIL import Image
import numpy as np
import os

INPUT_DIR = "Hairstyles"          # ← folder containing your grayscale PNGs
OUTPUT_DIR = "Hairstyles_Colored" # ← output folder (auto-created)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── HAIR COLOR PALETTES ───────────────────────────────────────────────────────
# Each palette needs: base, shadow, highlight as (R, G, B) tuples.
# base      → mid-tone color
# shadow    → dark areas / depth
# highlight → bright areas / sheen
#
# Replace or extend these with your own palette set.
HAIR_PALETTES = {
    "Black":       {"base": (25, 20, 18),    "shadow": (10, 8, 7),      "highlight": (60, 55, 50)},
    "Brown":       {"base": (110, 75, 45),   "shadow": (60, 40, 25),    "highlight": (160, 120, 80)},
    "Blonde":      {"base": (220, 190, 130), "shadow": (160, 120, 70),  "highlight": (255, 235, 180)},
    "Red":         {"base": (170, 60, 40),   "shadow": (100, 30, 20),   "highlight": (220, 100, 70)},
    "GraySilver":  {"base": (190, 195, 205), "shadow": (120, 125, 135), "highlight": (240, 245, 255)},
    "FantasyBlue": {"base": (100, 140, 230), "shadow": (60, 90, 160),   "highlight": (170, 200, 255)},
}

# ── RARITY WEIGHTS ────────────────────────────────────────────────────────────
# Keys must match HAIR_PALETTES exactly.
# Values are integers — used in the output filename as #{weight}.
# Should sum to 100 for clean percentage-based rarity.
WEIGHTS = {
    "Black":       40,
    "Brown":       30,
    "Blonde":      15,
    "Red":          8,
    "GraySilver":   5,
    "FantasyBlue":  2,
}

# ── HAIRSTYLE LISTS ───────────────────────────────────────────────────────────
# COLORABLE: sprite base names (no .png) that will be recolored across all palettes.
# Replace these with your actual sprite filenames.
COLORABLE = [
    "example_style_a",   # ← replace with your sprite name
    "example_style_b",
    "example_style_c",
]

# NO_COLOR: sprites with no hair to recolor (bald, shaved, etc.).
# These are copied as-is with a weight of 100.
NO_COLOR = [
    "example_bald",      # ← replace with your sprite name
]

# ── ACCESSORY RULES ───────────────────────────────────────────────────────────
# If a sprite has colored accessories (beads, clips, dyed tips), protect those
# pixels from recoloring by defining hue+saturation rules here.
#
# Hue reference: Red=0, Orange=30, Yellow=60, Green=120, Cyan=180, Blue=240, Purple=280
#
# Example: a style with red and blue decorative beads:
#   "example_style_with_beads": [
#       {"hue": 0,   "hue_range": 20, "min_sat": 0.35},   # reds
#       {"hue": 240, "hue_range": 30, "min_sat": 0.30},   # blues
#   ],
ACCESSORY_RULES = {
    # "example_style_a": [
    #     {"hue": 120, "hue_range": 25, "min_sat": 0.30},  # greens
    # ],
}


# ═══════════════════════════════════════════════════════════════════════════════
#  ENGINE — no need to edit below this line
# ═══════════════════════════════════════════════════════════════════════════════

def get_saturation_map(arr):
    r = arr[:, :, 0].astype(np.float32) / 255.0
    g = arr[:, :, 1].astype(np.float32) / 255.0
    b = arr[:, :, 2].astype(np.float32) / 255.0
    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    delta = cmax - cmin
    return np.where(cmax > 0, delta / cmax, 0.0)


def get_hue_map(arr):
    r = arr[:, :, 0].astype(np.float32) / 255.0
    g = arr[:, :, 1].astype(np.float32) / 255.0
    b = arr[:, :, 2].astype(np.float32) / 255.0
    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    delta = cmax - cmin
    hue = np.zeros_like(r)
    mask = (cmax == r) & (delta > 0)
    hue[mask] = (60 * ((g[mask] - b[mask]) / delta[mask])) % 360
    mask = (cmax == g) & (delta > 0)
    hue[mask] = 60 * ((b[mask] - r[mask]) / delta[mask]) + 120
    mask = (cmax == b) & (delta > 0)
    hue[mask] = 60 * ((r[mask] - g[mask]) / delta[mask]) + 240
    return hue % 360


def build_accessory_mask(arr, rules=[], grey_ranges=[]):
    """
    Returns a boolean mask (H x W) where True = protected from recoloring.

    rules       — list of hue-based rules for colored accessories.
    grey_ranges — list of (min_brightness, max_brightness) tuples for
                  grey/neutral accessories (low saturation, specific brightness).
                  Example: [(80, 200)] protects mid-grey pixels.
    """
    mask_total = np.zeros(arr.shape[:2], dtype=bool)

    if rules:
        sat = get_saturation_map(arr)
        hue = get_hue_map(arr)
        for rule in rules:
            h, hr, ms = rule["hue"], rule["hue_range"], rule["min_sat"]
            low, high = (h - hr) % 360, (h + hr) % 360
            if low < high:
                hue_mask = (hue >= low) & (hue <= high)
            else:
                hue_mask = (hue >= low) | (hue <= high)
            mask_total |= (hue_mask & (sat >= ms))

    if grey_ranges:
        sat = get_saturation_map(arr)
        brightness = (arr[:, :, 0].astype(np.float32) +
                      arr[:, :, 1].astype(np.float32) +
                      arr[:, :, 2].astype(np.float32)) / 3.0
        for (lo, hi) in grey_ranges:
            mask_total |= (brightness >= lo) & (brightness <= hi) & (sat < 0.15)

    return mask_total


def enhance_grayscale(arr):
    """Boost contrast on grayscale input before colorizing."""
    rgb = arr[:, :, :3].astype(np.float32)
    brightness = (rgb[:, :, 0] + rgb[:, :, 1] + rgb[:, :, 2]) / 3.0
    norm = brightness / 255.0
    enhanced = np.where(
        norm < 0.5,
        np.power(norm, 1.3),
        1 - np.power(1 - norm, 1.2)
    )
    mid_boost = 1 + 0.2 * np.exp(-((norm - 0.5) ** 2) / 0.02)
    enhanced = np.clip(enhanced * mid_boost, 0, 1) * 255.0
    result = arr.copy().astype(np.float32)
    result[:, :, 0] = enhanced
    result[:, :, 1] = enhanced
    result[:, :, 2] = enhanced
    return np.clip(result, 0, 255).astype(np.uint8)


def colorize(arr, palette, accessory_mask, highlight_threshold=200):
    """
    Recolor hair pixels using a brightness-driven blend between
    shadow → base → highlight, with a small noise pass for texture.
    Pixels in accessory_mask are left untouched.
    """
    r = arr[:, :, 0].astype(np.float32)
    g = arr[:, :, 1].astype(np.float32)
    b = arr[:, :, 2].astype(np.float32)
    brightness = (r + g + b) / 3.0
    norm = np.clip(brightness / 255.0, 0, 1)

    if arr.shape[2] == 4:
        alpha = arr[:, :, 3]
        base_mask = (alpha > 10) & (brightness < highlight_threshold)
    else:
        base_mask = brightness < highlight_threshold

    hair_mask = base_mask & ~accessory_mask

    br, bg, bb = palette["base"]
    sr, sg, sb = palette["shadow"]
    hr, hg, hb = palette["highlight"]

    shadow_mix    = np.power(1 - norm, 1.5)
    highlight_mix = np.power(norm, 1.2)

    cr = br * (1 - shadow_mix) + sr * shadow_mix
    cg = bg * (1 - shadow_mix) + sg * shadow_mix
    cb = bb * (1 - shadow_mix) + sb * shadow_mix

    cr = cr * (1 - highlight_mix) + hr * highlight_mix
    cg = cg * (1 - highlight_mix) + hg * highlight_mix
    cb = cb * (1 - highlight_mix) + hb * highlight_mix

    noise = (np.random.rand(*norm.shape) - 0.5) * 0.05
    cr *= (1 + noise)
    cg *= (1 + noise * 0.5)
    cb *= (1 - noise * 0.3)

    result = arr.copy().astype(np.float32)
    result[:, :, 0] = np.where(hair_mask, cr, r)
    result[:, :, 1] = np.where(hair_mask, cg, g)
    result[:, :, 2] = np.where(hair_mask, cb, b)
    return np.clip(result, 0, 255).astype(np.uint8)


# ── VALIDATION ────────────────────────────────────────────────────────────────
missing_weights = set(HAIR_PALETTES.keys()) - set(WEIGHTS.keys())
if missing_weights:
    raise ValueError(f"Missing weights for palettes: {missing_weights}")

# ── MAIN LOOP ─────────────────────────────────────────────────────────────────
processed = 0
skipped   = 0

for filename in sorted(os.listdir(INPUT_DIR)):
    if not filename.endswith(".png"):
        continue

    base     = os.path.splitext(filename)[0]
    filepath = os.path.join(INPUT_DIR, filename)

    # ── Pass-through (no hair to recolor) ────────────────────────────────────
    if base in NO_COLOR:
        img      = Image.open(filepath)
        out_name = f"{base}#100.png"
        img.save(os.path.join(OUTPUT_DIR, out_name))
        print(f"[COPY]  {out_name}")
        processed += 1
        continue

    # ── Skip unregistered sprites ─────────────────────────────────────────────
    if base not in COLORABLE:
        print(f"[SKIP]  {filename}")
        skipped += 1
        continue

    img = Image.open(filepath).convert("RGBA")
    arr = np.array(img)

    arr = enhance_grayscale(arr)

    rules          = ACCESSORY_RULES.get(base, [])
    accessory_mask = build_accessory_mask(arr, rules)

    print(f"\n[PROCESSING]  {base}")

    for color_name, palette in HAIR_PALETTES.items():
        weight   = WEIGHTS[color_name]
        colored  = colorize(arr, palette, accessory_mask)
        out_img  = Image.fromarray(colored, "RGBA")
        out_name = f"{base}_{color_name}#{weight}.png"
        out_img.save(os.path.join(OUTPUT_DIR, out_name))
        print(f"  → {out_name}")

    processed += 1

# ── SUMMARY ───────────────────────────────────────────────────────────────────
colorable_processed = processed - len([b for b in NO_COLOR
                                       if os.path.exists(os.path.join(INPUT_DIR, b + ".png"))])
print(f"\n✅ Done.")
print(f"   {colorable_processed} hairstyle(s) × {len(HAIR_PALETTES)} colors "
      f"= {colorable_processed * len(HAIR_PALETTES)} colored outputs")
print(f"   + {len(NO_COLOR)} no-color pass-through(s)")
print(f"   {skipped} file(s) skipped (not in COLORABLE or NO_COLOR)")
