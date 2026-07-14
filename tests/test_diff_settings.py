"""gui/diff_settings.pyのQSettings永続化(#新機能11: 画像サイズ設定)を確認する。"""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

from ymb_pdf_diff.gui.diff_settings import (
    DEFAULT_SHIFT_TOLERANCE,
    DEFAULT_THRESHOLD,
    get_image_size,
    get_shift_tolerance,
    get_threshold,
    set_image_size,
    set_shift_tolerance,
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


def test_shift_tolerance_round_trip():
    """位置ズレ許容(#新機能12)のQSettings永続化を確認する。"""
    app = QApplication.instance() or QApplication(sys.argv)
    original = get_shift_tolerance()

    try:
        for value in (0, 1, 5, 10):
            set_shift_tolerance(value)
            assert get_shift_tolerance() == value, f"set_shift_tolerance({value})後にget_shift_toleranceが一致しない"

        # 範囲外の値は0-10にクランプされる
        set_shift_tolerance(-5)
        assert get_shift_tolerance() == 0
        set_shift_tolerance(999)
        assert get_shift_tolerance() == 10

        print("OK: test_shift_tolerance_round_trip")
    finally:
        set_shift_tolerance(original)


def test_shift_tolerance_still_round_trips_alongside_threshold_and_image_size():
    """位置ズレ許容の追加が、既存のthreshold/image_size設定に影響しないことを確認する回帰チェック。"""
    app = QApplication.instance() or QApplication(sys.argv)
    original_threshold = get_threshold()
    original_size = get_image_size()
    original_shift_tolerance = get_shift_tolerance()

    try:
        set_threshold(12)
        set_image_size("large")
        set_shift_tolerance(4)
        assert get_threshold() == 12
        assert get_image_size() == "large"
        assert get_shift_tolerance() == 4

        set_shift_tolerance(DEFAULT_SHIFT_TOLERANCE)
        assert get_shift_tolerance() == DEFAULT_SHIFT_TOLERANCE
        assert get_threshold() == 12
        assert get_image_size() == "large"

        print("OK: test_shift_tolerance_still_round_trips_alongside_threshold_and_image_size")
    finally:
        set_threshold(original_threshold)
        set_image_size(original_size)
        set_shift_tolerance(original_shift_tolerance)


if __name__ == "__main__":
    test_image_size_round_trip()
    test_threshold_still_round_trips_alongside_image_size()
    test_shift_tolerance_round_trip()
    test_shift_tolerance_still_round_trips_alongside_threshold_and_image_size()
