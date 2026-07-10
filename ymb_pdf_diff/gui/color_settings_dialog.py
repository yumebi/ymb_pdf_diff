from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
)

from .diff_colors import LABELS, DiffColors
from .diff_settings import get_image_size, get_threshold, set_image_size, set_threshold

# レポート画像サイズ(#新機能11): プリセットキーと表示名の対応
_IMAGE_SIZE_LABELS = {
    "small": "小(コンパクト)",
    "medium": "中(標準)",
    "large": "大(高精細)",
}


def _contrasting_text_color(hex_color: str) -> str:
    """背景色の輝度から、読みやすい文字色(黒/白)を選ぶ。"""
    color = QColor(hex_color)
    luminance = 0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()
    return "#000000" if luminance > 140 else "#FFFFFF"


def _swatch_style(hex_color: str) -> str:
    return f"background-color: {hex_color}; color: {_contrasting_text_color(hex_color)};"


class ColorSettingsDialog(QDialog):
    """差分の配色をカスタマイズするダイアログ。OKを押すとDiffColorsに保存される。"""

    def __init__(self, diff_colors: DiffColors, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("表示設定(配色)")
        self.diff_colors = diff_colors
        self._buttons: dict = {}

        layout = QVBoxLayout(self)
        for key in diff_colors.keys():
            row = QHBoxLayout()
            row.addWidget(QLabel(LABELS[key]))

            swatch = QPushButton(diff_colors.get(key))
            swatch.setStyleSheet(_swatch_style(diff_colors.get(key)))
            swatch.clicked.connect(lambda _checked, k=key, b=swatch: self._pick_color(k, b))
            self._buttons[key] = swatch
            row.addWidget(swatch)
            layout.addLayout(row)

        reset_btn = QPushButton("初期値に戻す")
        reset_btn.clicked.connect(self._reset_defaults)
        layout.addWidget(reset_btn)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(separator)

        # 画像差分の感度(#新機能7): 値が小さいほど、わずかな画素差でも差分として拾う
        threshold_row = QHBoxLayout()
        threshold_row.addWidget(QLabel("画像差分の感度(小さいほど敏感)"))
        self._threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self._threshold_slider.setRange(0, 100)
        self._threshold_slider.setValue(get_threshold())
        threshold_row.addWidget(self._threshold_slider)
        self._threshold_value_label = QLabel(str(get_threshold()))
        self._threshold_value_label.setMinimumWidth(28)
        threshold_row.addWidget(self._threshold_value_label)
        self._threshold_slider.valueChanged.connect(self._on_threshold_changed)
        layout.addLayout(threshold_row)

        # レポート画像サイズ(#新機能11): PDF/Excelレポート・セッション保存の埋め込み画像サイズ
        image_size_row = QHBoxLayout()
        image_size_row.addWidget(QLabel("レポート画像サイズ"))
        self._image_size_combo = QComboBox()
        for key, label in _IMAGE_SIZE_LABELS.items():
            self._image_size_combo.addItem(label, key)
        current_index = self._image_size_combo.findData(get_image_size())
        self._image_size_combo.setCurrentIndex(max(current_index, 0))
        self._image_size_combo.currentIndexChanged.connect(self._on_image_size_changed)
        image_size_row.addWidget(self._image_size_combo)
        layout.addLayout(image_size_row)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

    def _pick_color(self, key: str, button: QPushButton) -> None:
        color = QColorDialog.getColor(QColor(self.diff_colors.get(key)), self, "色を選択")
        if color.isValid():
            self.diff_colors.set(key, color.name())
            button.setText(color.name())
            button.setStyleSheet(_swatch_style(color.name()))

    def _reset_defaults(self) -> None:
        self.diff_colors.reset_defaults()
        for key, button in self._buttons.items():
            value = self.diff_colors.get(key)
            button.setText(value)
            button.setStyleSheet(_swatch_style(value))

    def _on_threshold_changed(self, value: int) -> None:
        self._threshold_value_label.setText(str(value))
        set_threshold(value)

    def _on_image_size_changed(self, index: int) -> None:
        key = self._image_size_combo.itemData(index)
        if key:
            set_image_size(key)
