from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from .diff_colors import LABELS, DiffColors


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
