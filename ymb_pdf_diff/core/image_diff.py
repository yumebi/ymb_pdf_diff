from typing import List, Tuple

import fitz  # PyMuPDF
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

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


def _blur_for_comparison(img: Image.Image, radius: int) -> Image.Image:
    """位置ズレ許容(#新機能12)のため、比較専用にガウスぼかしを掛けたコピーを返す。

    radius<=0の場合は無加工(元画像そのまま)。ぼかすことでアンチエイリアスの違いや
    数ピクセル程度の一貫した位置ズレが吸収され、実際のレイアウト変更・内容差分のような
    ぼかし半径よりはるかに大きい差分だけが残るようになる。呼び出し元は返り値を書き換え
    ないため、radius<=0のときはコピーを作らずそのまま返す。
    """
    if radius <= 0:
        return img
    return img.filter(ImageFilter.GaussianBlur(radius))


def diff_images(
    img_a: Image.Image,
    img_b: Image.Image,
    threshold: int = 30,
    row_gap: int = 6,
    shift_tolerance: int = 0,
) -> ImageDiffResult:
    size_a = img_a.size
    size_b = img_b.size
    canvas_a, canvas_b = pad_to_same_size(img_a, img_b)

    # 位置ズレ許容(#新機能12): 実際の差分ピクセル判定にはぼかし後の画像を使う。
    # size_a/size_b等のメタデータは元画像基準のまま変えない(ぼかしは比較用のみ)。
    compare_a = _blur_for_comparison(canvas_a, shift_tolerance)
    compare_b = _blur_for_comparison(canvas_b, shift_tolerance)

    diff = ImageChops.difference(compare_a, compare_b).convert("L")
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
    pdf_a: str,
    a_page_index: int,
    pdf_b: str,
    b_page_index: int,
    dpi: int = 150,
    threshold: int = 30,
    row_gap: int = 6,
    shift_tolerance: int = 0,
) -> ImageDiffResult:
    img_a = render_page(pdf_a, a_page_index, dpi=dpi)
    img_b = render_page(pdf_b, b_page_index, dpi=dpi)
    return diff_images(img_a, img_b, threshold=threshold, row_gap=row_gap, shift_tolerance=shift_tolerance)


def overlay_images(img_a: Image.Image, img_b: Image.Image) -> Image.Image:
    """A/Bページを1枚に重ね合わせた合成画像(重ね表示モード用)を作る。

    それぞれをグレースケール化し(255=白/インクなし, 0=黒/インクあり)、
    RGBチャンネルへ以下のように割り当てる。
        R = Bのグレー値, G = A/Bの暗い方(=両方に共通するインク), B = Aのグレー値
    この割り当てにより、
        - 両方とも白いピクセルは (255,255,255) のまま白
        - Aのみにインクがある(A=黒,B=白)ピクセルは (255,0,0) = 赤
        - Bのみにインクがある(A=白,B=黒)ピクセルは (0,0,255) = 青
        - 両方にインクがある(A=黒,B=黒)ピクセルは (0,0,0) = 黒(暗く沈む)
    となり、「赤=ファイルAのみの内容 / 青=ファイルBのみの内容 / 黒=共通」を一目で判別できる。
    サイズが異なる場合はpad_to_same_sizeで白背景に揃えてから合成する。
    """
    canvas_a, canvas_b = pad_to_same_size(img_a, img_b)
    gray_a = np.array(canvas_a.convert("L"), dtype=np.uint8)
    gray_b = np.array(canvas_b.convert("L"), dtype=np.uint8)
    rgb = np.stack([gray_b, np.minimum(gray_a, gray_b), gray_a], axis=-1).astype(np.uint8)
    # mode引数は Pillow 13(2026-10)で削除される。(H, W, 3) の uint8 配列なので
    # 指定しなくてもRGBと判定される。
    return Image.fromarray(rgb)


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
