import argparse
import os
from pathlib import Path
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont
import piexif


SUPPORTED_EXTS = {".jpg", ".jpeg", ".png"}


def get_exif_datetime(img_path: Path) -> datetime | None:
    """
    Tries DateTimeOriginal first, then DateTime.
    Returns a datetime or None if not found.
    """
    try:
        exif_dict = piexif.load(str(img_path))
    except Exception:
        return None

    exif = exif_dict.get("Exif", {})
    zeroth = exif_dict.get("0th", {})

    dt_bytes = exif.get(piexif.ExifIFD.DateTimeOriginal) or zeroth.get(piexif.ImageIFD.DateTime)
    if not dt_bytes:
        return None

    try:
        dt_str = dt_bytes.decode("utf-8", errors="ignore").strip()
        # EXIF format is usually "YYYY:MM:DD HH:MM:SS"
        return datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
    except Exception:
        return None


def pick_font(font_path: str | None, font_size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """
    Uses a provided .ttf/.otf if given, else tries common fonts, else PIL default.
    """
    if font_path:
        try:
            return ImageFont.truetype(font_path, font_size)
        except Exception:
            pass

    # Try a few common fonts (Windows/macOS/Linux); if none exist, fallback.
    candidates = [
        "arial.ttf",
        "Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, font_size)
        except Exception:
            continue

    return ImageFont.load_default()


def compute_position(img_w: int, img_h: int, text_w: int, text_h: int, corner: str, pad: int):
    corner = corner.lower()
    if corner == "br":
        return (img_w - text_w - pad, img_h - text_h - pad)
    if corner == "bl":
        return (pad, img_h - text_h - pad)
    if corner == "tr":
        return (img_w - text_w - pad, pad)
    if corner == "tl":
        return (pad, pad)
    raise ValueError("corner must be one of: br, bl, tr, tl")


def stamp_image(
    in_path: Path,
    out_path: Path,
    text: str,
    corner: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    stroke_fill: tuple[int, int, int] | None,
    stroke_width: int,
    pad: int,
    box: bool,
    box_fill: tuple[int, int, int, int],
    box_pad: int,
):
    with Image.open(in_path) as im:
        # Work in RGBA for box transparency, then convert back as needed
        im_rgba = im.convert("RGBA")
        draw = ImageDraw.Draw(im_rgba)

        # Measure text
        # Use textbbox for accurate sizing
        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        x, y = compute_position(im_rgba.width, im_rgba.height, text_w, text_h, corner, pad)

        if box:
            rect = (
                x - box_pad,
                y - box_pad,
                x + text_w + box_pad,
                y + text_h + box_pad,
            )
            draw.rectangle(rect, fill=box_fill)

        draw.text(
            (x, y),
            text,
            font=font,
            fill=fill,
            stroke_fill=stroke_fill if stroke_width > 0 else None,
            stroke_width=stroke_width if stroke_width > 0 else 0,
        )

        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Save back as RGB for jpg
        if out_path.suffix.lower() in [".jpg", ".jpeg"]:
            im_rgba.convert("RGB").save(out_path, quality=95)
        else:
            im_rgba.save(out_path)


def parse_color(s: str, rgba: bool = False):
    """
    Accepts '255,255,255' or '255,255,255,160'
    """
    parts = [p.strip() for p in s.split(",")]
    nums = [int(p) for p in parts]
    if rgba:
        if len(nums) == 3:
            nums.append(180)
        if len(nums) != 4:
            raise ValueError("RGBA color must be R,G,B or R,G,B,A")
        return tuple(nums)  # type: ignore
    else:
        if len(nums) != 3:
            raise ValueError("RGB color must be R,G,B")
        return tuple(nums)  # type: ignore


def main():
    ap = argparse.ArgumentParser(description="Re-stamp photos with EXIF date (Nikon Coolpix S9600 friendly).")
    ap.add_argument("--input", "-i", required=True, help="Input folder of images")
    ap.add_argument("--output", "-o", required=True, help="Output folder")
    ap.add_argument("--format", default="%Y-%m-%d %H:%M", help="Datetime format (strftime)")
    ap.add_argument("--corner", default="br", choices=["br", "bl", "tr", "tl"], help="Stamp corner")
    ap.add_argument("--size", type=int, default=44, help="Font size (pixels-ish)")
    ap.add_argument("--pad", type=int, default=24, help="Padding from edge")
    ap.add_argument("--fill", default="255,255,255", help="Text color R,G,B")
    ap.add_argument("--stroke", default="0,0,0", help="Stroke color R,G,B (outline)")
    ap.add_argument("--stroke_width", type=int, default=2, help="Outline thickness (0 to disable)")
    ap.add_argument("--font", default=None, help="Optional .ttf/.otf path")
    ap.add_argument("--box", action="store_true", help="Draw semi-transparent box behind text")
    ap.add_argument("--box_fill", default="0,0,0,140", help="Box color R,G,B,A")
    ap.add_argument("--box_pad", type=int, default=10, help="Box padding around text")
    args = ap.parse_args()

    in_dir = Path(args.input)
    out_dir = Path(args.output)

    if not in_dir.exists() or not in_dir.is_dir():
        raise SystemExit(f"Input folder not found: {in_dir}")

    fill = parse_color(args.fill, rgba=False)
    stroke = parse_color(args.stroke, rgba=False) if args.stroke_width > 0 else None
    box_fill = parse_color(args.box_fill, rgba=True)

    font = pick_font(args.font, args.size)

    files = [p for p in in_dir.rglob("*") if p.suffix.lower() in SUPPORTED_EXTS]
    if not files:
        raise SystemExit("No images found in input folder.")

    processed = 0
    skipped = 0

    for p in files:
        dt = get_exif_datetime(p)
        if not dt:
            skipped += 1
            continue

        text = dt.strftime(args.format)

        rel = p.relative_to(in_dir)
        out_path = out_dir / rel
        out_path = out_path.with_name(out_path.stem + "_stamped" + out_path.suffix)

        try:
            stamp_image(
                in_path=p,
                out_path=out_path,
                text=text,
                corner=args.corner,
                font=font,
                fill=fill,
                stroke_fill=stroke,
                stroke_width=args.stroke_width,
                pad=args.pad,
                box=args.box,
                box_fill=box_fill,
                box_pad=args.box_pad,
            )
            processed += 1
        except Exception:
            skipped += 1

    print(f"Done. Processed: {processed}, Skipped (no EXIF / errors): {skipped}")
    print(f"Output: {out_dir}")


if __name__ == "__main__":
    main()
