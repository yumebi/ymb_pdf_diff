import html
import json
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from PySide6.QtCore import QSettings, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QImage, QKeySequence, QPixmap, QShortcut
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
    align_documents_in_range,
    char_diff_segments,
    detect_visual_only_changes,
    diff_page_lines,
    diff_page_pair,
    draw_highlights,
    load_pdf_pages,
    overlay_images,
    pad_to_same_size,
    parse_page_range,
    render_page,
)
from .. import __version__
from ..assets import asset_path
from ..report import build_excel_report, build_pdf_report
from ..session import LoadedSession, load_session, save_session
from ..update_check import check_for_update
from .color_settings_dialog import ColorSettingsDialog
from .diff_colors import DiffColors
from .diff_settings import get_image_size, get_threshold
from .image_view import ImageView
from .page_range_dialog import PageRangeDialog
from .window_state import save_window_geometry, restore_window_geometry

_ORG_NAME = "YMB"
_APP_NAME = "YMB PDF DIFF"
_RECENT_PAIRS_KEY = "recent/pairs"
_RECENT_PAIRS_MAX = 5

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


def _darken_hex(hex_color: str, factor: float = 0.75) -> str:
    """行内文字差分(#新機能5)で、変更箇所の背景を元の背景色より少し濃くするための補助関数。"""
    color = QColor(hex_color)
    r = max(0, int(color.red() * factor))
    g = max(0, int(color.green() * factor))
    b = max(0, int(color.blue() * factor))
    return QColor(r, g, b).name()


class _CompareCancelled(Exception):
    """比較処理がユーザーによりキャンセルされたことを表す内部例外。"""


def _do_compare_work(
    pdf_a_path: str,
    pdf_b_path: str,
    progress_cb: Callable[[str, int], None],
    is_cancelled: Callable[[], bool],
    threshold: int = 30,
    range_a: Optional[str] = None,
    range_b: Optional[str] = None,
) -> Tuple[List[List[PageLine]], List[List[PageLine]], AlignmentResult]:
    """PDF読み込み〜ページ整列〜画像差分検出までの重い処理本体。

    同期実行(テスト用)・バックグラウンドスレッド実行のどちらからも呼び出せるよう、
    GUI操作を含まない純粋な処理として切り出している。
    progress_cb(label, value) は進捗更新のたびに呼ばれる(value は0-100)。
    is_cancelled() がTrueを返した時点で_CompareCancelledを送出して処理を中断する。
    threshold(#新機能7)は画像差分の感度(0-100、小さいほど敏感)。表示設定ダイアログの
    値がGUI側から渡される。
    range_a/range_b(#新機能8)は「1-5,8」形式のページ範囲指定。Noneまたは空文字は
    該当ファイルの全ページを対象にする。書式・範囲外エラーはValueErrorとして送出される。
    """

    def make_load_progress(file_label: str, base: int, span: int):
        def callback(current: int, total: int) -> None:
            if is_cancelled():
                raise _CompareCancelled()
            progress_cb(
                f"読込中({file_label}): {current}/{total}ページ(OCR含む)",
                base + int(span * current / max(total, 1)),
            )

        return callback

    pages_a = load_pdf_pages(pdf_a_path, progress_callback=make_load_progress("ファイルA", 0, 35))
    pages_b = load_pdf_pages(pdf_b_path, progress_callback=make_load_progress("ファイルB", 35, 35))

    if is_cancelled():
        raise _CompareCancelled()
    progress_cb("ページを整列中...", 72)

    if range_a or range_b:
        indices_a = parse_page_range(range_a, len(pages_a)) if range_a else list(range(len(pages_a)))
        indices_b = parse_page_range(range_b, len(pages_b)) if range_b else list(range(len(pages_b)))
        alignment = align_documents_in_range(pages_a, pages_b, indices_a, indices_b)
    else:
        alignment = align_documents(pages_a, pages_b)

    def image_progress(current: int, total: int) -> None:
        if is_cancelled():
            raise _CompareCancelled()
        progress_cb(
            f"見た目(画像)の差分を確認中: {current}/{total}ページ",
            75 + int(23 * current / max(total, 1)),
        )

    detect_visual_only_changes(
        alignment, pdf_a_path, pdf_b_path, threshold=threshold, progress_callback=image_progress
    )
    if is_cancelled():
        raise _CompareCancelled()
    return pages_a, pages_b, alignment


class _CompareThread(QThread):
    """比較処理をバックグラウンドで実行するワーカースレッド。"""

    progress = Signal(str, int)
    finished_ok = Signal(object, object, object)
    failed = Signal(str)
    range_error = Signal(str)
    cancelled = Signal()

    def __init__(
        self,
        pdf_a_path: str,
        pdf_b_path: str,
        threshold: int = 30,
        range_a: Optional[str] = None,
        range_b: Optional[str] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._pdf_a_path = pdf_a_path
        self._pdf_b_path = pdf_b_path
        self._threshold = threshold
        self._range_a = range_a
        self._range_b = range_b
        self._cancel_requested = False

    def request_cancel(self) -> None:
        self._cancel_requested = True

    def run(self) -> None:  # noqa: D401 - QThreadのオーバーライド
        try:
            pages_a, pages_b, alignment = _do_compare_work(
                self._pdf_a_path,
                self._pdf_b_path,
                lambda text, value: self.progress.emit(text, value),
                lambda: self._cancel_requested,
                threshold=self._threshold,
                range_a=self._range_a,
                range_b=self._range_b,
            )
        except _CompareCancelled:
            self.cancelled.emit()
            return
        except OcrUnavailableError as exc:
            self.failed.emit(str(exc))
            return
        except ValueError as exc:
            # ページ範囲(#新機能8)の書式・範囲外エラー
            self.range_error.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 - GUI側にエラー内容を伝えるため捕捉
            self.failed.emit(str(exc))
            return
        self.finished_ok.emit(pages_a, pages_b, alignment)


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
        self.page_range_a: Optional[str] = None
        self.page_range_b: Optional[str] = None
        self._loaded_session: Optional[LoadedSession] = None
        self.diff_colors = DiffColors()
        self.show_highlights = True
        self.overlay_mode = False
        self._compare_thread: Optional[_CompareThread] = None
        self._compare_progress: Optional[QProgressDialog] = None

        self._build_menu()
        self._build_ui()
        restore_window_geometry(self)
        QTimer.singleShot(500, self._check_for_update)

    def _build_menu(self) -> None:
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("ファイル(&F)")
        self.recent_pairs_menu = file_menu.addMenu("最近使ったペア")
        self.recent_pairs_menu.aboutToShow.connect(self._populate_recent_pairs_menu)

    def _build_ui(self) -> None:
        self.setStyleSheet(_BUTTON_STYLE)

        toolbar = QToolBar()
        self.addToolBar(toolbar)

        self.btn_select_a = QPushButton("ファイルA選択")
        self.btn_select_a.clicked.connect(self._select_a)

        self.btn_select_b = QPushButton("ファイルB選択")
        self.btn_select_b.clicked.connect(self._select_b)

        # ページ範囲指定(#新機能8): 比較対象を特定のページ範囲だけに絞り込む
        self.btn_page_range = QPushButton("ページ範囲…")
        self.btn_page_range.clicked.connect(self._open_page_range_dialog)
        toolbar.addWidget(self.btn_page_range)

        self.btn_compare = QPushButton("比較実行")
        self.btn_compare.clicked.connect(self._run_compare)
        toolbar.addWidget(self.btn_compare)

        self.btn_export = QPushButton("Excel出力")
        self.btn_export.clicked.connect(self._export_excel)
        self.btn_export.setEnabled(False)
        toolbar.addWidget(self.btn_export)

        # PDFレポート出力(#新機能10)
        self.btn_export_pdf = QPushButton("PDFレポート")
        self.btn_export_pdf.clicked.connect(self._export_pdf)
        self.btn_export_pdf.setEnabled(False)
        toolbar.addWidget(self.btn_export_pdf)

        self.btn_save_session = QPushButton("セッション保存")
        self.btn_save_session.clicked.connect(self._save_session)
        self.btn_save_session.setEnabled(False)
        toolbar.addWidget(self.btn_save_session)

        self.btn_load_session = QPushButton("セッション読込")
        self.btn_load_session.clicked.connect(self._load_session_dialog)
        toolbar.addWidget(self.btn_load_session)

        toolbar.addSeparator()

        self.btn_prev_diff = QPushButton("◀ 前の差分")
        self.btn_prev_diff.clicked.connect(self._jump_prev_diff)
        self.btn_prev_diff.setEnabled(False)
        toolbar.addWidget(self.btn_prev_diff)

        self.btn_next_diff = QPushButton("次の差分 ▶")
        self.btn_next_diff.clicked.connect(self._jump_next_diff)
        self.btn_next_diff.setEnabled(False)
        toolbar.addWidget(self.btn_next_diff)

        # F3/Shift+F3でも前後の差分へジャンプできるようにする
        self.shortcut_next_diff = QShortcut(QKeySequence("F3"), self)
        self.shortcut_next_diff.activated.connect(self._jump_next_diff)
        self.shortcut_prev_diff = QShortcut(QKeySequence("Shift+F3"), self)
        self.shortcut_prev_diff.activated.connect(self._jump_prev_diff)

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

        # 重ね表示モード(#新機能6): A/Bを1枚に重ねた合成画像を左ペインに表示する。
        # 比較未実行、または両ページが揃っていない行を選択中は無効化する。
        self.btn_toggle_overlay = QPushButton("重ね表示: OFF")
        self.btn_toggle_overlay.setCheckable(True)
        self.btn_toggle_overlay.setChecked(False)
        self.btn_toggle_overlay.setEnabled(False)
        self.btn_toggle_overlay.setToolTip("ファイルA・Bのページを重ねて左側に表示します(赤=ファイルAのみ / 青=ファイルBのみ / 黒=共通)")
        self.btn_toggle_overlay.clicked.connect(self._toggle_overlay)
        toolbar.addWidget(self.btn_toggle_overlay)

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
        self.view_a.file_dropped.connect(self._on_drop_a)
        panel_a = QWidget()
        layout_a = QVBoxLayout(panel_a)
        layout_a.setContentsMargins(0, 0, 0, 0)
        layout_a.addWidget(self.btn_select_a)
        layout_a.addWidget(self.view_a)
        splitter.addWidget(panel_a)

        self.view_b = ImageView()
        self.view_b.set_placeholder("ファイルB")
        self.view_b.file_dropped.connect(self._on_drop_b)
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

    def _toggle_overlay(self) -> None:
        self.overlay_mode = self.btn_toggle_overlay.isChecked()
        self.btn_toggle_overlay.setText(f"重ね表示: {'ON' if self.overlay_mode else 'OFF'}")
        row = self.diff_list.currentRow()
        if row >= 0:
            self._on_select_row(row)

    def _open_color_settings(self) -> None:
        previous_threshold = get_threshold()
        dialog = ColorSettingsDialog(self.diff_colors, self)
        if dialog.exec():
            row = self.diff_list.currentRow()
            self._populate_diff_list()
            if row >= 0:
                self.diff_list.setCurrentRow(row)
            if get_threshold() != previous_threshold:
                self.statusBar().showMessage("感度を変更しました。再度「比較実行」を押すと反映されます")

    def _open_page_range_dialog(self) -> None:
        """ページ範囲指定ダイアログ(#新機能8)を開く。実際の書式検証は比較実行時に行う。"""
        dialog = PageRangeDialog(self.page_range_a, self.page_range_b, self)
        if dialog.exec():
            self.page_range_a, self.page_range_b = dialog.result_ranges()

    def _format_range_note(self) -> str:
        """アクティブなページ範囲があればサマリー表示に付け足す文字列を返す。"""
        if not self.page_range_a and not self.page_range_b:
            return ""
        a_text = self.page_range_a or "全ページ"
        b_text = self.page_range_b or "全ページ"
        return f"　(A:{a_text} / B:{b_text})"

    def _select_a(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "ファイルAを選択", "", "PDF Files (*.pdf)")
        if path:
            self._set_pdf_a(path)

    def _select_b(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "ファイルBを選択", "", "PDF Files (*.pdf)")
        if path:
            self._set_pdf_b(path)

    def _set_pdf_a(self, path: str) -> None:
        self.pdf_a_path = path
        self.btn_select_a.setText(f"✓ A: {Path(path).name}")
        self.view_a.set_placeholder("ファイルA\n✔ 読み込み完了")

    def _set_pdf_b(self, path: str) -> None:
        self.pdf_b_path = path
        self.btn_select_b.setText(f"✓ B: {Path(path).name}")
        self.view_b.set_placeholder("ファイルB\n✔ 読み込み完了")

    def _on_drop_a(self, path: str) -> None:
        """view_aへのPDFドラッグ&ドロップ受け取り(ファイルA選択と同等)。"""
        self._set_pdf_a(path)

    def _on_drop_b(self, path: str) -> None:
        """view_bへのPDFドラッグ&ドロップ受け取り(ファイルB選択と同等)。"""
        self._set_pdf_b(path)

    def _jump_prev_diff(self) -> None:
        self._jump_diff(-1)

    def _jump_next_diff(self) -> None:
        self._jump_diff(1)

    def _jump_diff(self, direction: int) -> None:
        """変更のある行(status != "unchanged")だけを対象に、前後の行へ循環移動する。"""
        if self.alignment is None or not self.alignment.page_statuses:
            return
        count = len(self.alignment.page_statuses)
        current = self.diff_list.currentRow()
        for step in range(1, count + 1):
            idx = (current + direction * step) % count
            if self.alignment.page_statuses[idx].status != "unchanged":
                self.diff_list.setCurrentRow(idx)
                return

    def _update_jump_buttons_enabled(self) -> None:
        has_changes = self.alignment is not None and any(
            s.status != "unchanged" for s in self.alignment.page_statuses
        )
        self.btn_prev_diff.setEnabled(has_changes)
        self.btn_next_diff.setEnabled(has_changes)

    def _load_recent_pairs(self) -> List[Tuple[str, str]]:
        settings = QSettings(_ORG_NAME, _APP_NAME)
        raw = settings.value(_RECENT_PAIRS_KEY, "")
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            return []
        pairs: List[Tuple[str, str]] = []
        for item in data:
            if isinstance(item, list) and len(item) == 2:
                pairs.append((item[0], item[1]))
        return pairs

    def _record_recent_pair(self, a_path: str, b_path: str) -> None:
        settings = QSettings(_ORG_NAME, _APP_NAME)
        pairs = [p for p in self._load_recent_pairs() if p != (a_path, b_path)]
        pairs.insert(0, (a_path, b_path))
        pairs = pairs[:_RECENT_PAIRS_MAX]
        settings.setValue(_RECENT_PAIRS_KEY, json.dumps([list(p) for p in pairs]))

    def _populate_recent_pairs_menu(self) -> None:
        self.recent_pairs_menu.clear()
        pairs = self._load_recent_pairs()
        if not pairs:
            action = self.recent_pairs_menu.addAction("(履歴なし)")
            action.setEnabled(False)
            return
        for a_path, b_path in pairs:
            label = f"{Path(a_path).name} ⇔ {Path(b_path).name}"
            action = self.recent_pairs_menu.addAction(label)
            tooltip = f"A: {a_path}\nB: {b_path}"
            action.setToolTip(tooltip)
            action.setStatusTip(tooltip)
            # 元ファイルが存在しない履歴は選択できないようグレーアウトする(一覧からは消さない)
            exists = Path(a_path).exists() and Path(b_path).exists()
            action.setEnabled(exists)
            if exists:
                action.triggered.connect(
                    lambda checked=False, a=a_path, b=b_path: self._open_recent_pair(a, b)
                )

    def _open_recent_pair(self, a_path: str, b_path: str) -> None:
        self._set_pdf_a(a_path)
        self._set_pdf_b(b_path)
        self._run_compare()

    def _run_compare(self, sync: bool = False) -> None:
        """比較を実行する。

        sync=Trueの場合はバックグラウンドスレッドを使わず、その場で同期的に処理する
        (テストなど、比較直後に結果を即座に検証したい場合向け)。
        通常のGUI操作(sync=False, デフォルト)ではQThreadで比較処理を実行し、
        UIがフリーズしないようにする。
        """
        if not self.pdf_a_path or not self.pdf_b_path:
            QMessageBox.warning(self, "確認", "ファイルA・Bを両方選択してください。")
            return

        self._loaded_session = None

        progress_dialog = QProgressDialog("PDFを読み込み中...", "キャンセル", 0, 100, self)
        progress_dialog.setWindowTitle("比較実行中")
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setMinimumDuration(0)
        progress_dialog.setValue(0)
        self._compare_progress = progress_dialog
        progress_dialog.show()
        QApplication.processEvents()

        threshold = get_threshold()

        if sync:
            self._run_compare_sync(progress_dialog, threshold)
            return

        progress_dialog.canceled.connect(self._on_compare_cancel_requested)

        thread = _CompareThread(
            self.pdf_a_path, self.pdf_b_path, threshold, self.page_range_a, self.page_range_b, self
        )
        thread.progress.connect(self._on_compare_progress)
        thread.finished_ok.connect(self._on_compare_finished)
        thread.failed.connect(self._on_compare_failed)
        thread.range_error.connect(self._on_compare_range_error)
        thread.cancelled.connect(self._on_compare_cancelled)
        self._compare_thread = thread
        thread.start()

    def _run_compare_sync(self, progress_dialog: QProgressDialog, threshold: int = 30) -> None:
        def progress_cb(text: str, value: int) -> None:
            progress_dialog.setLabelText(text)
            progress_dialog.setValue(value)
            self.statusBar().showMessage(text)
            QApplication.processEvents()

        try:
            pages_a, pages_b, alignment = _do_compare_work(
                self.pdf_a_path,
                self.pdf_b_path,
                progress_cb,
                lambda: False,
                threshold=threshold,
                range_a=self.page_range_a,
                range_b=self.page_range_b,
            )
        except OcrUnavailableError as exc:
            progress_dialog.close()
            QMessageBox.critical(self, "OCRエラー", str(exc))
            self.statusBar().showMessage("比較失敗(OCR利用不可)")
            return
        except ValueError as exc:
            progress_dialog.close()
            QMessageBox.warning(self, "ページ範囲エラー", str(exc))
            self.statusBar().showMessage("比較失敗(ページ範囲指定エラー)")
            return

        self.pages_a, self.pages_b, self.alignment = pages_a, pages_b, alignment
        progress_dialog.setValue(100)
        progress_dialog.close()
        self._on_compare_success()

    def _on_compare_progress(self, text: str, value: int) -> None:
        if self._compare_progress is None:
            return
        self._compare_progress.setLabelText(text)
        self._compare_progress.setValue(value)
        self.statusBar().showMessage(text)

    def _on_compare_cancel_requested(self) -> None:
        if self._compare_thread is not None:
            self._compare_thread.request_cancel()

    def _on_compare_finished(self, pages_a, pages_b, alignment) -> None:
        self.pages_a, self.pages_b, self.alignment = pages_a, pages_b, alignment
        if self._compare_progress is not None:
            self._compare_progress.setValue(100)
            self._compare_progress.close()
            self._compare_progress = None
        self._compare_thread = None
        self._on_compare_success()

    def _on_compare_failed(self, message: str) -> None:
        if self._compare_progress is not None:
            self._compare_progress.close()
            self._compare_progress = None
        self._compare_thread = None
        QMessageBox.critical(self, "OCRエラー", message)
        self.statusBar().showMessage("比較失敗(OCR利用不可)")

    def _on_compare_range_error(self, message: str) -> None:
        if self._compare_progress is not None:
            self._compare_progress.close()
            self._compare_progress = None
        self._compare_thread = None
        QMessageBox.warning(self, "ページ範囲エラー", message)
        self.statusBar().showMessage("比較失敗(ページ範囲指定エラー)")

    def _on_compare_cancelled(self) -> None:
        if self._compare_progress is not None:
            self._compare_progress.close()
            self._compare_progress = None
        self._compare_thread = None
        self.statusBar().showMessage("比較をキャンセルしました")

    def _on_compare_success(self) -> None:
        self._populate_diff_list()
        self.btn_export.setEnabled(True)
        self.btn_export_pdf.setEnabled(True)
        self.btn_save_session.setEnabled(True)
        self._update_jump_buttons_enabled()

        changed = len(self.alignment.changed_pages())
        self.summary_label.setText(
            f"A: {Path(self.pdf_a_path).name}({len(self.pages_a)}ページ)  /  "
            f"B: {Path(self.pdf_b_path).name}({len(self.pages_b)}ページ)　差分: {changed}件"
            f"{self._format_range_note()}"
        )
        self.statusBar().showMessage(f"比較完了: 差分{changed}件")

        if self.alignment.page_statuses:
            self.diff_list.setCurrentRow(0)

        self._record_recent_pair(self.pdf_a_path, self.pdf_b_path)

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
            # 保存済みセッションは元PDFを持たないため、重ね表示(#新機能6)は生成できない
            self.btn_toggle_overlay.setEnabled(False)
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

        both_pages = status.a_page is not None and status.b_page is not None
        self.btn_toggle_overlay.setEnabled(both_pages)

        regions: list = []
        if status.status == "changed" and both_pages:
            img_result = diff_page_pair(
                self.pdf_a_path, status.a_page, self.pdf_b_path, status.b_page, threshold=get_threshold()
            )
            regions = img_result.regions

        if self.overlay_mode and both_pages:
            # 重ね表示モード(#新機能6): 合成画像を左ペインのみに表示する
            raw_a = render_page(self.pdf_a_path, status.a_page)
            raw_b = render_page(self.pdf_b_path, status.b_page)
            raw_a, raw_b = pad_to_same_size(raw_a, raw_b)
            composite = overlay_images(raw_a, raw_b)
            if regions and self.show_highlights:
                composite = draw_highlights(composite, regions, color=self.diff_colors.get("highlight"))
            self.view_a.set_pixmap(_pil_to_pixmap(composite))
            self.view_b.set_placeholder("重ね表示中(左に表示)")
            return

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

    @staticmethod
    def _char_segments_to_html(segments, bg: str) -> str:
        """char_diff_segmentsの結果(#新機能5)をHTMLに変換する。

        差分箇所(kind="diff")は太字+下線+背景を少し濃くして目立たせ、
        一致箇所(kind="equal")はそのまま表示する。改行は<br>に変換する。
        """
        darker_bg = _darken_hex(bg)
        parts = []
        for kind, text in segments:
            escaped = html.escape(text).replace("\n", "<br>")
            if kind == "diff":
                parts.append(f'<span style="background:{darker_bg};font-weight:bold;text-decoration:underline;">{escaped}</span>')
            else:
                parts.append(f"<span>{escaped}</span>")
        return "".join(parts)

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
            color_key = _KIND_TO_COLOR_KEY[entry.kind]
            bg = self.diff_colors.get(f"{color_key}_bg")
            fg = self.diff_colors.get(f"{color_key}_fg")
            if entry.kind == "replace":
                # 行内文字差分(#新機能5): "replace"行は変更前後を文字単位で比較し、
                # 変わった箇所だけ強調表示する(太字+下線+背景を少し濃く)。
                # Excelレポート側はopenpyxlで文字単位のリッチテキストが困難なため未対応(GUIのみ)。
                before_text = "\n".join(entry.before)
                after_text = "\n".join(entry.after)
                segs_before, segs_after = char_diff_segments(before_text, after_text)
                before = self._char_segments_to_html(segs_before, bg) or "(なし)"
                after = self._char_segments_to_html(segs_after, bg) or "(なし)"
            else:
                before = "<br>".join(entry.before) or "(なし)"
                after = "<br>".join(entry.after) or "(なし)"
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
                threshold=get_threshold(), image_size=get_image_size(), progress_callback=progress,
            )
        except Exception as exc:  # noqa: BLE001 - ユーザーに失敗内容を見せるため捕捉
            progress_dialog.close()
            QMessageBox.critical(self, "エラー", f"Excel出力に失敗しました: {exc}")
            return
        progress_dialog.close()
        self.statusBar().showMessage(f"Excel出力完了: {path}")

    def _export_pdf(self) -> None:
        """PDFレポート出力(#新機能10)。Excel出力と同じ流れでbuild_pdf_reportを呼ぶ。"""
        if self.alignment is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "PDFレポートを保存", "diff_report.pdf", "PDF Files (*.pdf)")
        if not path:
            return

        progress_dialog = self._make_progress_dialog("PDF出力中", "PDFレポートを作成中...")

        def progress(current: int, total: int) -> None:
            progress_dialog.setValue(int(100 * current / max(total, 1)))
            QApplication.processEvents()

        try:
            build_pdf_report(
                self.pdf_a_path, self.pdf_b_path, self.pages_a, self.pages_b, self.alignment, path,
                threshold=get_threshold(), image_size=get_image_size(), progress_callback=progress,
            )
        except Exception as exc:  # noqa: BLE001 - ユーザーに失敗内容を見せるため捕捉
            progress_dialog.close()
            QMessageBox.critical(self, "エラー", f"PDF出力に失敗しました: {exc}")
            return
        progress_dialog.close()
        self.statusBar().showMessage(f"PDF出力完了: {path}")

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
                threshold=get_threshold(), image_size=get_image_size(), progress_callback=progress,
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
        self.btn_export_pdf.setEnabled(False)
        self.btn_save_session.setEnabled(False)
        self._update_jump_buttons_enabled()

        changed = len(self.alignment.changed_pages())
        self.summary_label.setText(f"[保存済みセッションを表示中] 差分: {changed}件 (元PDFなしで表示)")
        self.statusBar().showMessage(f"セッション読込完了: {path}")
        if self.alignment.page_statuses:
            self.diff_list.setCurrentRow(0)
