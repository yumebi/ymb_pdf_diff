import os
import sys
from pathlib import Path

import pytesseract


def _vendor_dir() -> Path:
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent
    return base / "vendor" / "tesseract"


def configure_bundled_tesseract() -> bool:
    """同梱のTesseract-OCR(vendor/tesseract/)があればpytesseractに使わせる。

    見つからない場合は何もしない(システムPATH上のtesseractにフォールバックする、
    開発時はvendor/未作成のためこちらの経路になる)。
    戻り値: 同梱版を使うよう設定できたか
    """
    vendor_dir = _vendor_dir()
    exe_name = "tesseract.exe" if sys.platform == "win32" else "tesseract"
    exe_path = vendor_dir / exe_name
    tessdata_dir = vendor_dir / "tessdata"

    if exe_path.exists() and tessdata_dir.exists():
        pytesseract.pytesseract.tesseract_cmd = str(exe_path)
        os.environ["TESSDATA_PREFIX"] = str(tessdata_dir)
        return True
    return False
