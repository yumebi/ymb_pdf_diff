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


def test_build_pdf_report_with_each_image_size_preset():
    """#新機能11: image_size="small"/"large"のいずれでも正常にレポートが生成できることを確認する
    (スモークテスト。ファイルサイズの詳細な比較はscripts/benchmark.pyで行う)。
    """
    tmp_dir = Path(__file__).resolve().parent.parent
    path_a, path_b = _make_sample_pdfs(tmp_dir)
    output_small = tmp_dir / "pdf_report_sample_output_small.pdf"
    output_large = tmp_dir / "pdf_report_sample_output_large.pdf"
    try:
        pages_a = load_pdf_pages(str(path_a))
        pages_b = load_pdf_pages(str(path_b))
        alignment = align_documents(pages_a, pages_b)
        detect_visual_only_changes(alignment, str(path_a), str(path_b))

        for output_path, size in ((output_small, "small"), (output_large, "large")):
            build_pdf_report(
                str(path_a), str(path_b), pages_a, pages_b, alignment, str(output_path), image_size=size,
            )
            assert output_path.exists()
            doc = fitz.open(str(output_path))
            try:
                assert doc.page_count >= 2
            finally:
                doc.close()

        print("OK: test_build_pdf_report_with_each_image_size_preset")
    finally:
        path_a.unlink(missing_ok=True)
        path_b.unlink(missing_ok=True)
        output_small.unlink(missing_ok=True)
        output_large.unlink(missing_ok=True)


def test_build_pdf_report_embeds_text_diff_content():
    """#報告対応: PDFレポートにも(Excelレポート同様)行単位のテキスト差分が埋め込まれることを確認する。

    変更前後で実際に異なるテキストを持つページペアを用意し、出力PDFのいずれかのページの
    get_text()に、その差分に由来する文字列が含まれることを検証する(キャプチャ画像だけでなく、
    テキスト差分そのものが描画されていることの証拠)。
    """
    tmp_dir = Path(__file__).resolve().parent.parent
    path_a, path_b = _make_sample_pdfs(tmp_dir)
    output_path = tmp_dir / "pdf_report_textdiff_output.pdf"
    try:
        pages_a = load_pdf_pages(str(path_a))
        pages_b = load_pdf_pages(str(path_b))
        alignment = align_documents(pages_a, pages_b)
        detect_visual_only_changes(alignment, str(path_a), str(path_b))

        build_pdf_report(str(path_a), str(path_b), pages_a, pages_b, alignment, str(output_path))
        assert output_path.exists()

        doc = fitz.open(str(output_path))
        try:
            full_text = "\n".join(doc[i].get_text() for i in range(doc.page_count))
        finally:
            doc.close()

        # sample_a/sample_bのページ1は"alpha text here."→"alpha text here CHANGED."に変わっている。
        # このテキスト差分由来の文字列がどこかのページに実際に埋め込まれていることを確認する。
        assert "変更" in full_text, "種別(変更)ラベルがPDFに見当たらない"
        assert "CHANGED" in full_text, "変更後のテキスト差分がPDFに埋め込まれていない"

        print("OK: test_build_pdf_report_embeds_text_diff_content")
    finally:
        path_a.unlink(missing_ok=True)
        path_b.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)


if __name__ == "__main__":
    test_build_pdf_report_produces_valid_pdf_with_summary_title()
    test_build_pdf_report_with_each_image_size_preset()
    test_build_pdf_report_embeds_text_diff_content()
