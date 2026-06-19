from typing import List, Tuple

import fitz  # PyMuPDF
import numpy as np
from PIL import Image, ImageChops, ImageDraw

from .models import ImageDiffResult


def render_page(pdf_path: str, page_index: int, dpi: int = 150) -> Image.Image:
    doc = fitz.open(pdf_path)
    try:
        page = doc[page_index]
        zoom = dpi / 72
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    finally:
        doc.close()


def pad_to_same_size(img_a: Image.Image, img_b: Image.Image) -> Tuple[Image.Image, Image.Image]:
    width = max(img_a.width, img_b.width)
    height = max(img_a.height, img_b.height)
    canvas_a = Image.new("RGB", (width, height), "white")
    canvas_a.paste(img_a, (0, 0))
    canvas_b = Image.new("RGB", (width, height), "white")
    canvas_b.paste(img_b, (0, 0))
    return canvas_a, canvas_b


def _extract_regions(mask: np.ndarray, row_gap: int) -> List[Tuple[int, int, int, int]]:
    """差分ピクセルのある行を近接バンドにまとめ、各バンドの矩形(x0,y0,x1,y1)を返す。"""
    rows_with_diff = np.where(mask.any(axis=1))[0]
    if rows_with_diff.size == 0:
        return []

    bands = []
    band_start = rows_with_diff[0]
    prev = rows_with_diff[0]
    for r in rows_with_diff[1:]:
        if r - prev > row_gap:
            bands.append((band_start, prev))
            band_start = r
        prev = r
    bands.append((band_start, prev))

    regions: List[Tuple[int, int, int, int]] = []
    for y0, y1 in bands:
        band_mask = mask[y0 : y1 + 1, :]
        cols = np.where(band_mask.any(axis=0))[0]
        if cols.size == 0:
            continue
        regions.append((int(cols[0]), int(y0), int(cols[-1]) + 1, int(y1) + 1))
    return regions


def diff_images(img_a: Image.Image, img_b: Image.Image, threshold: int = 30, row_gap: int = 6) -> ImageDiffResult:
    size_a = img_a.size
    size_b = img_b.size
    canvas_a, canvas_b = pad_to_same_size(img_a, img_b)

    diff = ImageChops.difference(canvas_a, canvas_b).convert("L")
    mask = np.array(diff) > threshold

    diff_pixels = int(mask.sum())
    diff_ratio = diff_pixels / mask.size if mask.size else 0.0
    regions = _extract_regions(mask, row_gap=row_gap)

    return ImageDiffResult(
        has_diff=diff_pixels > 0,
        diff_ratio=diff_ratio,
        regions=regions,
        size_a=size_a,
        size_b=size_b,
    )


def diff_page_pair(
    pdf_a: str, a_page_index: int, pdf_b: str, b_page_index: int, dpi: int = 150, threshold: int = 30, row_gap: int = 6
) -> ImageDiffResult:
    img_a = render_page(pdf_a, a_page_index, dpi=dpi)
    img_b = render_page(pdf_b, b_page_index, dpi=dpi)
    return diff_images(img_a, img_b, threshold=threshold, row_gap=row_gap)


def draw_highlights(
    image: Image.Image, regions: List[Tuple[int, int, int, int]], color: str = "red", width: int = 3, padding: int = 10
) -> Image.Image:
    """差分領域に矩形ハイライトを描いた画像コピーを返す(キャプチャ用、元画像は変更しない)。

    paddingで矩形を外側に広げる(差分ピクセルのギリギリではなく、少し余裕を持たせて見やすくする)。
    """
    highlighted = image.copy()
    draw = ImageDraw.Draw(highlighted)
    w, h = image.size
    for x0, y0, x1, y1 in regions:
        box = [
            max(0, x0 - padding),
            max(0, y0 - padding),
            min(w - 1, x1 - 1 + padding),
            min(h - 1, y1 - 1 + padding),
        ]
        draw.rectangle(box, outline=color, width=width)
    return highlighted
