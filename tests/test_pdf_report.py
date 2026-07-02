"""PDFレポート出力(#新機能10)が最後まで動き、妥当な内容のPDFを生成できることを確認する。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fitz

from ymb_pdf_diff.core import align_documents, detect_visual_only_changes, load_pdf_pages
from ymb_pdf_diff.report import build_pdf_report


def _make_sample_pdfs(tmp_dir: Path):
    doc_a = fitz.open()
    doc_a.new_page().insert_text((72, 72), "Page A1 alpha text here.")
    doc_a.new_page().insert_text((72, 72), "Page A2 beta text here unchanged.")
    path_a = tmp_dir / "pdf_report_sample_a.pdf"
    doc_a.save(str(path_a))
    doc_a.close()

    doc_b = fitz.open()
    doc_b.new_page().insert_text((72, 72), "Page A1 alpha text here CHANGED.")
    doc_b.new_page().insert_text((72, 72), "Page A2 beta text here unchanged.")
    doc_b.new_page().insert_text((72, 72), "Page A3 brand new page only in B.")
    path_b = tmp_dir / "pdf_report_sample_b.pdf"
    doc_b.save(str(path_b))
    doc_b.close()
    return path_a, path_b


def test_build_pdf_report_produces_valid_pdf_with_summary_title():
    tmp_dir = Path(__file__).resolve().parent.parent
    path_a, path_b = _make_sample_pdfs(tmp_dir)
    output_path = tmp_dir / "pdf_report_sample_output.pdf"
    try:
        pages_a = load_pdf_pages(str(path_a))
        pages_b = load_pdf_pages(str(path_b))
        alignment = align_documents(pages_a, pages_b)
        detect_visual_only_changes(alignment, str(path_a), str(path_b))

        progress_calls = []
        build_pdf_report(
            str(path_a), str(path_b), pages_a, pages_b, alignment, str(output_path),
            progress_callback=lambda cur, total: progress_calls.append((cur, total)),
        )
        assert output_path.exists()
        assert progress_calls, "progress_callbackが一度も呼ばれていない"

        doc = fitz.open(str(output_path))
        try:
            # サマリーページ(1) + 差分のあるページ数(changed 1 + inserted 1)以上
            assert doc.page_count >= 2
            summary_text = doc[0].get_text()
            assert "PDF差分レポート" in summary_text
        finally:
            doc.close()

        print("OK: test_build_pdf_report_produces_valid_pdf_with_summary_title")
    finally:
        path_a.unlink(missing_ok=True)
        path_b.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)


if __name__ == "__main__":
    test_build_pdf_report_produces_valid_pdf_with_summary_title()
