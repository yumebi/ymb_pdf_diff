"""HTML/CSV差分レポート出力(#新機能13)が正常に生成できることを確認する。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ymb_pdf_diff.core import align_documents, detect_visual_only_changes, load_pdf_pages
from ymb_pdf_diff.report import build_csv_report, build_html_report

import fitz


def _make_sample_pdfs(tmp_dir: Path):
    doc_a = fitz.open()
    doc_a.new_page().insert_text((72, 72), "Page A1 alpha text here.")
    doc_a.new_page().insert_text((72, 72), "Page A2 beta text here unchanged.")
    path_a = tmp_dir / "html_csv_sample_a.pdf"
    doc_a.save(str(path_a))
    doc_a.close()

    doc_b = fitz.open()
    doc_b.new_page().insert_text((72, 72), "Page A1 alpha text here CHANGED.")
    doc_b.new_page().insert_text((72, 72), "Page A2 beta text here unchanged.")
    path_b = tmp_dir / "html_csv_sample_b.pdf"
    doc_b.save(str(path_b))
    doc_b.close()
    return path_a, path_b


def _prepare(tmp_dir: Path):
    path_a, path_b = _make_sample_pdfs(tmp_dir)
    pages_a = load_pdf_pages(str(path_a))
    pages_b = load_pdf_pages(str(path_b))
    alignment = align_documents(pages_a, pages_b)
    detect_visual_only_changes(alignment, str(path_a), str(path_b))
    return path_a, path_b, pages_a, pages_b, alignment


def test_build_html_report():
    tmp_dir = Path(__file__).resolve().parent.parent
    path_a, path_b, pages_a, pages_b, alignment = _prepare(tmp_dir)
    output_path = tmp_dir / "html_report_sample_output.html"
    try:
        build_html_report(
            str(path_a), str(path_b), pages_a, pages_b, alignment, str(output_path),
        )
        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")

        # 単一HTMLとして成立していること
        assert "<!DOCTYPE html>" in content
        assert "</html>" in content
        # ファイル情報とステータス一覧が含まれること
        assert "PDF差分レポート" in content
        assert "差分あり" in content
        assert "差分なし" in content
        # 変更ページのテキスト差分(種別ラベルと変更前/変更後)が含まれること
        assert "テキスト差分" in content
        assert "変更前" in content
        assert "変更後" in content

        print("OK: test_build_html_report")
    finally:
        path_a.unlink(missing_ok=True)
        path_b.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)


def test_build_csv_report():
    tmp_dir = Path(__file__).resolve().parent.parent
    path_a, path_b, pages_a, pages_b, alignment = _prepare(tmp_dir)
    output_path = tmp_dir / "csv_report_sample_output.csv"
    try:
        build_csv_report(
            str(path_a), str(path_b), pages_a, pages_b, alignment, str(output_path),
        )
        assert output_path.exists()

        raw = output_path.read_bytes()
        # 文字化け防止のBOM付きUTF-8(utf-8-sig)で書き出されていること
        assert raw.startswith(b"\xef\xbb\xbf")
        text = raw.decode("utf-8-sig")

        # ヘッダー行とページ別ステータス行が含まれること
        assert "ページ番号A,ページ番号B,ステータス,備考,差分件数" in text
        assert "差分あり" in text
        assert "差分なし" in text

        # ファイル情報行が含まれること
        assert "ファイルA" in text
        assert "ファイルB" in text
        assert "総差分件数" in text

        print("OK: test_build_csv_report")
    finally:
        path_a.unlink(missing_ok=True)
        path_b.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)


if __name__ == "__main__":
    test_build_html_report()
    test_build_csv_report()
