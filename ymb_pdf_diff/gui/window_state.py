from PySide6.QtCore import QRect, QSettings
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QMainWindow

_ORG_NAME = "YMB"
_APP_NAME = "YMB PDF DIFF"
_GEOMETRY_KEY = "window/geometry"


def save_window_geometry(window: QMainWindow) -> None:
    settings = QSettings(_ORG_NAME, _APP_NAME)
    settings.setValue(_GEOMETRY_KEY, window.saveGeometry())


def restore_window_geometry(window: QMainWindow) -> None:
    settings = QSettings(_ORG_NAME, _APP_NAME)
    geometry = settings.value(_GEOMETRY_KEY)
    if geometry is not None:
        window.restoreGeometry(geometry)
    clamp_to_available_screens(window)


def clamp_to_available_screens(window: QMainWindow) -> None:
    """保存位置が現在接続中のどの画面にも収まらない場合(外部モニタ取り外し後等)、
    プライマリ画面の範囲内に収まるよう位置・サイズを補正する。"""
    geo = window.geometry()
    screens = QGuiApplication.screens()
    if any(screen.availableGeometry().intersects(geo) for screen in screens):
        return

    primary = QGuiApplication.primaryScreen()
    if primary is None:
        return
    target = primary.availableGeometry()
    width = min(geo.width(), target.width())
    height = min(geo.height(), target.height())
    x = target.x() + (target.width() - width) // 2
    y = target.y() + (target.height() - height) // 2
    window.setGeometry(QRect(x, y, width, height))
