"""動作確認用のわかりやすいサンプルPDF(A/B)を作る。

含まれる差分パターン:
- 表紙: 完全に同一(差分なし)
- 「1. 開会のご挨拶」: 文章の一部だけ変更(テキスト差分)
- 「2. 売上報告」: 文章は同一だが図(色・位置)だけ変更(見た目だけの差分)
- 「2.5 質疑応答」: Bにのみ存在する新規ページ(追加ページ)
- 「3. 来期の計画」「4. 閉会のご挨拶」: 内容は同一だが、新規ページ挿入の影響でページ番号がズレる(ページ移動)

使い方:
    python scripts/make_sample_pdfs.py
出力:
    samples/sample_A.pdf
    samples/sample_B.pdf
"""
from pathlib import Path

import fitz

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"
PAGE_SIZE = (595, 842)  # A4
FONT = "japan"
MARGIN = 72


def _add_title_page(doc: fitz.Document) -> None:
    page = doc.new_page(width=PAGE_SIZE[0], height=PAGE_SIZE[1])
    page.insert_text((MARGIN, 220), "定例会議 議事録", fontname=FONT, fontsize=28)
    page.insert_text((MARGIN, 280), "2026年6月19日　第3会議室", fontname=FONT, fontsize=14)
    page.insert_text((MARGIN, 310), "出席者: 山田、佐藤、鈴木、田中", fontname=FONT, fontsize=14)


def _add_text_page(doc: fitz.Document, heading: str, body: str) -> None:
    page = doc.new_page(width=PAGE_SIZE[0], height=PAGE_SIZE[1])
    page.insert_text((MARGIN, 100), heading, fontname=FONT, fontsize=20)
    rect = fitz.Rect(MARGIN, 140, PAGE_SIZE[0] - MARGIN, 400)
    page.insert_textbox(rect, body, fontname=FONT, fontsize=13.5, lineheight=1.8)


def _add_sales_report_page(doc: fitz.Document, box_color: tuple, box_rect: tuple, box_label: str) -> None:
    page = doc.new_page(width=PAGE_SIZE[0], height=PAGE_SIZE[1])
    page.insert_text((MARGIN, 100), "2. 売上報告", fontname=FONT, fontsize=20)
    body = "今月の売上は前月比5%増加しました。詳細は下記グラフの通りです。主要因は新製品の販売が好調だったことです。"
    rect = fitz.Rect(MARGIN, 140, PAGE_SIZE[0] - MARGIN, 280)
    page.insert_textbox(rect, body, fontname=FONT, fontsize=13.5, lineheight=1.8)

    page.draw_rect(fitz.Rect(*box_rect), color=box_color, fill=box_color, width=0)
    page.insert_text((box_rect[0], box_rect[1] - 12), box_label, fontname=FONT, fontsize=12)


def build_document_a(path: Path) -> None:
    doc = fitz.open()
    _add_title_page(doc)
    _add_text_page(
        doc,
        "1. 開会のご挨拶",
        "本日はお忙しい中お集まりいただきありがとうございます。定刻になりましたので、"
        "ただいまより定例会議を開始いたします。本日の会議は14時までを予定しております。",
    )
    _add_sales_report_page(doc, box_color=(0.2, 0.4, 0.9), box_rect=(100, 320, 400, 420), box_label="売上グラフ")
    _add_text_page(
        doc,
        "3. 来期の計画",
        "来期は新規顧客の開拓に力を入れる予定です。具体的な数値目標は次回会議で共有します。",
    )
    _add_text_page(
        doc,
        "4. 閉会のご挨拶",
        "本日は活発なご意見をありがとうございました。これにて定例会議を閉会いたします。お疲れ様でした。",
    )
    doc.save(str(path))
    doc.close()


def build_document_b(path: Path) -> None:
    doc = fitz.open()
    _add_title_page(doc)
    _add_text_page(
        doc,
        "1. 開会のご挨拶",
        "本日はお忙しい中お集まりいただきありがとうございます。定刻になりましたので、"
        "ただいまより定例会議を開始いたします。本日の会議は15時30分までを予定しております。",
    )
    _add_sales_report_page(doc, box_color=(0.9, 0.2, 0.2), box_rect=(120, 340, 420, 440), box_label="売上グラフ")
    _add_text_page(
        doc,
        "2.5 質疑応答",
        "Q. 新製品の売上について教えてください。\nA. 新製品は発売後3ヶ月で目標を達成しました。",
    )
    _add_text_page(
        doc,
        "3. 来期の計画",
        "来期は新規顧客の開拓に力を入れる予定です。具体的な数値目標は次回会議で共有します。",
    )
    _add_text_page(
        doc,
        "4. 閉会のご挨拶",
        "本日は活発なご意見をありがとうございました。これにて定例会議を閉会いたします。お疲れ様でした。",
    )
    doc.save(str(path))
    doc.close()


def main() -> None:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    path_a = SAMPLES_DIR / "sample_A.pdf"
    path_b = SAMPLES_DIR / "sample_B.pdf"
    build_document_a(path_a)
    build_document_b(path_b)
    print(f"saved: {path_a}")
    print(f"saved: {path_b}")


if __name__ == "__main__":
    main()
