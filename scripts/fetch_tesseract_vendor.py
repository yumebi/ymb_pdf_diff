"""配布物にTesseract-OCR本体+日本語データを同梱するため、ローカルにvendor/tesseract/を作る。

このスクリプトはビルドする開発者のマシンで一度だけ実行する(end userは実行不要)。
配布バイナリ(DLL等)はリポジトリにコミットしない想定(.gitignore対象)。

前提: Windowsの場合 choco install tesseract 等で本体が
"C:\\Program Files\\Tesseract-OCR" にインストール済みであること。

使い方:
    python scripts/fetch_tesseract_vendor.py
出力:
    vendor/tesseract/tesseract.exe
    vendor/tesseract/*.dll
    vendor/tesseract/tessdata/eng.traineddata
    vendor/tesseract/tessdata/jpn.traineddata
    vendor/tesseract/LICENSE
"""
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENDOR_DIR = PROJECT_ROOT / "vendor" / "tesseract"
JPN_TRAINEDDATA_URL = "https://github.com/tesseract-ocr/tessdata_fast/raw/main/jpn.traineddata"

WINDOWS_INSTALL_DIR = Path("C:/Program Files/Tesseract-OCR")


def _find_system_install() -> Path:
    if sys.platform == "win32" and WINDOWS_INSTALL_DIR.exists():
        return WINDOWS_INSTALL_DIR
    raise FileNotFoundError(
        "システムにインストール済みのTesseract-OCRが見つからない。"
        "先に `choco install tesseract -y` 等でインストールしてから再実行すること。"
    )


def main() -> None:
    system_dir = _find_system_install()
    VENDOR_DIR.mkdir(parents=True, exist_ok=True)
    (VENDOR_DIR / "tessdata").mkdir(exist_ok=True)

    exe_name = "tesseract.exe" if sys.platform == "win32" else "tesseract"
    shutil.copy2(system_dir / exe_name, VENDOR_DIR / exe_name)
    for dll in system_dir.glob("*.dll"):
        shutil.copy2(dll, VENDOR_DIR / dll.name)

    shutil.copy2(system_dir / "tessdata" / "eng.traineddata", VENDOR_DIR / "tessdata" / "eng.traineddata")

    license_path = system_dir / "doc" / "LICENSE"
    if license_path.exists():
        shutil.copy2(license_path, VENDOR_DIR / "LICENSE")

    jpn_path = VENDOR_DIR / "tessdata" / "jpn.traineddata"
    print(f"jpn.traineddataを取得中: {JPN_TRAINEDDATA_URL}")
    subprocess.run(["curl", "-sL", "-o", str(jpn_path), JPN_TRAINEDDATA_URL], check=True)

    print(f"完了: {VENDOR_DIR}")


if __name__ == "__main__":
    main()
