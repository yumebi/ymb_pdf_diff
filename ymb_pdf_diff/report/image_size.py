"""レポート埋め込み画像のサイズプリセット(#新機能11)。

PDFレポート・Excelレポート・セッション保存はいずれもページキャプチャをサムネイル化して
埋め込むが、その最大サイズをCLI/GUI双方から同じ3段階(small/medium/large)で選べるように
一元管理する。GUI(PySide6)に依存せずCLIからも参照できるよう、report配下の
このモジュールだけに定義を集約する。
"""
from typing import Dict, Tuple

IMAGE_SIZE_CHOICES = ("small", "medium", "large")
DEFAULT_IMAGE_SIZE = "medium"

# PDFレポート・セッション保存用: サムネイル化する際の長辺の最大ピクセル数。
# mediumは変更前の既定値(1200px)と同じにして、既存の見た目を変えない。
LONG_EDGE_MAX_PX: Dict[str, int] = {
    "small": 800,
    "medium": 1200,
    "large": 1600,
}

# Excelレポート用: サムネイルの(幅, 高さ)上限。mediumは変更前の既定値(800, 1100)と同じ。
EXCEL_THUMB_MAX_SIZE: Dict[str, Tuple[int, int]] = {
    "small": (534, 734),
    "medium": (800, 1100),
    "large": (1067, 1467),
}


def resolve_long_edge_max_px(image_size: str) -> int:
    """image_size("small"/"medium"/"large")から長辺の最大ピクセル数を返す。未知の値はmedium扱い。"""
    return LONG_EDGE_MAX_PX.get(image_size, LONG_EDGE_MAX_PX[DEFAULT_IMAGE_SIZE])


def resolve_excel_thumb_max_size(image_size: str) -> Tuple[int, int]:
    """image_size("small"/"medium"/"large")からExcel用サムネイルの(幅, 高さ)上限を返す。"""
    return EXCEL_THUMB_MAX_SIZE.get(image_size, EXCEL_THUMB_MAX_SIZE[DEFAULT_IMAGE_SIZE])
