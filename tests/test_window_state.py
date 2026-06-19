"""保存済みウィンドウ位置が現在の画面に収まらない場合のクランプ処理を確認する。
画面なし環境でも実行できるようQT_QPA_PLATFORM=offscreenを使う。
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QRect
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QMainWindow

from ymb_pdf_diff.gui.window_state import clamp_to_available_screens


def test_offscreen_window_is_clamped_into_primary_screen():
    app = QApplication.instance() or QApplication(sys.argv)
    window = QMainWindow()

    # 取り外された外部モニタに置かれていたかのような、現在のどの画面にも存在しない座標
    window.setGeometry(QRect(-100000, -100000, 800, 600))
    clamp_to_available_screens(window)

    primary = QGuiApplication.primaryScreen().availableGeometry()
    geo = window.geometry()
    assert primary.intersects(geo), f"primary={primary}, geo={geo}"
    assert geo.width() <= primary.width()
    assert geo.height() <= primary.height()
    window.close()
    print("OK: test_offscreen_window_is_clamped_into_primary_screen")


def test_geometry_within_screen_is_left_untouched():
    app = QApplication.instance() or QApplication(sys.argv)
    window = QMainWindow()

    primary = QGuiApplication.primaryScreen().availableGeometry()
    original = QRect(primary.x() + 10, primary.y() + 10, 400, 300)
    window.setGeometry(original)
    clamp_to_available_screens(window)

    assert window.geometry() == original
    window.close()
    print("OK: test_geometry_within_screen_is_left_untouched")


if __name__ == "__main__":
    test_offscreen_window_is_clamped_into_primary_screen()
    test_geometry_within_screen_is_left_untouched()
