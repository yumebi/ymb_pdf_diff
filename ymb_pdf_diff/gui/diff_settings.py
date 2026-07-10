from PySide6.QtCore import QSettings

from ..report.image_size import DEFAULT_IMAGE_SIZE, IMAGE_SIZE_CHOICES

_ORG_NAME = "YMB"
_APP_NAME = "YMB PDF DIFF"
_THRESHOLD_KEY = "diff/threshold"
_IMAGE_SIZE_KEY = "report/image_size"

DEFAULT_THRESHOLD = 30
MIN_THRESHOLD = 0
MAX_THRESHOLD = 100


def get_threshold() -> int:
    """画像差分の感度(0-100、小さいほど敏感)をQSettingsから読み出す。"""
    settings = QSettings(_ORG_NAME, _APP_NAME)
    raw = settings.value(_THRESHOLD_KEY, DEFAULT_THRESHOLD)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = DEFAULT_THRESHOLD
    return max(MIN_THRESHOLD, min(MAX_THRESHOLD, value))


def set_threshold(value: int) -> None:
    """画像差分の感度をQSettingsに保存する。次回の「比較実行」から反映される。"""
    value = max(MIN_THRESHOLD, min(MAX_THRESHOLD, int(value)))
    settings = QSettings(_ORG_NAME, _APP_NAME)
    settings.setValue(_THRESHOLD_KEY, value)


def get_image_size() -> str:
    """レポート埋め込み画像のサイズ(#新機能11、"small"/"medium"/"large")をQSettingsから読み出す。"""
    settings = QSettings(_ORG_NAME, _APP_NAME)
    raw = settings.value(_IMAGE_SIZE_KEY, DEFAULT_IMAGE_SIZE)
    value = str(raw)
    return value if value in IMAGE_SIZE_CHOICES else DEFAULT_IMAGE_SIZE


def set_image_size(value: str) -> None:
    """レポート埋め込み画像のサイズをQSettingsに保存する。次回のレポート出力から反映される。"""
    if value not in IMAGE_SIZE_CHOICES:
        value = DEFAULT_IMAGE_SIZE
    settings = QSettings(_ORG_NAME, _APP_NAME)
    settings.setValue(_IMAGE_SIZE_KEY, value)
