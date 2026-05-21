# NFT Hair Colorizer — Generalized Prompt & Requirements

## 📋 Project Overview

A Python pipeline that takes grayscale or lightly-tinted hairstyle sprite PNGs and
recolors them across a defined set of hair color palettes using a brightness-preserving
Azuki-style colorization engine. Outputs are named with rarity weights for use in
NFT trait generation systems.

---

## 🤖 Prompt to Reproduce This Script

Use the following prompt with an AI assistant (Claude, ChatGPT, etc.) to regenerate
or adapt this pipeline for your own asset set:

---

> **Prompt:**
>
> Write a Python script that batch-recolors grayscale hair sprite PNGs for an NFT
> collection. The script should:
>
> 1. Read all `.png` files from an input directory.
> 2. Separate sprites into two groups:
>    - `COLORABLE` — hair sprites that get recolored across all palettes.
>    - `NO_COLOR` — sprites (e.g. bald) that are copied as-is with a fixed weight.
> 3. Define a set of named hair color palettes, each with three RGB values:
>    `base`, `shadow`, and `highlight`.
> 4. Define rarity weights per color name (integers that sum to ~100).
> 5. For each colorable sprite:
>    a. Load the image as RGBA.
>    b. Enhance grayscale contrast using a gamma/sigmoid-style curve.
>    c. Build an accessory mask to protect non-hair pixels from recoloring,
>       using hue+saturation rules (for colored accessories) and
>       brightness+saturation rules (for grey/neutral accessories).
>    d. Colorize using a brightness-driven blend: dark pixels pull toward
>       `shadow`, light pixels pull toward `highlight`, mid pixels use `base`.
>       Add a small per-channel noise pass for texture variation.
>    e. Save each color variant as `{sprite_name}_{ColorName}#{weight}.png`
>       into an output directory.
> 6. For NO_COLOR sprites, copy as-is and save as `{sprite_name}#{weight}.png`.
> 7. Print a summary of outputs when done.
>
> Use only `Pillow` and `numpy`. No OpenCV.

---

## ⚙️ Requirements

### Python Dependencies

```
Pillow>=9.0.0
numpy>=1.21.0
```

Install with:

```bash
pip install Pillow numpy
```

### Python Version

- Python 3.8 or higher recommended.

---

## 📁 Input/Output Structure

```
project/
├── Hairstyles_[Gender]/          ← Input: grayscale PNGs, one per hairstyle
│   ├── style_a.png
│   ├── style_b.png
│   └── ...
├── Hairstyles_[Gender]_Colored/  ← Output: auto-created by the script
│   ├── style_a_Black#40.png
│   ├── style_a_Blonde#5.png
│   └── ...
└── generate_hair_colors.py
```

### Sprite Requirements

| Property        | Requirement                                        |
|-----------------|----------------------------------------------------|
| Format          | PNG with alpha channel (RGBA)                      |
| Base style      | Grayscale or near-grayscale (desaturated)          |
| Background      | Transparent (alpha = 0)                            |
| Hair pixels     | Dark to light grayscale values on transparent bg   |
| Accessories     | Any non-hair colored elements (beads, clips, etc.) |

> **Tip:** Sprites do not need to be perfectly grayscale. The colorizer will
> override any existing hue. Use near-black shadows, mid-grey midtones, and
> near-white highlights for best results.

---

## 🎨 Palette Design Guide

Each palette entry has three RGB tuples:

```python
"ColorName": {
    "base":      (R, G, B),   # mid-tone base color
    "shadow":    (R, G, B),   # darkest shade (used in shadows)
    "highlight": (R, G, B),   # brightest point (used in highlights)
}
```

### Rules of Thumb

- `shadow` should be a darker, more saturated version of `base`.
- `highlight` should be lighter and slightly warm/cool shifted.
- For fantasy colors, keep saturation high across all three values.
- For naturals (black, brown), keep saturation low and values close.

---

## ⚖️ Rarity Weight System

Weights are integers attached to the filename via `#{weight}`. They are **not**
enforced by the script — they are metadata for your NFT generation layer (e.g.
HashLips, Bueno, custom combiners) to use during trait selection.

```python
WEIGHTS = {
    "Black":      40,   # most common
    "DarkBrown":  25,
    ...
    "FantasyRed":  1,   # rarest
}
```

All weights should sum to **100** for clean percentage-based rarity.

---

## 🛡️ Accessory Mask — Protecting Non-Hair Pixels

If a hairstyle sprite contains colored accessories (beads, clips, dyed tips),
define per-sprite hue rules to prevent those pixels from being recolored:

```python
ACCESSORY_RULES = {
    "your_style_name": [
        {"hue": 0,   "hue_range": 20,  "min_sat": 0.35},  # reds
        {"hue": 240, "hue_range": 30,  "min_sat": 0.30},  # blues
        # add one rule per distinct accessory hue
    ],
}
```

For **grey/metallic** accessories (clips, bands), use brightness ranges instead:

```python
grey_ranges = [(80, 200)]  # protect mid-grey brightness band
```

Pass both to `build_accessory_mask(arr, rules, grey_ranges)`.

---

## 🔧 Customization Checklist

Before running, configure these sections in the script:

- [ ] `INPUT_DIR` / `OUTPUT_DIR` — set to your folder names
- [ ] `HAIR_PALETTES` — define your color palette set
- [ ] `WEIGHTS` — assign rarity weights matching your palette keys
- [ ] `COLORABLE` — list your recolorable sprite base names (no `.png`)
- [ ] `NO_COLOR` — list any pass-through sprites (bald, shaved, etc.)
- [ ] `ACCESSORY_RULES` — add rules for any sprites with colored accessories

---

## ✅ Output Naming Convention

```
{sprite_base_name}_{ColorName}#{weight}.png
```

Examples:
```
curly_fade_Black#40.png
curly_fade_Blonde#5.png
bald_none#100.png
```

This format is compatible with most NFT layer combiners that parse `#weight`
from filenames.

---

## 🚫 What This Repo Does NOT Include

- Specific hairstyle names or asset files (proprietary to each project).
- Specific palette RGB values (design decision per collection).
- Rarity weight distributions (collection-specific).
- Any generated output PNGs.
