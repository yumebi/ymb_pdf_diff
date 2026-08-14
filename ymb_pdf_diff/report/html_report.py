"""HTML差分レポート出力(#新機能13)。

Excel/PDFレポートの内容を、追加ツールなしでブラウザから閲覧・印刷できる
単一ファイルのHTMLとして書き出す。画像は埋め込まず、ページ別ステータス一覧と
各変更ページのテキスト差分(種別ごとの背景色つき)を中心に構成する。
"""
import html
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

_KIND_LABEL = {"replace": "変更", "insert": "追加", "delete": "削除"}
_KIND_BG = {"replace": "#FFEB9C", "insert": "#C6EFCE", "delete": "#FFC7CE"}
_KIND_FG = {"replace": "#9C6500", "insert": "#006100", "delete": "#9C0006"}

_CSS = """
body { font-family: "Yu Gothic UI", "Hiragino Sans", sans-serif; margin: 24px; color: #222; }
h1 { font-size: 22px; }
h2 { font-size: 16px; margin-top: 28px; }
table { border-collapse: collapse; width: 100%; margin-top: 8px; }
th, td { border: 1px solid #999; padding: 4px 8px; font-size: 13px; vertical-align: top; }
th { background: #f0f0f0; text-align: left; }
.info td:first-child { width: 180px; background: #f7f7f7; font-weight: bold; }
tr.changed { background: #FFF7E6; }
tr.inserted { background: #EDF7EE; }
tr.deleted { background: #FCECEE; }
.diff-entry { margin: 4px 0; padding: 6px 8px; border: 1px solid #ddd; font-size: 13px; white-space: pre-wrap; }
.diff-entry .kind { font-weight: bold; margin-right: 6px; }
.note { color: #666; font-style: italic; }
@media print { body { margin: 0; } h2 { page-break-before: always; } }
"""


def _status_note(status: PageStatus) -> str:
    notes = []
    if status.moved:
        notes.append("ページ移動")
    if status.visual_only:
        notes.append("見た目のみ")
    return " / ".join(notes)


def _status_row_html(status: PageStatus, diff_count: int) -> str:
    a_disp = status.a_page + 1 if status.a_page is not None else "-"
    b_disp = status.b_page + 1 if status.b_page is not None else "-"
    note = _status_note(status)
    return (
        f'<tr class="{status.status}">'
        f"<td>{a_disp}</td><td>{b_disp}</td>"
        f"<td>{_STATUS_LABEL[status.status]}</td>"
        f"<td>{html.escape(note)}</td>"
        f"<td>{diff_count}</td></tr>"
    )


def _diff_section_html(status: PageStatus, entries) -> str:
    a_disp = status.a_page + 1 if status.a_page is not None else "-"
    b_disp = status.b_page + 1 if status.b_page is not None else "-"
    parts = [f"<h2>ページ A{a_disp} / B{b_disp} のテキスト差分</h2>"]

    if not entries and status.visual_only:
        parts.append('<p class="note">テキストは同一です。画像(見た目)のみ差分があります。</p>')
        return "".join(parts)
    if not entries:
        parts.append('<p class="note">差分なし</p>')
        return "".join(parts)

    for entry in entries:
        bg = _KIND_BG.get(entry.kind, "#ffffff")
        fg = _KIND_FG.get(entry.kind, "#222222")
        kind = _KIND_LABEL.get(entry.kind, entry.kind)
        before = html.escape("\n".join(entry.before)) or "(なし)"
        after = html.escape("\n".join(entry.after)) or "(なし)"
        parts.append(
            f'<div class="diff-entry" style="background:{bg};color:{fg};">'
            f'<span class="kind">[{kind}]</span>'
            f"変更前: {before}<br>変更後: {after}</div>"
        )
    return "".join(parts)


def build_html_report(
    pdf_a_path: str,
    pdf_b_path: str,
    pages_a: List[List[PageLine]],
    pages_b: List[List[PageLine]],
    alignment: AlignmentResult,
    output_path: str,
    dpi: int = 150,  # Excel/PDFレポートと同一シグネチャを維持するため受け取る
    threshold: int = 30,  # 同上
    image_size: str = "medium",  # 同上
    shift_tolerance: int = 0,  # 同上
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> None:
    """比較結果を単一ファイルのHTMLとして書き出す。

    冒頭にファイル情報・集計値、ページ別ステータス一覧(Excel/PDFレポートのサマリー相当)、
    続けて各変更ページのテキスト差分(種別ごとの背景色つき)を出力する。
    dpi/threshold/image_size/shift_toleranceはExcel/PDFレポートと同一シグネチャを
    維持するために受け取るだけで、画像を含まないHTMLでは使用しない。
    ブラウザで開いてそのまま印刷できるよう、CSSはすべてインラインで埋め込む。
    """
    out_path = Path(output_path)
    if out_path.suffix.lower() not in (".html", ".htm"):
        out_path = out_path.with_suffix(".html")

    total_diff = len(alignment.changed_pages())

    info_rows = [
        ("ファイルA", pdf_a_path),
        ("ファイルB", pdf_b_path),
        ("比較日時", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("総ページ数(A/B)", f"{len(pages_a)} / {len(pages_b)}"),
        ("総差分件数", str(total_diff)),
    ]
    info_html = "".join(f"<tr><td>{k}</td><td>{html.escape(v)}</td></tr>" for k, v in info_rows)

    body_rows: List[str] = []
    for idx, status in enumerate(alignment.page_statuses):
        diff_count = (
            len(diff_page_lines(pages_a[status.a_page], pages_b[status.b_page]))
            if status.status == "changed" and status.a_page is not None and status.b_page is not None
            else (1 if status.status in ("inserted", "deleted") else 0)
        )
        body_rows.append(_status_row_html(status, diff_count))
        if progress_callback:
            progress_callback(idx + 1, len(alignment.page_statuses))

    summary_html = "".join(body_rows)

    detail_parts: List[str] = []
    for status in alignment.page_statuses:
        if status.status == "changed" and status.a_page is not None and status.b_page is not None:
            entries = diff_page_lines(pages_a[status.a_page], pages_b[status.b_page])
            detail_parts.append(_diff_section_html(status, entries))

    document = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>PDF差分レポート</title>
<style>{_CSS}</style>
</head>
<body>
<h1>PDF差分レポート</h1>
<table class="info">{info_html}</table>
<h2>ページ別ステータス一覧</h2>
<table>
<thead><tr><th>ページ番号A</th><th>ページ番号B</th><th>ステータス</th><th>備考</th><th>差分件数</th></tr></thead>
<tbody>{summary_html}</tbody>
</table>
{"".join(detail_parts)}
</body>
</html>
"""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(document, encoding="utf-8")
