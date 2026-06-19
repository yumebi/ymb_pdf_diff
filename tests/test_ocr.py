"""スキャンPDF(テキストレイヤーなし)のOCR合流を確認する。
Tesseract-OCR本体が未インストールの環境では、クラッシュせず明確な例外になることを確認する。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fitz
from PIL import Image, ImageDraw

from ymb_pdf_diff.core import OcrUnavailableError, load_pdf_pages


def _make_scanned_pdf(path: Path, text: str) -> None:
    """テキストレイヤーを持たない(画像のみの)PDFを作る。"""
    img = Image.new("RGB", (600, 200), "white")
    ImageDraw.Draw(img).text((20, 80), text, fill="black")
    img_path = path.with_suffix(".png")
    img.save(img_path)

    doc = fitz.open()
    page = doc.new_page(width=600, height=200)
    page.insert_image(fitz.Rect(0, 0, 600, 200), filename=str(img_path))
    doc.save(str(path))
    doc.close()
    img_path.unlink()


def test_scanned_pdf_triggers_ocr_or_clear_error():
    tmp_dir = Path(__file__).resolve().parent.parent
    pdf_path = tmp_dir / "ocr_sample.pdf"
    try:
        _make_scanned_pdf(pdf_path, "OCR TEST PAGE")

        progress_calls = []
        try:
            pages = load_pdf_pages(str(pdf_path), progress_callback=lambda c, t: progress_calls.append((c, t)))
        except OcrUnavailableError as exc:
            assert "Tesseract" in str(exc)
            print("OK: test_scanned_pdf_triggers_ocr_or_clear_error (Tesseract未インストール、エラー文言を確認)")
            return

        assert len(pages) == 1
        assert progress_calls == [(1, 1)]
        joined = " ".join(line.text for line in pages[0])
        assert "OCR" in joined.upper()
        print("OK: test_scanned_pdf_triggers_ocr_or_clear_error (Tesseractで実OCR成功)")
    finally:
        pdf_path.unlink(missing_ok=True)


def test_use_ocr_false_leaves_scanned_page_empty():
    tmp_dir = Path(__file__).resolve().parent.parent
    pdf_path = tmp_dir / "ocr_sample_noocr.pdf"
    try:
        _make_scanned_pdf(pdf_path, "SHOULD NOT BE READ")
        pages = load_pdf_pages(str(pdf_path), use_ocr=False)
        assert pages == [[]]
        print("OK: test_use_ocr_false_leaves_scanned_page_empty")
    finally:
        pdf_path.unlink(missing_ok=True)


if __name__ == "__main__":
    test_scanned_pdf_triggers_ocr_or_clear_error()
    test_use_ocr_false_leaves_scanned_page_empty()
