#!/usr/bin/env python3
import argparse
import json
import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Missing dependency — run: pip install Pillow")

W, H        = 630, 880
CORNER_SIZE = 165
CORNER_PAD  = 30
CORNER_R    = 10
CARD_R      = 40
BORDER_W    = 6
INNER_OFF   = 16

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
CARDS_DIR   = os.path.join(SCRIPT_DIR, "cards")
SPECIAL_PNG = os.path.join(SCRIPT_DIR, "Special.png")


def hex_to_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def rounded_rect_mask(size, radius):
    mask = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, size[0]-1, size[1]-1], radius=radius, fill=255)
    return mask


def paste_rounded(base, img, xy, size, radius):
    thumb = img.resize(size, Image.LANCZOS)
    mask = rounded_rect_mask(size, radius)
    base.paste(thumb, xy, mask)


def fit_image(img, box_w, box_h):
    img.thumbnail((box_w, box_h), Image.LANCZOS)
    return img


def best_font(size):
    candidates = [
        "arialbd.ttf", "Arial Bold.ttf", "Arial_Bold.ttf",
        "impact.ttf", "Impact.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/impact.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def draw_text_shadow(draw, xy, text, font, fill, shadow_color=(0, 0, 0, 80), offset=(0, 2)):
    sx, sy = xy[0] + offset[0], xy[1] + offset[1]
    draw.text((sx, sy), text, font=font, fill=shadow_color, anchor="mm")
    draw.text(xy, text, font=font, fill=fill, anchor="mm")


def fit_font_to_width(text, start_size, max_width, min_size=16):
    size = start_size
    while size >= min_size:
        font = best_font(size)
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        if text_width <= max_width:
            return font
        size -= 2
    return best_font(min_size)


def force_cards_output(output_value, image_path):
    if output_value:
        filename = os.path.basename(output_value)
    else:
        stem = os.path.splitext(os.path.basename(image_path))[0]
        filename = f"{stem}-card.png"
    return os.path.join(CARDS_DIR, filename)


def get_logo_path(supermarket: str):
    if not supermarket:
        return None
    s = supermarket.strip().lower()
    if s == "aldi":
        return os.path.join(SCRIPT_DIR, "aldi.png")
    if s == "coles":
        return os.path.join(SCRIPT_DIR, "coles.png")
    if s == "woolworths":
        return os.path.join(SCRIPT_DIR, "woolworths.png")
    return None


def add_supermarket_logo(card, supermarket):
    logo_path = get_logo_path(supermarket)
    if not logo_path or not os.path.exists(logo_path):
        return

    logo = Image.open(logo_path).convert("RGBA")

    # Bigger logo
    max_w = 300
    max_h = 140
    logo.thumbnail((max_w, max_h), Image.LANCZOS)
    lw, lh = logo.size

    # Top centre
    logo_x = (W - lw) // 2
    logo_y = 20
    card.paste(logo, (logo_x, logo_y), logo)


def make_card(image_path: str, name: str = None, line: str = None,
              size: str = "", color: str = "#8B0000",
              output: str = None, special: bool = False,
              supermarket: str = "") -> str:

    if not os.path.exists(image_path):
        sys.exit(f"Image not found: {image_path}")

    stem = os.path.splitext(os.path.basename(image_path))[0]
    name = name or stem.upper()
    line = line or stem.upper()
    rgb = hex_to_rgb(color)

    src = Image.open(image_path).convert("RGBA")
    card = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    card_mask = rounded_rect_mask((W, H), CARD_R)

    centre_y = 170
    centre_h = 420
    centre_img = src.copy().convert("RGBA")
    centre_img = fit_image(centre_img, W - 80, centre_h)
    cw, ch = centre_img.size

    # Keep centre image centred
    cx = (W - cw) // 2
    cy = centre_y + (centre_h - ch) // 2
    card.paste(centre_img, (cx, cy), centre_img)

    cs = CORNER_SIZE
    cp = CORNER_PAD

    # Top-left thumbnail
    paste_rounded(card, src.copy().convert("RGB"), (cp, cp), (cs, cs), CORNER_R)

    # Bottom-right thumbnail
    br_img = src.copy().convert("RGB").rotate(180)
    paste_rounded(card, br_img, (W - cp - cs, H - cp - cs), (cs, cs), CORNER_R)

    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle([cp, cp, cp+cs, cp+cs], radius=CORNER_R,
                           outline=(180, 180, 180), width=1)
    draw.rounded_rectangle([W-cp-cs, H-cp-cs, W-cp, H-cp], radius=CORNER_R,
                           outline=(180, 180, 180), width=1)

    add_supermarket_logo(card, supermarket)

    font_name = fit_font_to_width(name, 46, 500, 20)
    font_line = fit_font_to_width(line, 54, 520, 18)
    font_size = best_font(28)

    text_cx = W // 2

    name_y = centre_y + centre_h + 42
    draw_text_shadow(draw, (text_cx, name_y), name, font_name, rgb)

    line_y = name_y + 62
    draw_text_shadow(draw, (text_cx, line_y), line, font_line, rgb)

    div_y = line_y + 30
    draw.line([(185, div_y), (445, div_y)], fill=(*rgb, 100), width=2)

    if size:
        draw.text((text_cx, div_y + 30), size, font=font_size,
                  fill=(60, 60, 60), anchor="mm")

    draw.rounded_rectangle([2, 2, W-3, H-3], radius=CARD_R,
                           outline=(0, 0, 0), width=BORDER_W)
    draw.rounded_rectangle([INNER_OFF, INNER_OFF, W-INNER_OFF-1, H-INNER_OFF-1],
                           radius=32, outline=(0, 0, 0), width=2)

    if special and os.path.exists(SPECIAL_PNG):
        badge = Image.open(SPECIAL_PNG).convert("RGBA")
        badge_size = 110
        badge.thumbnail((badge_size, badge_size), Image.LANCZOS)
        bw, bh = badge.size

        # Top-right
        tr_x = W - INNER_OFF - bw
        tr_y = INNER_OFF
        card.paste(badge, (tr_x, tr_y), badge)

        # Bottom-left
        bl_x = INNER_OFF
        bl_y = H - INNER_OFF - bh
        card.paste(badge, (bl_x, bl_y), badge)

    output = force_cards_output(output, image_path)
    os.makedirs(CARDS_DIR, exist_ok=True)

    out_img = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    out_img.paste(card, (0, 0), card_mask)
    out_img.convert("RGB").save(output, "PNG")
    print(f"OK  {output}")
    return output


def batch_from_json(json_path: str, default_color: str):
    json_dir = os.path.dirname(os.path.abspath(json_path))
    with open(json_path, encoding="utf-8") as f:
        products = json.load(f)

    for p in products:
        image = os.path.join(json_dir, p["image"])
        make_card(
            image_path=image,
            name=p.get("name"),
            line=p.get("line"),
            size=p.get("size", ""),
            color=p.get("color", default_color),
            output=p.get("out"),
            special=p.get("special", False),
            supermarket=p.get("supermarket", ""),
        )


def main():
    parser = argparse.ArgumentParser(description="Generate a playing-card PNG from a product image.")
    parser.add_argument("image", help="Product image (JPEG/PNG) or a .json file for batch mode")
    parser.add_argument("--name", default=None, help="Brand name")
    parser.add_argument("--line", default=None, help="Product line")
    parser.add_argument("--size", default="", help="Weight/size")
    parser.add_argument("--color", default="#8B0000", help="Hex text colour")
    parser.add_argument("--output", default=None, help="Output PNG filename")
    parser.add_argument("--special", action="store_true", help="Mark this card as a special")
    parser.add_argument("--supermarket", default="", help="Aldi, Coles, or Woolworths")
    args = parser.parse_args()

    if args.image.lower().endswith(".json"):
        batch_from_json(args.image, args.color)
    else:
        make_card(
            image_path=args.image,
            name=args.name,
            line=args.line,
            size=args.size,
            color=args.color,
            output=args.output,
            special=args.special,
            supermarket=args.supermarket,
        )


if __name__ == "__main__":
    main()