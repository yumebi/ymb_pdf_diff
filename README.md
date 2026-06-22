# YMB PDF差分抽出ツール

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

## 開発環境のセットアップ

### 必要環境

- Python 3.9+
- Windows or macOS
- (OCR利用時) Tesseract-OCR本体 ※同梱ビルドなら不要

### セットアップ

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

## 技術スタック

| 用途 | ライブラリ/ツール |
|---|---|
| 言語 | Python 3.9+ |
| GUI | PySide6 |
| PDF読込・テキスト抽出・画像化 | PyMuPDF (fitz) |
| 画像差分 | Pillow / numpy |
| テキスト整列・差分 | difflib(標準ライブラリ) |
| OCR(スキャンPDF対応) | pytesseract + Tesseract-OCR |
| Excelレポート出力 | openpyxl |
| バージョン比較 | packaging |
| HTTP通信(自動更新チェック) | requests |
| ビルド | PyInstaller |
| Windowsインストーラ | Inno Setup |
| Macインストーラ(dmg) | hdiutil(macOS標準搭載) |
| CI/CD | GitHub Actions |

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

## テスト

```bash
python tests/test_aligner.py
python tests/test_image_diff.py
# 他、tests/ 配下の各ファイルを個別実行(pytest不使用)
```

GUI関連テストは画面なし環境でも動くよう `QT_QPA_PLATFORM=offscreen` を使用。

## ダウンロード

[Releases](https://github.com/yumebi/ymb_pdf_diff/releases) からOS別のインストーラをダウンロードして実行する。

- Windows: `YMB_PDF_DIFF_Setup.exe`
- Mac: `YMB_PDF_DIFF.dmg`

> **インストール時に警告が出る場合がある。** コード署名を行っていないため、Windowsでは「Windows によって PC が保護されました」(SmartScreen)、Macでは「開発元が未確認のため開けません」(Gatekeeper)という警告が表示される可能性がある。問題のあるファイルではないので、以下の手順で進めること。
> - **Windows**: 警告画面で「詳細情報」→「実行」をクリック
> - **Mac**: ファイルを右クリック→「開く」を選択(または システム設定 → プライバシーとセキュリティ で許可)

## ライセンス

[MIT License](LICENSE) © 2026 ymb
