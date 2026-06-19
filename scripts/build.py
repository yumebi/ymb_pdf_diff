"""PyInstallerでWin exe / Mac appをビルドする(各OS上でそのOS向けにネイティブ実行する。クロスコンパイルではない)。

使い方:
    python scripts/build.py
"""
import subprocess
import sys
from pathlib import Path

APP_NAME = "YMB PDF DIFF"
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    data_sep = ";" if sys.platform == "win32" else ":"
    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--windowed",
        "--name",
        APP_NAME,
        "--add-data",
        f"{PROJECT_ROOT / 'assets'}{data_sep}assets",
    ]
    if sys.platform == "win32":
        args += ["--icon", str(PROJECT_ROOT / "assets" / "icon.ico")]
    # macOS: .icns未生成のためアイコン指定は省略(#10でMac実機検証時に追加対応)

    vendor_dir = PROJECT_ROOT / "vendor" / "tesseract"
    if vendor_dir.exists():
        args += ["--add-data", f"{vendor_dir}{data_sep}vendor/tesseract"]
    else:
        print(f"[警告] {vendor_dir} が見つからない。OCR(同梱版)なしでビルドする(scripts/fetch_tesseract_vendor.pyで取得可能)。")

    args.append(str(PROJECT_ROOT / "app_main.py"))
    subprocess.run(args, check=True, cwd=PROJECT_ROOT)


if __name__ == "__main__":
    main()
