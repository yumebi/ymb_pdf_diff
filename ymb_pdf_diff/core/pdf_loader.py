from typing import Callable, Dict, List, Optional

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

from ..tesseract_setup import configure_bundled_tesseract
from .models import PageLine

ProgressCallback = Optional[Callable[[int, int], None]]

configure_bundled_tesseract()


class OcrUnavailableError(RuntimeError):
    """Tesseract-OCR本体がシステムに見つからない場合に送出する。"""


def _extract_text_layer_lines(page: "fitz.Page", page_index: int) -> List[PageLine]:
    page_lines: List[PageLine] = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            text = "".join(span["text"] for span in line.get("spans", [])).strip()
            if not text:
                continue
            page_lines.append(PageLine(page=page_index, text=text, bbox=tuple(line["bbox"])))
    return page_lines


def _ocr_page_lines(page: "fitz.Page", page_index: int, dpi: int, lang: str) -> List[PageLine]:
    zoom = dpi / 72
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    try:
        data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
    except pytesseract.TesseractNotFoundError as exc:
        raise OcrUnavailableError(
            "Tesseract-OCR本体が見つからない。OS別にインストールが必要(スキャンPDFの対応には別途要)。"
        ) from exc

    scale = 72 / dpi  # OCRはdpi基準の座標になるため、PDF座標(72dpi基準)に揃える
    lines: Dict[tuple, dict] = {}
    for i, text in enumerate(data["text"]):
        text = text.strip()
        if not text:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        left, top = data["left"][i] * scale, data["top"][i] * scale
        right = left + data["width"][i] * scale
        bottom = top + data["height"][i] * scale
        if key not in lines:
            lines[key] = {"words": [text], "bbox": [left, top, right, bottom]}
        else:
            entry = lines[key]
            entry["words"].append(text)
            entry["bbox"][0] = min(entry["bbox"][0], left)
            entry["bbox"][1] = min(entry["bbox"][1], top)
            entry["bbox"][2] = max(entry["bbox"][2], right)
            entry["bbox"][3] = max(entry["bbox"][3], bottom)

    return [
        PageLine(page=page_index, text=" ".join(lines[key]["words"]), bbox=tuple(lines[key]["bbox"]))
        for key in sorted(lines.keys())
    ]


def load_pdf_pages(
    path: str,
    use_ocr: bool = True,
    ocr_lang: str = "jpn+eng",
    ocr_dpi: int = 300,
    progress_callback: ProgressCallback = None,
) -> List[List[PageLine]]:
    """各ページのテキストを行単位で抽出する。

    テキストレイヤーがないページ(スキャンPDF)は use_ocr=True の場合、pytesseractでOCRして合流させる。
    progress_callback(現在のページ番号1始まり, 総ページ数) はページ処理ごとに呼ばれる(OCR有無に関わらず)。
    """
    doc = fitz.open(path)
    pages: List[List[PageLine]] = []
    try:
        total = doc.page_count
        for page_index in range(total):
            page = doc[page_index]
            page_lines = _extract_text_layer_lines(page, page_index)

            if not page_lines and use_ocr:
                page_lines = _ocr_page_lines(page, page_index, dpi=ocr_dpi, lang=ocr_lang)

            pages.append(page_lines)
            if progress_callback:
                progress_callback(page_index + 1, total)
    finally:
        doc.close()
    return pages
