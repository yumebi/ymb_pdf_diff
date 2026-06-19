"""GUIがクラッシュせず比較〜表示〜Excel出力まで一通り動くことを確認するスモークテスト。
画面なし環境でも実行できるようQT_QPA_PLATFORM=offscreenを使う。
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fitz
from PySide6.QtWidgets import QApplication

from ymb_pdf_diff.gui import MainWindow


def _make_sample_pdfs(tmp_dir: Path):
    doc_a = fitz.open()
    doc_a.new_page().insert_text((72, 72), "Hello world this is page one of document A.")
    doc_a.new_page().insert_text((72, 72), "This is page two content unchanged.")
    path_a = tmp_dir / "gui_sample_a.pdf"
    doc_a.save(str(path_a))

    doc_b = fitz.open()
    doc_b.new_page().insert_text((72, 72), "Hello world THIS IS CHANGED page one of document B.")
    doc_b.new_page().insert_text((72, 72), "This is page two content unchanged.")
    path_b = tmp_dir / "gui_sample_b.pdf"
    doc_b.save(str(path_b))
    return path_a, path_b


def test_compare_and_render_smoke():
    tmp_dir = Path(__file__).resolve().parent.parent
    path_a, path_b = _make_sample_pdfs(tmp_dir)
    try:
        app = QApplication.instance() or QApplication(sys.argv)
        window = MainWindow()
        window.pdf_a_path = str(path_a)
        window.pdf_b_path = str(path_b)

        window._run_compare()
        assert window.alignment is not None
        assert window.diff_list.count() == len(window.alignment.page_statuses)
        assert window.btn_export.isEnabled()

        for row in range(window.diff_list.count()):
            window.diff_list.setCurrentRow(row)
            assert not window.view_a.current_pixmap().isNull() or window.alignment.page_statuses[row].a_page is None

        # ズーム連動(#11)
        window._apply_zoom(1.5)
        assert window.view_a.zoom() == 1.5
        assert window.view_b.zoom() == 1.5
        window.view_a.set_zoom(2.0)  # zoomed信号経由でview_bにも伝播するはず
        assert window.view_b.zoom() == 2.0
        window._apply_zoom(1.0)

        # ハイライト表示/非表示切替(#13)
        window.btn_toggle_highlight.setChecked(False)
        window._toggle_highlight()
        assert window.show_highlights is False
        window.btn_toggle_highlight.setChecked(True)
        window._toggle_highlight()
        assert window.show_highlights is True

        # 配色(#12): changed行は背景色と文字色が異なる(視認性確保)
        changed_row = next(i for i, s in enumerate(window.alignment.page_statuses) if s.status == "changed")
        item = window.diff_list.item(changed_row)
        assert item.background().color() != item.foreground().color()

        export_path = tmp_dir / "gui_sample_report.xlsx"
        from ymb_pdf_diff.report import build_excel_report

        build_excel_report(window.pdf_a_path, window.pdf_b_path, window.pages_a, window.pages_b, window.alignment, str(export_path))
        assert export_path.exists()
        export_path.unlink()

        # セッション保存→読込→キャプチャ表示まで(ファイルダイアログを介さず直接関数呼び出しで検証)
        from ymb_pdf_diff.session import load_session, save_session

        session_path = tmp_dir / "gui_sample_session.ymbdiff"
        save_session(str(session_path), window.pdf_a_path, window.pdf_b_path, window.pages_a, window.pages_b, window.alignment)
        assert session_path.exists()

        window._loaded_session = load_session(str(session_path))
        window.alignment = type(window.alignment)(window._loaded_session.page_statuses())
        window._populate_diff_list()
        for row in range(window.diff_list.count()):
            window.diff_list.setCurrentRow(row)
        session_path.unlink()

        window.close()
        print("OK: test_compare_and_render_smoke")
    finally:
        path_a.unlink(missing_ok=True)
        path_b.unlink(missing_ok=True)


if __name__ == "__main__":
    test_compare_and_render_smoke()
