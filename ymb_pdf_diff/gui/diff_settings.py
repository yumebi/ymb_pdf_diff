from PySide6.QtCore import QSettings

_ORG_NAME = "YMB"
_APP_NAME = "YMB PDF DIFF"
_THRESHOLD_KEY = "diff/threshold"

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
