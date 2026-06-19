import io
import re
from datetime import datetime
from typing import Callable, Dict, List, Optional, Set

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.worksheet import Worksheet

from ..core import (
    AlignmentResult,
    PageLine,
    PageStatus,
    diff_page_lines,
    diff_page_pair,
    draw_highlights,
    render_page,
)

_INVALID_SHEET_CHARS = re.compile(r"[\\/*?:\[\]]")

_STATUS_LABEL = {
    "unchanged": "差分なし",
    "changed": "差分あり",
    "inserted": "追加ページ(Bのみ)",
    "deleted": "削除ページ(Aのみ)",
}

_FILL_DELETE = PatternFill("solid", fgColor="FFC7CE")
_FONT_DELETE = Font(color="9C0006")
_FILL_INSERT = PatternFill("solid", fgColor="C6EFCE")
_FONT_INSERT = Font(color="006100")
_FILL_REPLACE = PatternFill("solid", fgColor="FFEB9C")
_FONT_REPLACE = Font(color="9C6500")
_HEADER_FONT = Font(bold=True)
_THUMB_MAX_SIZE = (800, 1100)


def _safe_sheet_name(name: str, used: Set[str]) -> str:
    name = _INVALID_SHEET_CHARS.sub("_", name)[:31]
    candidate = name
    suffix = 1
    while candidate in used:
        suffix += 1
        candidate = f"{name[: 31 - len(str(suffix)) - 1]}_{suffix}"
    used.add(candidate)
    return candidate


def _sheet_name_for(status: PageStatus, used: Set[str]) -> str:
    if status.status in ("changed",) and status.a_page is not None and status.b_page is not None:
        base = f"P_A{status.a_page + 1}_B{status.b_page + 1}"
    elif status.status == "inserted":
        base = f"P_B{status.b_page + 1}_new"
    elif status.status == "deleted":
        base = f"P_A{status.a_page + 1}_del"
    else:
        base = f"P_A{status.a_page + 1}"
    return _safe_sheet_name(base, used)


def _diff_count_for(status: PageStatus, pages_a: List[List[PageLine]], pages_b: List[List[PageLine]]) -> int:
    if status.status == "changed" and status.a_page is not None and status.b_page is not None:
        return len(diff_page_lines(pages_a[status.a_page], pages_b[status.b_page]))
    if status.status in ("inserted", "deleted"):
        return 1
    return 0


def _embed_thumbnail(ws: Worksheet, image, anchor: str) -> None:
    """PIL Imageをサムネイル化してExcelに埋め込む。

    openpyxlのImage._data()は`fp`(元ファイルのファイルポインタ)を読みに行く実装のため、
    PIL.Image.new/copy等で生成した(ファイルから開いていない)画像はそのまま渡すと
    `AttributeError: 'Image' object has no attribute 'fp'`になる。PNGとしてメモリに
    一度書き出し、fp/formatを明示的に持たせてから渡す。
    """
    thumb = image.copy()
    thumb.thumbnail(_THUMB_MAX_SIZE)
    buf = io.BytesIO()
    thumb.save(buf, format="PNG")
    buf.seek(0)
    thumb.fp = buf
    thumb.format = "PNG"
    ws.add_image(XLImage(thumb), anchor)


def _write_text_diff_table(ws: Worksheet, start_row: int, entries) -> int:
    row = start_row
    ws.cell(row=row, column=1, value="種別").font = _HEADER_FONT
    ws.cell(row=row, column=2, value="変更前(A)").font = _HEADER_FONT
    ws.cell(row=row, column=3, value="変更後(B)").font = _HEADER_FONT
    row += 1

    kind_label = {"replace": "変更", "insert": "追加", "delete": "削除"}
    kind_style = {
        "replace": (_FILL_REPLACE, _FONT_REPLACE),
        "insert": (_FILL_INSERT, _FONT_INSERT),
        "delete": (_FILL_DELETE, _FONT_DELETE),
    }

    for entry in entries:
        fill, font = kind_style.get(entry.kind, (None, None))
        c1 = ws.cell(row=row, column=1, value=kind_label.get(entry.kind, entry.kind))
        c2 = ws.cell(row=row, column=2, value="\n".join(entry.before))
        c3 = ws.cell(row=row, column=3, value="\n".join(entry.after))
        for cell in (c1, c2, c3):
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if fill is not None:
                cell.fill = fill
                cell.font = font
        row += 1
    return row


def _build_detail_sheet_changed(
    wb: Workbook, sheet_name: str, status: PageStatus, pdf_a_path: str, pdf_b_path: str,
    pages_a: List[List[PageLine]], pages_b: List[List[PageLine]], dpi: int,
) -> Worksheet:
    ws = wb.create_sheet(sheet_name)
    ws.cell(row=1, column=1, value=f"ページ A{status.a_page + 1} / B{status.b_page + 1} 比較").font = Font(bold=True, size=14)
    ws.cell(row=2, column=1, value="サマリーへ戻る").hyperlink = "#'サマリー'!A1"
    ws.cell(row=2, column=1).font = Font(color="0563C1", underline="single")

    img_result = diff_page_pair(pdf_a_path, status.a_page, pdf_b_path, status.b_page, dpi=dpi)
    img_a = render_page(pdf_a_path, status.a_page, dpi=dpi)
    img_b = render_page(pdf_b_path, status.b_page, dpi=dpi)
    img_a = draw_highlights(img_a, img_result.regions, color="red")
    img_b = draw_highlights(img_b, img_result.regions, color="red")

    ws.cell(row=4, column=2, value="変更前(A)").font = _HEADER_FONT
    ws.cell(row=4, column=20, value="変更後(B)").font = _HEADER_FONT
    _embed_thumbnail(ws, img_a, "B5")
    _embed_thumbnail(ws, img_b, "T5")

    entries = diff_page_lines(pages_a[status.a_page], pages_b[status.b_page])
    if not entries and status.visual_only:
        ws.cell(row=70, column=1, value="テキストは同一です。画像(見た目)のみ差分があります。").font = Font(italic=True)
    else:
        _write_text_diff_table(ws, 70, entries)
    return ws


def _build_detail_sheet_single_side(
    wb: Workbook, sheet_name: str, status: PageStatus, pdf_path: str, page_index: int, side_label: str, dpi: int,
) -> Worksheet:
    ws = wb.create_sheet(sheet_name)
    ws.cell(row=1, column=1, value=f"ページ {side_label}{page_index + 1}({_STATUS_LABEL[status.status]})").font = Font(bold=True, size=14)
    ws.cell(row=2, column=1, value="サマリーへ戻る").hyperlink = "#'サマリー'!A1"
    ws.cell(row=2, column=1).font = Font(color="0563C1", underline="single")

    img = render_page(pdf_path, page_index, dpi=dpi)
    ws.cell(row=4, column=2, value=f"{side_label}側のみに存在するページ").font = _HEADER_FONT
    _embed_thumbnail(ws, img, "B5")
    return ws


def build_excel_report(
    pdf_a_path: str,
    pdf_b_path: str,
    pages_a: List[List[PageLine]],
    pages_b: List[List[PageLine]],
    alignment: AlignmentResult,
    output_path: str,
    dpi: int = 150,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> None:
    wb = Workbook()
    summary_ws = wb.active
    summary_ws.title = "サマリー"

    diff_counts: Dict[int, int] = {}
    for idx, status in enumerate(alignment.page_statuses):
        diff_counts[idx] = _diff_count_for(status, pages_a, pages_b)
    total_diff = sum(diff_counts.values())

    summary_ws.cell(row=1, column=1, value="ファイルA").font = _HEADER_FONT
    summary_ws.cell(row=1, column=2, value=pdf_a_path)
    summary_ws.cell(row=2, column=1, value="ファイルB").font = _HEADER_FONT
    summary_ws.cell(row=2, column=2, value=pdf_b_path)
    summary_ws.cell(row=3, column=1, value="比較日時").font = _HEADER_FONT
    summary_ws.cell(row=3, column=2, value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    summary_ws.cell(row=4, column=1, value="総ページ数(A/B)").font = _HEADER_FONT
    summary_ws.cell(row=4, column=2, value=f"{len(pages_a)} / {len(pages_b)}")
    summary_ws.cell(row=5, column=1, value="総差分件数").font = _HEADER_FONT
    summary_ws.cell(row=5, column=2, value=total_diff)

    header_row = 7
    headers = ["ページ番号A", "ページ番号B", "ステータス", "備考", "差分件数", "詳細シート"]
    for col, text in enumerate(headers, start=1):
        summary_ws.cell(row=header_row, column=col, value=text).font = _HEADER_FONT

    used_sheet_names: Set[str] = set()
    row = header_row + 1
    for idx, status in enumerate(alignment.page_statuses):
        a_disp: Optional[int] = status.a_page + 1 if status.a_page is not None else None
        b_disp: Optional[int] = status.b_page + 1 if status.b_page is not None else None
        notes = []
        if status.moved:
            notes.append("ページ移動")
        if status.visual_only:
            notes.append("見た目のみ")
        note = " / ".join(notes)

        summary_ws.cell(row=row, column=1, value=a_disp if a_disp is not None else "-")
        summary_ws.cell(row=row, column=2, value=b_disp if b_disp is not None else "-")
        summary_ws.cell(row=row, column=3, value=_STATUS_LABEL[status.status])
        summary_ws.cell(row=row, column=4, value=note)
        summary_ws.cell(row=row, column=5, value=diff_counts[idx])

        if status.status != "unchanged":
            sheet_name = _sheet_name_for(status, used_sheet_names)
            link_cell = summary_ws.cell(row=row, column=6, value=sheet_name)
            link_cell.hyperlink = f"#'{sheet_name}'!A1"
            link_cell.font = Font(color="0563C1", underline="single")

            if status.status == "changed" and status.a_page is not None and status.b_page is not None:
                _build_detail_sheet_changed(wb, sheet_name, status, pdf_a_path, pdf_b_path, pages_a, pages_b, dpi)
            elif status.status == "inserted" and status.b_page is not None:
                _build_detail_sheet_single_side(wb, sheet_name, status, pdf_b_path, status.b_page, "B", dpi)
            elif status.status == "deleted" and status.a_page is not None:
                _build_detail_sheet_single_side(wb, sheet_name, status, pdf_a_path, status.a_page, "A", dpi)
        row += 1

        if progress_callback:
            progress_callback(idx + 1, len(alignment.page_statuses))

    for col, width in zip("ABCDEF", (12, 12, 16, 10, 10, 20)):
        summary_ws.column_dimensions[col].width = width

    wb.save(output_path)
