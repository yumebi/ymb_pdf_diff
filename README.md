# YMB PDF DIFF

2つのPDFを読み込み、差異を初心者でも一目で分かる形で表示するWindows/Mac対応ツール。

## 主な機能

- **テキスト差分**: 文書全体を1本の行シーケンスとして整列(`difflib`)し、1文の増減によるページズレに強い
- **見た目(画像)差分**: テキストが同一でも図・色・レイアウトだけが変わったページも検出
- **ページ移動検出**: ページ番号がズレても内容が同じなら「移動」と表示、誤って差分扱いしない
- **スキャンPDF対応**: テキストレイヤーがないページはOCR(Tesseract、日本語+英語)で読み取り
- **GUI**: 左右2ペイン表示、ズーム/ドラッグスクロール、差分ハイライト、配色カスタマイズ
- **Excelレポート出力**: サマリーシート+ページ単位の詳細シート(キャプチャ画像・テキスト差分付き)
- **セッション保存/読込**: 差分結果を`.ymbdiff`形式で保存、元PDFなしでも再表示可能
- **自動更新チェック**: 起動時に新バージョン通知(任意)

## 必要環境

- Python 3.9+
- Windows or macOS
- (OCR利用時) Tesseract-OCR本体 ※同梱ビルドなら不要、詳細は下記

## セットアップ(開発)

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
python -m ymb_pdf_diff   # GUI起動
```

CLIで動作確認する場合:

```bash
python -m ymb_pdf_diff.cli sample_A.pdf sample_B.pdf --excel diff_report.xlsx
```

動作確認用サンプルPDFは `samples/sample_A.pdf` / `samples/sample_B.pdf` にある(`scripts/make_sample_pdfs.py`で再生成可能)。

## ビルド(配布用パッケージ作成)

```bash
pip install -r requirements-dev.txt
python scripts/build.py
```

Windowsはexe(`--icon`付き)、Macはネイティブ.appが`dist/`に生成される(各OS上で実行すること、クロスコンパイル不可)。

### GitHub Actionsで自動リリース

`v*.*.*` 形式のタグをpushすると、[.github/workflows/release.yml](.github/workflows/release.yml) がWindows/Mac両方でビルドし、Windowsインストーラ(.exe)とMacのdmgをGitHub Releasesに自動添付する。

```bash
git tag v0.1.0
git push origin v0.1.0
```

タグなしで`workflow_dispatch`から手動実行も可能(その場合はビルドのみ、Releaseへの公開はスキップ)。

### OCR(Tesseract)を同梱する場合

```bash
python scripts/fetch_tesseract_vendor.py   # システムにインストール済みのTesseract-OCRからvendor/tesseract/を作成
python scripts/build.py                     # vendor/があれば自動的に同梱される
```

未同梱の場合、実行環境にTesseract-OCRが別途インストールされていればOCRは動作する(`jpn`言語データの追加が必要)。

### Windowsインストーラ

[Inno Setup](https://jrsoftware.org/isinfo.php) をインストール後:

```bash
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\windows\installer.iss
```

### Macのdmg

```bash
bash packaging/macos/build_dmg.sh
```

## テスト

```bash
python tests/test_aligner.py
python tests/test_image_diff.py
# 他、tests/ 配下の各ファイルを個別実行(pytest不使用)
```

GUI関連テストは画面なし環境でも動くよう `QT_QPA_PLATFORM=offscreen` を使用。

## プロジェクト構成

```
ymb_pdf_diff/
  core/        # PDF読込・テキスト/画像差分・OCRなどコアロジック(UI非依存)
  gui/         # PySide6 GUI
  report/      # Excelレポート出力
  session.py   # セッション保存/読込
  update_check.py
scripts/       # ビルド・サンプル生成・Tesseract同梱用スクリプト
packaging/     # Windowsインストーラ(.iss)・Mac dmgスクリプト
tests/         # 単体テスト(pytest不使用、直接実行)
samples/       # 動作確認用サンプルPDF
```
