"""GUIがクラッシュせず比較〜表示〜Excel出力まで一通り動くことを確認するスモークテスト。
画面なし環境でも実行できるようQT_QPA_PLATFORM=offscreenを使う。
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fitz
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QSplitter

from ymb_pdf_diff.gui import MainWindow
from ymb_pdf_diff.gui.main_window import _SELECTION_MARKER


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

        # ピクセルマップの拡大縮小がスムーズ変換になっているか(#UI改善: ズーム時のジャギー対策)
        assert window.view_a._pixmap_item.transformationMode() == Qt.TransformationMode.SmoothTransformation
        assert window.view_b._pixmap_item.transformationMode() == Qt.TransformationMode.SmoothTransformation

        # 下部テキスト差分パネルがドラッグでリサイズ可能になっているか(#UI改善: 高さ固定の解除)
        central = window.centralWidget()
        assert isinstance(central, QSplitter)
        assert central.orientation() == Qt.Orientation.Vertical
        assert window.text_diff_view.maximumHeight() > 220

        window._run_compare(sync=True)
        assert window.alignment is not None
        assert window.diff_list.count() == len(window.alignment.page_statuses)
        assert window.btn_export.isEnabled()

        # 選択行マーカー(#UI改善: 選択行の視認性向上): 行を切り替えるたびに
        # マーカーが1件だけ付与され、currentRowと一致していることを確認する
        def _marked_rows():
            return [i for i in range(window.diff_list.count()) if window.diff_list.item(i).text().startswith(_SELECTION_MARKER)]

        for row in range(window.diff_list.count()):
            window.diff_list.setCurrentRow(row)
            marked = _marked_rows()
            assert marked == [row], f"row={row} marked={marked}"
            assert window._current_marker_row == row

        # 前の差分/次の差分ジャンプ(#新機能2): 差分ありなのでボタンが有効化され、
        # 「次の差分」で最初のchanged行へ移動できる
        assert window.btn_next_diff.isEnabled()
        assert window.btn_prev_diff.isEnabled()
        window.diff_list.setCurrentRow(0)
        window._jump_next_diff()
        current = window.diff_list.currentRow()
        assert window.alignment.page_statuses[current].status != "unchanged"

        # 最近使ったペア履歴(#新機能3): 比較成功後にQSettingsへ記録される
        from PySide6.QtCore import QSettings

        settings = QSettings("YMB", "YMB PDF DIFF")
        recorded = settings.value("recent/pairs", "")
        assert recorded
        import json as _json

        recent_pairs = _json.loads(recorded)
        assert [str(path_a), str(path_b)] in recent_pairs

        for row in range(window.diff_list.count()):
            window.diff_list.setCurrentRow(row)
            assert not window.view_a.current_pixmap().isNull() or window.alignment.page_statuses[row].a_page is None

        # ドラッグ&ドロップ配線(#新機能1): file_droppedシグナルのハンドラを直接叩いて確認
        window._on_drop_a(str(path_a))
        assert window.pdf_a_path == str(path_a)
        # ドロップ直後はプレースホルダー表示になるため、再描画してpixmapを戻しておく
        window._on_select_row(window.diff_list.currentRow())

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

        # 重ね表示モード切替(#新機能6): 差分ありの行で重ね表示ONにしてもクラッシュせず、
        # 左ペインにピクセルマップが表示されることを確認する
        window.diff_list.setCurrentRow(changed_row)
        assert window.btn_toggle_overlay.isEnabled()
        window.btn_toggle_overlay.setChecked(True)
        window._toggle_overlay()
        assert window.overlay_mode is True
        assert not window.view_a.current_pixmap().isNull()
        window.btn_toggle_overlay.setChecked(False)
        window._toggle_overlay()
        assert window.overlay_mode is False

        # 画像差分感度設定(#新機能7): QSettings経由での往復を確認する
        from ymb_pdf_diff.gui.diff_settings import DEFAULT_THRESHOLD, get_threshold, set_threshold

        original_threshold = get_threshold()
        set_threshold(15)
        assert get_threshold() == 15
        set_threshold(original_threshold if original_threshold != 15 else DEFAULT_THRESHOLD)

        export_path = tmp_dir / "gui_sample_report.xlsx"
        from ymb_pdf_diff.report import build_excel_report

        build_excel_report(window.pdf_a_path, window.pdf_b_path, window.pages_a, window.pages_b, window.alignment, str(export_path))
        assert export_path.exists()
        export_path.unlink()

        # PDFレポート出力(#新機能10): btn_export_pdfが比較成功後に有効化され、
        # build_pdf_reportが正常に動くことを確認する(ファイルダイアログを介さず直接関数呼び出しで検証)
        assert window.btn_export_pdf.isEnabled()
        pdf_export_path = tmp_dir / "gui_sample_report.pdf"
        from ymb_pdf_diff.report import build_pdf_report

        build_pdf_report(window.pdf_a_path, window.pdf_b_path, window.pages_a, window.pages_b, window.alignment, str(pdf_export_path))
        assert pdf_export_path.exists()
        pdf_export_path.unlink()

        # ページ範囲指定(#新機能8): ダイアログでの往復と、範囲を絞った再比較が正常に動くことを確認する
        from ymb_pdf_diff.gui.page_range_dialog import PageRangeDialog

        range_dialog = PageRangeDialog(window.page_range_a, window.page_range_b)
        assert range_dialog.result_ranges() == (None, None)
        range_dialog.deleteLater()

        window.page_range_a = "1"
        window.page_range_b = "1"
        window._run_compare(sync=True)
        assert window.alignment is not None
        assert all(s.a_page in (0, None) for s in window.alignment.page_statuses)
        assert "A:1" in window.summary_label.text()
        window.page_range_a = None
        window.page_range_b = None

        # ページ範囲の書式・範囲外エラーはValueErrorとして送出される(QMessageBox表示部分は
        # モーダルダイアログとなるためオフスクリーンテストでは検証せず、tests/test_page_range.pyで確認済み)。

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
