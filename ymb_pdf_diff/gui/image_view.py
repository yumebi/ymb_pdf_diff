from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsTextItem, QGraphicsView

MIN_ZOOM = 0.1
MAX_ZOOM = 8.0
_ZOOM_STEP = 1.15


class ImageView(QGraphicsView):
    """ズーム(Ctrl+ホイール/ボタン)とドラッグスクロール(ScrollHandDrag)に対応したPDFページ表示用ビュー。

    PDFファイルのドラッグ&ドロップにも対応し、ドロップ時にfile_droppedシグナルを発火する。
    """

    zoomed = Signal(float)
    file_dropped = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item = QGraphicsPixmapItem()
        # QGraphicsPixmapItemはデフォルトでFastTransformation(ニアレストネイバー)を使うため、
        # ビュー側のSmoothPixmapTransformを設定していても拡大縮小時にジャギーが出てしまう。
        # アイテム側にも明示的にスムーズ変換を指定する。
        self._pixmap_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self._scene.addItem(self._pixmap_item)
        self._placeholder_item = QGraphicsTextItem("")
        self._scene.addItem(self._placeholder_item)

        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._zoom = 1.0
        self.setAcceptDrops(True)

    def set_pixmap(self, pixmap: QPixmap) -> None:
        self._placeholder_item.setPlainText("")
        self._pixmap_item.setPixmap(pixmap)
        self._scene.setSceneRect(self._pixmap_item.boundingRect())

    def set_placeholder(self, text: str) -> None:
        self._pixmap_item.setPixmap(QPixmap())
        self._placeholder_item.setPlainText(text)
        self._scene.setSceneRect(self._placeholder_item.boundingRect())

    def zoom(self) -> float:
        return self._zoom

    def current_pixmap(self) -> QPixmap:
        return self._pixmap_item.pixmap()

    def set_zoom(self, factor: float, emit: bool = True) -> None:
        factor = max(MIN_ZOOM, min(MAX_ZOOM, factor))
        self._zoom = factor
        self.resetTransform()
        self.scale(factor, factor)
        if emit:
            self.zoomed.emit(factor)

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = _ZOOM_STEP if event.angleDelta().y() > 0 else 1 / _ZOOM_STEP
            self.set_zoom(self._zoom * factor)
            event.accept()
        else:
            super().wheelEvent(event)

    @staticmethod
    def _dropped_pdf_path(event) -> Optional[str]:
        """イベントがローカルのPDFファイル1つのドロップであれば、そのパスを返す。"""
        mime = event.mimeData()
        if not mime.hasUrls():
            return None
        for url in mime.urls():
            if url.isLocalFile() and url.toLocalFile().lower().endswith(".pdf"):
                return url.toLocalFile()
        return None

    def dragEnterEvent(self, event) -> None:
        if self._dropped_pdf_path(event) is not None:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        # QGraphicsViewのデフォルト実装はシーンにイベントを転送するが、
        # ファイルドロップはビュー自身で処理したいためオーバーライドする。
        if self._dropped_pdf_path(event) is not None:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        path = self._dropped_pdf_path(event)
        if path is not None:
            event.acceptProposedAction()
            self.file_dropped.emit(path)
        else:
            event.ignore()
