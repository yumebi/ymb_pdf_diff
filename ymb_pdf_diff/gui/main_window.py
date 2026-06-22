from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSplitter,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ..core import (
    AlignmentResult,
    OcrUnavailableError,
    PageLine,
    PageStatus,
    align_documents,
    detect_visual_only_changes,
    diff_page_lines,
    diff_page_pair,
    draw_highlights,
    load_pdf_pages,
    render_page,
)
from .. import __version__
from ..assets import asset_path
from ..report import build_excel_report
from ..session import LoadedSession, load_session, save_session
from ..update_check import check_for_update
from .color_settings_dialog import ColorSettingsDialog
from .diff_colors import DiffColors
from .image_view import ImageView
from .window_state import save_window_geometry, restore_window_geometry

_STATUS_LABEL = {
    "unchanged": "差分なし",
    "changed": "差分あり",
    "inserted": "追加(Bのみ)",
    "deleted": "削除(Aのみ)",
}
_STATUS_TO_COLOR_KEY = {"changed": "changed", "inserted": "inserted", "deleted": "deleted"}
_TEXT_KIND_LABEL = {"replace": "変更", "insert": "追加", "delete": "削除"}
_KIND_TO_COLOR_KEY = {"replace": "changed", "insert": "inserted", "delete": "deleted"}

_BUTTON_STYLE = """
QPushButton {
    background-color: #D7E3F4;
    border: 1px solid #7E96B8;
    border-radius: 4px;
    padding: 4px 12px;
    margin: 3px;
    color: #15233D;
}
QPushButton:hover {
    background-color: #BFD3EE;
    border-color: #4C7BC2;
}
QPushButton:pressed {
    background-color: #9FBBE0;
}
QPushButton:checked {
    background-color: #6FA0DD;
    border-color: #2E5FA0;
}
QPushButton:disabled {
    background-color: #E0E0E0;
    border-color: #C0C0C0;
    color: #909090;
}
"""


def _pil_to_pixmap(img) -> QPixmap:
    rgb = img.convert("RGB")
    data = rgb.tobytes("raw", "RGB")
    qimg = QImage(data, rgb.width, rgb.height, rgb.width * 3, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimg.copy())


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"YMB PDF差分抽出ツール v{__version__}")
        self.resize(1400, 900)
        icon_path = asset_path("icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.pdf_a_path: Optional[str] = None
        self.pdf_b_path: Optional[str] = None
        self.pages_a: List[List[PageLine]] = []
        self.pages_b: List[List[PageLine]] = []
        self.alignment: Optional[AlignmentResult] = None
        self._loaded_session: Optional[LoadedSession] = None
        self.diff_colors = DiffColors()
        self.show_highlights = True

        self._build_ui()
        restore_window_geometry(self)
        QTimer.singleShot(500, self._check_for_update)

    def _build_ui(self) -> None:
        self.setStyleSheet(_BUTTON_STYLE)

        toolbar = QToolBar()
        self.addToolBar(toolbar)

        self.btn_select_a = QPushButton("ファイルA選択")
        self.btn_select_a.clicked.connect(self._select_a)

        self.btn_select_b = QPushButton("ファイルB選択")
        self.btn_select_b.clicked.connect(self._select_b)

        self.btn_compare = QPushButton("比較実行")
        self.btn_compare.clicked.connect(self._run_compare)
        toolbar.addWidget(self.btn_compare)

        self.btn_export = QPushButton("Excel出力")
        self.btn_export.clicked.connect(self._export_excel)
        self.btn_export.setEnabled(False)
        toolbar.addWidget(self.btn_export)

        self.btn_save_session = QPushButton("セッション保存")
        self.btn_save_session.clicked.connect(self._save_session)
        self.btn_save_session.setEnabled(False)
        toolbar.addWidget(self.btn_save_session)

        self.btn_load_session = QPushButton("セッション読込")
        self.btn_load_session.clicked.connect(self._load_session_dialog)
        toolbar.addWidget(self.btn_load_session)

        toolbar.addSeparator()

        self.btn_zoom_out = QPushButton("縮小 -")
        self.btn_zoom_out.clicked.connect(lambda: self._apply_zoom(self.view_a.zoom() / 1.2))
        toolbar.addWidget(self.btn_zoom_out)

        self.btn_zoom_reset = QPushButton("100%")
        self.btn_zoom_reset.clicked.connect(lambda: self._apply_zoom(1.0))
        toolbar.addWidget(self.btn_zoom_reset)

        self.btn_zoom_in = QPushButton("拡大 +")
        self.btn_zoom_in.clicked.connect(lambda: self._apply_zoom(self.view_a.zoom() * 1.2))
        toolbar.addWidget(self.btn_zoom_in)

        self.btn_toggle_highlight = QPushButton("差分枠: ON")
        self.btn_toggle_highlight.setCheckable(True)
        self.btn_toggle_highlight.setChecked(True)
        self.btn_toggle_highlight.clicked.connect(self._toggle_highlight)
        toolbar.addWidget(self.btn_toggle_highlight)

        self.btn_color_settings = QPushButton("表示設定")
        self.btn_color_settings.clicked.connect(self._open_color_settings)
        toolbar.addWidget(self.btn_color_settings)

        self.summary_label = QLabel("PDFファイルA・Bを選択して「比較実行」を押してください。")

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(self.summary_label)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.diff_list = QListWidget()
        self.diff_list.setMinimumWidth(220)
        self.diff_list.setMaximumWidth(320)
        self.diff_list.currentRowChanged.connect(self._on_select_row)
        splitter.addWidget(self.diff_list)

        self.view_a = ImageView()
        self.view_a.set_placeholder("ファイルA")
        panel_a = QWidget()
        layout_a = QVBoxLayout(panel_a)
        layout_a.setContentsMargins(0, 0, 0, 0)
        layout_a.addWidget(self.btn_select_a)
        layout_a.addWidget(self.view_a)
        splitter.addWidget(panel_a)

        self.view_b = ImageView()
        self.view_b.set_placeholder("ファイルB")
        panel_b = QWidget()
        layout_b = QVBoxLayout(panel_b)
        layout_b.setContentsMargins(0, 0, 0, 0)
        layout_b.addWidget(self.btn_select_b)
        layout_b.addWidget(self.view_b)
        splitter.addWidget(panel_b)

        # ズーム・スクロールをA/B間で連動させる(emit=Falseで無限ループを防止)
        self.view_a.zoomed.connect(lambda factor: self.view_b.set_zoom(factor, emit=False))
        self.view_b.zoomed.connect(lambda factor: self.view_a.set_zoom(factor, emit=False))
        self.view_a.horizontalScrollBar().valueChanged.connect(self.view_b.horizontalScrollBar().setValue)
        self.view_b.horizontalScrollBar().valueChanged.connect(self.view_a.horizontalScrollBar().setValue)
        self.view_a.verticalScrollBar().valueChanged.connect(self.view_b.verticalScrollBar().setValue)
        self.view_b.verticalScrollBar().valueChanged.connect(self.view_a.verticalScrollBar().setValue)

        splitter.setSizes([240, 580, 580])
        layout.addWidget(splitter, stretch=1)

        self.text_diff_view = QTextEdit()
        self.text_diff_view.setReadOnly(True)
        self.text_diff_view.setMaximumHeight(220)
        layout.addWidget(self.text_diff_view)

        self.setCentralWidget(central)
        self.statusBar().showMessage("準備完了")

        self.update_label = QLabel("")
        self.update_label.setOpenExternalLinks(True)
        self.statusBar().addPermanentWidget(self.update_label)

    def closeEvent(self, event) -> None:
        save_window_geometry(self)
        super().closeEvent(event)

    def _check_for_update(self) -> None:
        info = check_for_update(__version__)
        if info is None:
            return
        self.update_label.setText(f'<a href="{info.download_url}">新しいバージョン v{info.latest_version} があります</a>')

    def _apply_zoom(self, factor: float) -> None:
        self.view_a.set_zoom(factor, emit=False)
        self.view_b.set_zoom(factor, emit=False)

    def _toggle_highlight(self) -> None:
        self.show_highlights = self.btn_toggle_highlight.isChecked()
        self.btn_toggle_highlight.setText(f"差分枠: {'ON' if self.show_highlights else 'OFF'}")
        row = self.diff_list.currentRow()
        if row >= 0:
            self._on_select_row(row)

    def _open_color_settings(self) -> None:
        dialog = ColorSettingsDialog(self.diff_colors, self)
        if dialog.exec():
            row = self.diff_list.currentRow()
            self._populate_diff_list()
            if row >= 0:
                self.diff_list.setCurrentRow(row)

    def _select_a(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "ファイルAを選択", "", "PDF Files (*.pdf)")
        if path:
            self.pdf_a_path = path
            self.btn_select_a.setText(f"✓ A: {Path(path).name}")
            self.view_a.set_placeholder("ファイルA\n✔ 読み込み完了")

    def _select_b(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "ファイルBを選択", "", "PDF Files (*.pdf)")
        if path:
            self.pdf_b_path = path
            self.btn_select_b.setText(f"✓ B: {Path(path).name}")
            self.view_b.set_placeholder("ファイルB\n✔ 読み込み完了")

    def _run_compare(self) -> None:
        if not self.pdf_a_path or not self.pdf_b_path:
            QMessageBox.warning(self, "確認", "ファイルA・Bを両方選択してください。")
            return

        self._loaded_session = None

        progress_dialog = QProgressDialog("PDFを読み込み中...", None, 0, 100, self)
        progress_dialog.setWindowTitle("比較実行中")
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setMinimumDuration(0)
        progress_dialog.setValue(0)
        progress_dialog.show()
        QApplication.processEvents()

        def progress(file_label: str, base: int, span: int):
            def callback(current: int, total: int) -> None:
                progress_dialog.setLabelText(f"読込中({file_label}): {current}/{total}ページ(OCR含む)")
                progress_dialog.setValue(base + int(span * current / max(total, 1)))
                self.statusBar().showMessage(f"読込中({file_label}): {current}/{total}ページ(OCR含む)")
                QApplication.processEvents()

            return callback

        try:
            self.pages_a = load_pdf_pages(self.pdf_a_path, progress_callback=progress("ファイルA", 0, 35))
            self.pages_b = load_pdf_pages(self.pdf_b_path, progress_callback=progress("ファイルB", 35, 35))
        except OcrUnavailableError as exc:
            progress_dialog.close()
            QMessageBox.critical(self, "OCRエラー", str(exc))
            self.statusBar().showMessage("比較失敗(OCR利用不可)")
            return

        progress_dialog.setLabelText("ページを整列中...")
        progress_dialog.setValue(72)
        QApplication.processEvents()
        self.alignment = align_documents(self.pages_a, self.pages_b)

        def image_progress(current: int, total: int) -> None:
            progress_dialog.setLabelText(f"見た目(画像)の差分を確認中: {current}/{total}ページ")
            progress_dialog.setValue(75 + int(23 * current / max(total, 1)))
            QApplication.processEvents()

        detect_visual_only_changes(self.alignment, self.pdf_a_path, self.pdf_b_path, progress_callback=image_progress)
        progress_dialog.setValue(100)
        progress_dialog.close()

        self._populate_diff_list()
        self.btn_export.setEnabled(True)
        self.btn_save_session.setEnabled(True)

        changed = len(self.alignment.changed_pages())
        self.summary_label.setText(
            f"A: {Path(self.pdf_a_path).name}({len(self.pages_a)}ページ)  /  "
            f"B: {Path(self.pdf_b_path).name}({len(self.pages_b)}ページ)　差分: {changed}件"
        )
        self.statusBar().showMessage(f"比較完了: 差分{changed}件")

        if self.alignment.page_statuses:
            self.diff_list.setCurrentRow(0)

    def _populate_diff_list(self) -> None:
        self.diff_list.clear()
        if self.alignment is None:
            return
        for status in self.alignment.page_statuses:
            a_disp = status.a_page + 1 if status.a_page is not None else "-"
            b_disp = status.b_page + 1 if status.b_page is not None else "-"
            moved_tag = "(ページ移動)" if status.moved else ""
            visual_tag = "(見た目のみ)" if status.visual_only else ""
            text = f"A{a_disp} ↔ B{b_disp}  [{_STATUS_LABEL[status.status]}]{moved_tag}{visual_tag}"
            item = QListWidgetItem(text)
            color_key = _STATUS_TO_COLOR_KEY.get(status.status)
            if color_key is not None:
                item.setBackground(QColor(self.diff_colors.get(f"{color_key}_bg")))
                item.setForeground(QColor(self.diff_colors.get(f"{color_key}_fg")))
            self.diff_list.addItem(item)

    def _on_select_row(self, row: int) -> None:
        if self.alignment is None or row < 0 or row >= len(self.alignment.page_statuses):
            return
        status = self.alignment.page_statuses[row]
        self._render_page_pair(status, row)
        self._render_text_diff(status, row)

    def _render_page_pair(self, status: PageStatus, idx: int) -> None:
        if self._loaded_session is not None:
            img_a = self._loaded_session.capture_image(idx, "a")
            img_b = self._loaded_session.capture_image(idx, "b")
            if img_a is not None:
                self.view_a.set_pixmap(_pil_to_pixmap(img_a))
            else:
                self.view_a.set_placeholder("(このページのキャプチャは保存されていません)")
            if img_b is not None:
                self.view_b.set_pixmap(_pil_to_pixmap(img_b))
            else:
                self.view_b.set_placeholder("(このページのキャプチャは保存されていません)")
            return

        regions: list = []
        if status.status == "changed" and status.a_page is not None and status.b_page is not None:
            img_result = diff_page_pair(self.pdf_a_path, status.a_page, self.pdf_b_path, status.b_page)
            regions = img_result.regions

        if status.a_page is not None:
            img_a = render_page(self.pdf_a_path, status.a_page)
            if regions and self.show_highlights:
                img_a = draw_highlights(img_a, regions, color=self.diff_colors.get("highlight"))
            self.view_a.set_pixmap(_pil_to_pixmap(img_a))
        else:
            self.view_a.set_placeholder("(このページはファイルAに存在しません)")

        if status.b_page is not None:
            img_b = render_page(self.pdf_b_path, status.b_page)
            if regions and self.show_highlights:
                img_b = draw_highlights(img_b, regions, color=self.diff_colors.get("highlight"))
            self.view_b.set_pixmap(_pil_to_pixmap(img_b))
        else:
            self.view_b.set_placeholder("(このページはファイルBに存在しません)")

    def _render_text_diff(self, status: PageStatus, idx: int) -> None:
        if status.status != "changed" or status.a_page is None or status.b_page is None:
            self.text_diff_view.setHtml("<i>このページのテキスト差分はありません。</i>")
            return

        if self._loaded_session is not None:
            entries = self._loaded_session.text_diff_for(idx)
        else:
            entries = diff_page_lines(self.pages_a[status.a_page], self.pages_b[status.b_page])
        html_parts = []
        for entry in entries:
            before = "<br>".join(entry.before) or "(なし)"
            after = "<br>".join(entry.after) or "(なし)"
            color_key = _KIND_TO_COLOR_KEY[entry.kind]
            bg = self.diff_colors.get(f"{color_key}_bg")
            fg = self.diff_colors.get(f"{color_key}_fg")
            html_parts.append(
                f'<div style="background:{bg};color:{fg};padding:4px;margin:2px 0;">'
                f"<b>[{_TEXT_KIND_LABEL[entry.kind]}]</b> 変更前: {before} / 変更後: {after}</div>"
            )
        if not html_parts and status.visual_only:
            self.text_diff_view.setHtml("<i>テキストは同一です。画像(見た目)のみ差分があります。</i>")
        else:
            self.text_diff_view.setHtml("".join(html_parts) or "<i>差分なし</i>")

    def _make_progress_dialog(self, title: str, label: str) -> QProgressDialog:
        dialog = QProgressDialog(label, None, 0, 100, self)
        dialog.setWindowTitle(title)
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        dialog.setMinimumDuration(0)
        dialog.setValue(0)
        dialog.show()
        QApplication.processEvents()
        return dialog

    def _export_excel(self) -> None:
        if self.alignment is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Excelレポートを保存", "diff_report.xlsx", "Excel Files (*.xlsx)")
        if not path:
            return

        progress_dialog = self._make_progress_dialog("Excel出力中", "Excelレポートを作成中...")

        def progress(current: int, total: int) -> None:
            progress_dialog.setValue(int(100 * current / max(total, 1)))
            QApplication.processEvents()

        try:
            build_excel_report(
                self.pdf_a_path, self.pdf_b_path, self.pages_a, self.pages_b, self.alignment, path,
                progress_callback=progress,
            )
        except Exception as exc:  # noqa: BLE001 - ユーザーに失敗内容を見せるため捕捉
            progress_dialog.close()
            QMessageBox.critical(self, "エラー", f"Excel出力に失敗しました: {exc}")
            return
        progress_dialog.close()
        self.statusBar().showMessage(f"Excel出力完了: {path}")

    def _save_session(self) -> None:
        if self.alignment is None or self._loaded_session is not None:
            QMessageBox.warning(self, "確認", "保存するには先に比較を実行してください。")
            return
        path, _ = QFileDialog.getSaveFileName(self, "セッションを保存", "diff_session.ymbdiff", "YMB PDF DIFF Session (*.ymbdiff)")
        if not path:
            return

        progress_dialog = self._make_progress_dialog("セッション保存中", "セッションを保存中...")

        def progress(current: int, total: int) -> None:
            progress_dialog.setValue(int(100 * current / max(total, 1)))
            QApplication.processEvents()

        try:
            save_session(
                path, self.pdf_a_path, self.pdf_b_path, self.pages_a, self.pages_b, self.alignment,
                progress_callback=progress,
            )
        except Exception as exc:  # noqa: BLE001 - ユーザーに失敗内容を見せるため捕捉
            progress_dialog.close()
            QMessageBox.critical(self, "エラー", f"セッション保存に失敗しました: {exc}")
            return
        progress_dialog.close()
        self.statusBar().showMessage(f"セッション保存完了: {path}")

    def _load_session_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "セッションを開く", "", "YMB PDF DIFF Session (*.ymbdiff)")
        if not path:
            return
        try:
            loaded = load_session(path)
        except Exception as exc:  # noqa: BLE001 - ユーザーに失敗内容を見せるため捕捉
            QMessageBox.critical(self, "エラー", f"セッション読込に失敗しました: {exc}")
            return

        self._loaded_session = loaded
        self.pdf_a_path = loaded.meta.get("pdf_a_path")
        self.pdf_b_path = loaded.meta.get("pdf_b_path")
        self.pages_a = []
        self.pages_b = []
        self.alignment = AlignmentResult(loaded.page_statuses())
        self._populate_diff_list()
        self.btn_export.setEnabled(False)
        self.btn_save_session.setEnabled(False)

        changed = len(self.alignment.changed_pages())
        self.summary_label.setText(f"[保存済みセッションを表示中] 差分: {changed}件 (元PDFなしで表示)")
        self.statusBar().showMessage(f"セッション読込完了: {path}")
        if self.alignment.page_statuses:
            self.diff_list.setCurrentRow(0)
