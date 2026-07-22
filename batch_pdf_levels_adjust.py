#!/usr/bin/env python3
"""
Batch adjust black point / white point of all PDF pages (like Photoshop Curves
black/white point sliders) for every PDF in ./pdfs, writing results to
./processed_pdfs.

Instead of rasterizing entire pages (which destroys text/OCR layers and
bloats file size), this script keeps the original page content (text, OCR
layer, vector graphics) intact and only applies the levels adjustment to the
embedded raster images on each page, re-encoding them at their original
resolution.

CLI PARAMETERS
---------------
--black         Black point (0-254). Pixel values at/below this become pure
                 black. Default: 20
--white         White point (1-255). Pixel values at/above this become pure
                 white. Default: 230
--input-dir     Folder containing source PDFs. Default: pdfs
--output-dir    Folder for processed PDFs. Default: processed_pdfs
--jpeg-quality  JPEG quality for re-encoded images (1-95). Default: auto -
                 detects and matches each image's original JPEG quality
                 (via its quantization tables) to avoid file-size growth.

USAGE EXAMPLES
---------------
# Use defaults (black=20, white=230, auto JPEG quality)
python batch_pdf_levels_adjust.py

# Custom black/white points
python batch_pdf_levels_adjust.py --black 15 --white 240

# Force a specific JPEG quality (lower = smaller files, more compression
# artifacts). Useful if auto-detected quality still yields larger files
# than the originals.
python batch_pdf_levels_adjust.py --black 20 --white 230 --jpeg-quality 60

# Custom input/output folders
python batch_pdf_levels_adjust.py --input-dir scans --output-dir scans_adjusted

TIPS
-----
- Start with the defaults (20/230) and inspect a couple of output pages;
  nudge --white down (e.g. 220) for scans with a grayish background, or
  --black up (e.g. 30-40) to deepen faint text.
- If output files are noticeably larger than the originals, try setting
  --jpeg-quality explicitly to something below the auto-detected value
  (e.g. 60-70).
- This script only touches embedded raster images; text, OCR layers, and
  vector content are passed through untouched.
- 1-bit / palette images are re-encoded as PNG (lossless), which can be
  larger than the original bilevel encoding for very large scans.
"""

import argparse
import io
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image
import numpy as np


def estimate_jpeg_quality(pil_img: Image.Image, default: int = 75) -> int:
    """Roughly estimate the JPEG quality used to encode the source image,
    based on its quantization tables, so re-encoding doesn't inflate size."""
    try:
        qtables = pil_img.quantization
        if not qtables:
            return default
        # Use the luminance table (key 0) sum as a rough proxy.
        table = qtables.get(0)
        if not table:
            table = next(iter(qtables.values()))
        avg = sum(table) / len(table)
        # Empirical mapping: lower average -> higher quality.
        if avg <= 2:
            return 95
        elif avg <= 6:
            return 90
        elif avg <= 12:
            return 80
        elif avg <= 20:
            return 75
        elif avg <= 35:
            return 65
        else:
            return 50
    except Exception:
        return default


def adjust_levels(img: Image.Image, black: int, white: int) -> Image.Image:
    """Apply a Photoshop-Curves-style black/white point adjustment."""
    if black >= white:
        raise ValueError("black point must be less than white point")

    mode = img.mode
    if mode not in ("L", "RGB"):
        img = img.convert("RGB")
        mode = "RGB"

    arr = np.asarray(img).astype(np.float32)
    arr = (arr - black) * (255.0 / (white - black))
    arr = np.clip(arr, 0, 255).astype(np.uint8)

    return Image.fromarray(arr, mode=mode)


def process_pdf(
    src_path: Path, dst_path: Path, black: int, white: int, jpeg_quality=None
):
    doc = fitz.open(src_path)

    seen_xrefs = set()

    for page in doc:
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)

            try:
                base_image = doc.extract_image(xref)
            except Exception:
                continue

            img_bytes = base_image["image"]

            try:
                pil_img = Image.open(io.BytesIO(img_bytes))
                pil_img.load()
            except Exception:
                continue

            # Skip tiny images (icons, masks, etc.)
            if pil_img.width < 8 or pil_img.height < 8:
                continue

            # If this image has a soft mask (SMask) or explicit mask, drop
            # the mask reference. We're baking the adjustment directly into
            # the visible pixels and replacing the stream as an opaque
            # image; leaving the old mask attached causes huge transparent/
            # black areas because the mask no longer corresponds correctly.
            for mask_key in ("SMask", "Mask"):
                try:
                    if doc.xref_get_key(xref, mask_key)[0] != "null":
                        doc.xref_set_key(xref, mask_key, "null")
                except Exception:
                    pass

            # Drop a leftover /Decode array (e.g. inverted CMYK scans). If
            # we don't remove this, the new (non-inverted) JPEG gets
            # re-inverted by the viewer -> mostly black pages.
            try:
                if doc.xref_get_key(xref, "Decode")[0] != "null":
                    doc.xref_set_key(xref, "Decode", "null")
            except Exception:
                pass

            # Drop alpha channel from the working image (we removed the
            # SMask, so the rendered image must be fully opaque).
            if pil_img.mode in ("RGBA", "LA"):
                pil_img = (
                    pil_img.convert("RGB")
                    if pil_img.mode == "RGBA"
                    else pil_img.convert("L")
                )

            # CMYK or other non-RGB/L modes: normalize to RGB so our new
            # JPEG's component count matches what we'll set /ColorSpace to.
            if pil_img.mode not in ("L", "RGB"):
                pil_img = pil_img.convert("RGB")

            orig_mode = pil_img.mode
            quality = (
                jpeg_quality
                if jpeg_quality is not None
                else estimate_jpeg_quality(pil_img, default=75)
            )

            try:
                adjusted = adjust_levels(pil_img, black, white)
            except Exception:
                continue

            # Re-encode at original resolution. JPEG keeps size down.
            buf = io.BytesIO()
            use_png = orig_mode in ("P", "1")
            if use_png:
                adjusted.save(buf, format="PNG", optimize=True)
            else:
                save_img = adjusted.convert("RGB") if adjusted.mode != "L" else adjusted
                save_img.save(buf, format="JPEG", quality=quality)
            new_bytes = buf.getvalue()

            # Replace the image. Prefer page.replace_image() (newer PyMuPDF)
            # which correctly rewrites ColorSpace/Filter/Decode/masks for us.
            # Fall back to manual stream + dict patching on older versions.
            if hasattr(page, "replace_image"):
                try:
                    page.replace_image(xref, stream=new_bytes)
                    continue
                except Exception:
                    pass

            try:
                doc.update_stream(xref, new_bytes)
            except Exception:
                continue

            # Fix up the image xref dict so the new stream is interpreted
            # correctly regardless of what the original encoding was.
            new_w, new_h = adjusted.size
            new_csname = "DeviceGray" if adjusted.mode == "L" else "DeviceRGB"
            new_filter = "FlateDecode" if use_png else "DCTDecode"
            try:
                doc.xref_set_key(xref, "Width", str(new_w))
                doc.xref_set_key(xref, "Height", str(new_h))
                doc.xref_set_key(xref, "BitsPerComponent", "8")
                doc.xref_set_key(xref, "ColorSpace", f"/{new_csname}")
                doc.xref_set_key(xref, "Filter", f"/{new_filter}")
            except Exception:
                continue

    doc.save(dst_path, garbage=4, deflate=True)
    doc.close()


def main():
    parser = argparse.ArgumentParser(
        description="Batch-adjust black/white points of images inside PDFs (Curves-style), preserving text/OCR layers."
    )
    parser.add_argument(
        "--black",
        type=int,
        default=20,
        help="Black point (0-254), input values below become pure black. Default: 20",
    )
    parser.add_argument(
        "--white",
        type=int,
        default=230,
        help="White point (1-255), input values above become pure white. Default: 230",
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default="pdfs",
        help="Folder containing source PDFs. Default: pdfs",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="processed_pdfs",
        help="Folder for processed PDFs. Default: processed_pdfs",
    )
    parser.add_argument(
        "--jpeg-quality",
        type=int,
        default=None,
        help="JPEG quality for re-encoded images (1-95). Default: auto-detect "
        "and match each image's original quality to avoid file-size growth.",
    )
    args = parser.parse_args()

    if not (0 <= args.black < args.white <= 255):
        parser.error("Require 0 <= black < white <= 255")

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(input_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in '{input_dir}'.")
        return

    for pdf_file in pdf_files:
        out_file = output_dir / pdf_file.name
        print(f"Processing: {pdf_file.name} -> {out_file}")
        try:
            process_pdf(
                pdf_file,
                out_file,
                args.black,
                args.white,
                jpeg_quality=args.jpeg_quality,
            )
        except Exception as e:
            print(f"  Error processing {pdf_file.name}: {e}")

    print("Done.")


if __name__ == "__main__":
    main()
