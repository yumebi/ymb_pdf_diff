"""gui/diff_settings.pyのQSettings永続化(#新機能11: 画像サイズ設定)を確認する。"""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

from ymb_pdf_diff.gui.diff_settings import (
    DEFAULT_THRESHOLD,
    get_image_size,
    get_threshold,
    set_image_size,
    set_threshold,
)
from ymb_pdf_diff.report.image_size import DEFAULT_IMAGE_SIZE


def test_image_size_round_trip():
    app = QApplication.instance() or QApplication(sys.argv)
    original = get_image_size()

    try:
        for size in ("small", "medium", "large"):
            set_image_size(size)
            assert get_image_size() == size, f"set_image_size({size!r})後にget_image_sizeが一致しない"

        # 不正な値を保存しようとした場合は既定値(medium)にフォールバックする
        set_image_size("huge")
        assert get_image_size() == DEFAULT_IMAGE_SIZE

        print("OK: test_image_size_round_trip")
    finally:
        set_image_size(original)


def test_threshold_still_round_trips_alongside_image_size():
    """画像サイズ設定の追加が、既存のthreshold設定に影響しないことを確認する回帰チェック。"""
    app = QApplication.instance() or QApplication(sys.argv)
    original_threshold = get_threshold()
    original_size = get_image_size()

    try:
        set_threshold(12)
        set_image_size("large")
        assert get_threshold() == 12
        assert get_image_size() == "large"

        set_threshold(DEFAULT_THRESHOLD)
        assert get_threshold() == DEFAULT_THRESHOLD
        assert get_image_size() == "large"

        print("OK: test_threshold_still_round_trips_alongside_image_size")
    finally:
        set_threshold(original_threshold)
        set_image_size(original_size)


if __name__ == "__main__":
    test_image_size_round_trip()
    test_threshold_still_round_trips_alongside_image_size()
