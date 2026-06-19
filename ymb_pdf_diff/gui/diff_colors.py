from PySide6.QtCore import QSettings

_ORG_NAME = "YMB"
_APP_NAME = "YMB PDF DIFF"

DEFAULT_COLORS = {
    "changed_bg": "#FFEB9C",
    "changed_fg": "#9C6500",
    "inserted_bg": "#C6EFCE",
    "inserted_fg": "#006100",
    "deleted_bg": "#FFC7CE",
    "deleted_fg": "#9C0006",
    "highlight": "#FF0000",
}

LABELS = {
    "changed_bg": "変更: 背景色",
    "changed_fg": "変更: 文字色",
    "inserted_bg": "追加: 背景色",
    "inserted_fg": "追加: 文字色",
    "deleted_bg": "削除: 背景色",
    "deleted_fg": "削除: 文字色",
    "highlight": "差分ハイライト枠の色",
}


class DiffColors:
    """差分の配色設定。QSettingsに永続化し、ユーザーがカスタマイズできるようにする。"""

    def __init__(self) -> None:
        self._settings = QSettings(_ORG_NAME, _APP_NAME)
        self._colors = dict(DEFAULT_COLORS)
        for key in DEFAULT_COLORS:
            value = self._settings.value(f"colors/{key}")
            if value:
                self._colors[key] = value

    def get(self, key: str) -> str:
        return self._colors[key]

    def set(self, key: str, value: str) -> None:
        self._colors[key] = value
        self._settings.setValue(f"colors/{key}", value)

    def reset_defaults(self) -> None:
        for key, value in DEFAULT_COLORS.items():
            self.set(key, value)

    def keys(self):
        return list(DEFAULT_COLORS.keys())
