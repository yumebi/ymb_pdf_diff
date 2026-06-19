from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsTextItem, QGraphicsView

MIN_ZOOM = 0.1
MAX_ZOOM = 8.0
_ZOOM_STEP = 1.15


class ImageView(QGraphicsView):
    """ズーム(Ctrl+ホイール/ボタン)とドラッグスクロール(ScrollHandDrag)に対応したPDFページ表示用ビュー。"""

    zoomed = Signal(float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item = QGraphicsPixmapItem()
        self._scene.addItem(self._pixmap_item)
        self._placeholder_item = QGraphicsTextItem("")
        self._scene.addItem(self._placeholder_item)

        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self._zoom = 1.0

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
