from __future__ import annotations

from io import BytesIO
from typing import Optional, Tuple

from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import pytesseract
from pytesseract import TesseractError

from app.settings import settings


def configure_tesseract() -> None:
    if settings.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd


def _preprocess_for_ocr(img: Image.Image) -> Image.Image:
    """
    Preprocessing tuned for chat/screenshot OCR:
    - auto rotate via EXIF
    - grayscale
    - upscale (improves small text)
    - contrast + sharpen + mild denoise
    - binary thresholding
    """
    img = ImageOps.exif_transpose(img)
    img = ImageOps.grayscale(img)

    # Upscale if small to help Tesseract
    w, h = img.size
    scale = 2 if max(w, h) < 1600 else 1.5
    img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

    img = ImageOps.autocontrast(img)
    img = ImageEnhance.Contrast(img).enhance(1.6)
    img = img.filter(ImageFilter.MedianFilter(size=3))
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=160, threshold=3))

    # Threshold to clean background
    img = img.point(lambda p: 255 if p > 165 else 0)
    return img


def extract_text_from_image(image_bytes: bytes) -> Tuple[str, Optional[str]]:
    """
    Returns (text, warning). Warning is set when extraction is likely degraded.
    """
    configure_tesseract()
    warning: Optional[str] = None

    img = Image.open(BytesIO(image_bytes))
    img = _preprocess_for_ocr(img)

    try:
        # Try Hindi+English first; fallback to English if Hindi data not installed.
        config = "--oem 3 --psm 6"
        try:
            text = pytesseract.image_to_string(img, lang="eng+hin", config=config)
        except TesseractError:
            text = pytesseract.image_to_string(img, lang="eng", config=config)
    except Exception as e:
        raise RuntimeError(f"OCR failed: {type(e).__name__}: {str(e)}") from e

    cleaned = " ".join((text or "").split())
    if len(cleaned) < 5:
        warning = "OCR extracted very little text; results may be unreliable."
    return cleaned, warning

