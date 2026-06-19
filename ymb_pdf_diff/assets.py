import sys
from pathlib import Path


def asset_path(name: str) -> Path:
    """開発時はプロジェクトルートのassets/、PyInstallerバンドル時はsys._MEIPASS配下のassets/を見る。"""
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent
    return base / "assets" / name
