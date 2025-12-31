import argparse
from pathlib import Path
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont, ImageOps
import piexif


SUPPORTED_EXTS = {".jpg", ".jpeg", ".png"}


def getExifDatetime(imagePath: Path):
    try:
        exifDict = piexif.load(str(imagePath))
    except Exception:
        return None

    exif = exifDict.get("Exif", {})
    zeroth = exifDict.get("0th", {})

    dateBytes = (
        exif.get(piexif.ExifIFD.DateTimeOriginal)
        or zeroth.get(piexif.ImageIFD.DateTime)
    )

    if not dateBytes:
        return None

    try:
        dateString = dateBytes.decode("utf-8", errors="ignore").strip()
        return datetime.strptime(dateString, "%Y:%m:%d %H:%M:%S")
    except Exception:
        return None


def pickFont(fontPath, fontSize):
    if fontPath:
        try:
            return ImageFont.truetype(fontPath, fontSize)
        except Exception:
            pass

    fallbackFonts = [
        "arial.ttf",
        "Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]

    for font in fallbackFonts:
        try:
            return ImageFont.truetype(font, fontSize)
        except Exception:
            continue

    return ImageFont.load_default()


def computePosition(imgWidth, imgHeight, textWidth, textHeight, corner, padX, padY):
    corner = corner.lower()

    if corner == "br":
        return (imgWidth - textWidth - padX, imgHeight - textHeight - padY)
    if corner == "bl":
        return (padX, imgHeight - textHeight - padY)
    if corner == "tr":
        return (imgWidth - textWidth - padX, padY)
    if corner == "tl":
        return (padX, padY)

    raise ValueError("Invalid corner option")


def stampImage(
    inputPath,
    outputPath,
    text,
    corner,
    font,
    fillColor,
    strokeColor,
    strokeWidth,
    padX,
    padY,
    drawBox,
    boxFill,
    boxPadding,
    drawShadow,
    shadowOffset,
    shadowFill,
):
    with Image.open(inputPath) as image:
        image = ImageOps.exif_transpose(image)
        imageRGBA = image.convert("RGBA")
        draw = ImageDraw.Draw(imageRGBA)

        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=strokeWidth)
        textWidth = bbox[2] - bbox[0]
        textHeight = bbox[3] - bbox[1]

        x, y = computePosition(
            imageRGBA.width,
            imageRGBA.height,
            textWidth,
            textHeight,
            corner,
            padX,
            padY,
        )

        if drawBox:
            rect = (
                x - boxPadding,
                y - boxPadding,
                x + textWidth + boxPadding,
                y + textHeight + boxPadding,
            )
            draw.rectangle(rect, fill=boxFill)

        if drawShadow:
            dx, dy = shadowOffset
            draw.text(
                (x + dx, y + dy),
                text,
                font=font,
                fill=shadowFill,
            )

        draw.text(
            (x, y),
            text,
            font=font,
            fill=fillColor,
            stroke_fill=strokeColor if strokeWidth > 0 else None,
            stroke_width=strokeWidth if strokeWidth > 0 else 0,
        )

        outputPath.parent.mkdir(parents=True, exist_ok=True)
        if outputPath.suffix.lower() in [".jpg", ".jpeg"]:
            imageRGBA.convert("RGB").save(outputPath, quality=95)
        else:
            imageRGBA.save(outputPath)


def parseColor(colorString, rgba=False):
    values = [int(v.strip()) for v in colorString.split(",")]

    if rgba:
        if len(values) == 3:
            values.append(180)
        return tuple(values)

    return tuple(values)


def main():
    parser = argparse.ArgumentParser("Nikon-style EXIF date restamper")

    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("-o", "--output", required=True)

    parser.add_argument("--format", default="%m.%d.%Y   %H:%M")
    parser.add_argument("--corner", default="br", choices=["br", "bl", "tr", "tl"])
    parser.add_argument("--size", type=int, default=44)

    parser.add_argument("--pad", type=int, default=24)
    parser.add_argument("--padX", type=int, default=None)
    parser.add_argument("--padY", type=int, default=None)

    parser.add_argument("--fill", default="255,165,0")
    parser.add_argument("--stroke", default="0,0,0")
    parser.add_argument("--strokeWidth", type=int, default=0)
    parser.add_argument("--font", default=None)

    parser.add_argument("--box", action="store_true")
    parser.add_argument("--boxFill", default="0,0,0,140")
    parser.add_argument("--boxPad", type=int, default=10)

    parser.add_argument("--shadow", action="store_true")
    parser.add_argument("--shadowOffset", default="5,5")
    parser.add_argument("--shadowFill", default="0,0,0,230")

    # Add your own presets alongside "nikon"
    parser.add_argument("--preset", choices=["none", "nikon"], default="none")

    args = parser.parse_args()

    # VERY TEDIOUS PLACING FOR THE DATESTAMP AHHH
    # Can add your own version :)
    if args.preset == "nikon":
        args.size = 160
        args.padX = 340
        args.padY = 360
        args.shadow = True
        args.strokeWidth = 0
        args.box = False

    padX = args.padX if args.padX is not None else args.pad
    padY = args.padY if args.padY is not None else args.pad

    fillColor = parseColor(args.fill)
    strokeColor = parseColor(args.stroke) if args.strokeWidth > 0 else None
    boxFill = parseColor(args.boxFill, rgba=True)
    shadowFill = parseColor(args.shadowFill, rgba=True)
    shadowOffset = tuple(int(v) for v in args.shadowOffset.split(","))

    font = pickFont(args.font, args.size)

    inputDir = Path(args.input)
    outputDir = Path(args.output)

    imageFiles = [
        p for p in inputDir.rglob("*") if p.suffix.lower() in SUPPORTED_EXTS
    ]

    for imagePath in imageFiles:
        timestamp = getExifDatetime(imagePath)
        if not timestamp:
            continue

        text = timestamp.strftime(args.format)

        outputPath = outputDir / imagePath.relative_to(inputDir)
        outputPath = outputPath.with_name(
            outputPath.stem + "_stamped" + outputPath.suffix
        )

        stampImage(
            imagePath,
            outputPath,
            text,
            args.corner,
            font,
            fillColor,
            strokeColor,
            args.strokeWidth,
            padX,
            padY,
            args.box,
            boxFill,
            args.boxPad,
            args.shadow,
            shadowOffset,
            shadowFill,
        )

    print("Done.")


if __name__ == "__main__":
    main()
