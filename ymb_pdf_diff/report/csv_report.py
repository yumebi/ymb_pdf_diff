"""CSV差分レポート出力(#新機能13)。

Excelレポートの「サマリー」シートに相当するページ別ステータス一覧を、
Excelを開かなくても表計算ソフトやテキストエディタで扱えるCSVとして書き出す。
画像の埋め込みは行わないため、dpi/image_sizeは受け取るが使わない。
UTF-8 BOM付きで出力するため、WindowsのExcelでそのまま開いても文字化けしない。
"""
import csv
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

from ..core import AlignmentResult, PageLine, PageStatus, diff_page_lines

_STATUS_LABEL = {
    "unchanged": "差分なし",
    "changed": "差分あり",
    "inserted": "追加ページ(Bのみ)",
    "deleted": "削除ページ(Aのみ)",
}


def _diff_count_for(status: PageStatus, pages_a: List[List[PageLine]], pages_b: List[List[PageLine]]) -> int:
    if status.status == "changed" and status.a_page is not None and status.b_page is not None:
        return len(diff_page_lines(pages_a[status.a_page], pages_b[status.b_page]))
    if status.status in ("inserted", "deleted"):
        return 1
    return 0


def build_csv_report(
    pdf_a_path: str,
    pdf_b_path: str,
    pages_a: List[List[PageLine]],
    pages_b: List[List[PageLine]],
    alignment: AlignmentResult,
    output_path: str,
    dpi: int = 150,
    threshold: int = 30,
    image_size: str = "medium",
    shift_tolerance: int = 0,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> None:
    """比較結果をCSVとして書き出す。

    先頭にファイル情報・集計値、続けてページ別ステータス一覧(ページ番号A/B、ステータス、
    備考、差分件数)を出力する。ヘッダー行はExcel/PDFレポートのサマリーと揃えている。
    dpi/threshold/image_size/shift_toleranceはExcel/PDFレポートと同一シグネチャを
    維持するために受け取るだけで、画像を含まないCSVでは使用しない。
    """
    out_path = Path(output_path)
    if out_path.suffix.lower() != ".csv":
        out_path = out_path.with_suffix(".csv")

    total_diff = len(alignment.changed_pages())
    rows: List[List[str]] = []
    rows.append(["ファイルA", pdf_a_path])
    rows.append(["ファイルB", pdf_b_path])
    rows.append(["比較日時", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    rows.append(["総ページ数(A/B)", f"{len(pages_a)} / {len(pages_b)}"])
    rows.append(["総差分件数", str(total_diff)])
    rows.append([])
    rows.append(["ページ番号A", "ページ番号B", "ステータス", "備考", "差分件数"])

    for idx, status in enumerate(alignment.page_statuses):
        a_disp = status.a_page + 1 if status.a_page is not None else "-"
        b_disp = status.b_page + 1 if status.b_page is not None else "-"
        notes = []
        if status.moved:
            notes.append("ページ移動")
        if status.visual_only:
            notes.append("見た目のみ")
        rows.append([
            str(a_disp),
            str(b_disp),
            _STATUS_LABEL[status.status],
            " / ".join(notes),
            str(_diff_count_for(status, pages_a, pages_b)),
        ])
        if progress_callback:
            progress_callback(idx + 1, len(alignment.page_statuses))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    # 文字化け防止のためBOM付きUTF-8で書く(Excelで開いても日本語がそのまま表示される)。
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
