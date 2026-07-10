"""Excelレポート出力(#新機能11: image_sizeプリセット)が各サイズで正常に生成できることを確認する。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openpyxl import load_workbook

from ymb_pdf_diff.core import align_documents, detect_visual_only_changes, load_pdf_pages
from ymb_pdf_diff.report import build_excel_report

import fitz


def _make_sample_pdfs(tmp_dir: Path):
    doc_a = fitz.open()
    doc_a.new_page().insert_text((72, 72), "Page A1 alpha text here.")
    doc_a.new_page().insert_text((72, 72), "Page A2 beta text here unchanged.")
    path_a = tmp_dir / "excel_report_sample_a.pdf"
    doc_a.save(str(path_a))
    doc_a.close()

    doc_b = fitz.open()
    doc_b.new_page().insert_text((72, 72), "Page A1 alpha text here CHANGED.")
    doc_b.new_page().insert_text((72, 72), "Page A2 beta text here unchanged.")
    path_b = tmp_dir / "excel_report_sample_b.pdf"
    doc_b.save(str(path_b))
    doc_b.close()
    return path_a, path_b


def test_build_excel_report_with_each_image_size_preset():
    """#新機能11: image_size="small"/"medium"/"large"のいずれでも正常にExcelを生成できることを確認する
    (スモークテスト。ファイルサイズの詳細な比較はscripts/benchmark.pyで行う)。
    """
    tmp_dir = Path(__file__).resolve().parent.parent
    path_a, path_b = _make_sample_pdfs(tmp_dir)
    outputs = {size: tmp_dir / f"excel_report_sample_output_{size}.xlsx" for size in ("small", "medium", "large")}
    try:
        pages_a = load_pdf_pages(str(path_a))
        pages_b = load_pdf_pages(str(path_b))
        alignment = align_documents(pages_a, pages_b)
        detect_visual_only_changes(alignment, str(path_a), str(path_b))

        for size, output_path in outputs.items():
            build_excel_report(
                str(path_a), str(path_b), pages_a, pages_b, alignment, str(output_path), image_size=size,
            )
            assert output_path.exists()
            wb = load_workbook(str(output_path))
            assert "サマリー" in wb.sheetnames

        print("OK: test_build_excel_report_with_each_image_size_preset")
    finally:
        path_a.unlink(missing_ok=True)
        path_b.unlink(missing_ok=True)
        for output_path in outputs.values():
            output_path.unlink(missing_ok=True)


if __name__ == "__main__":
    test_build_excel_report_with_each_image_size_preset()
