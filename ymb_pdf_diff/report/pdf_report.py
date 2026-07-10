"""PDFレポート出力(#新機能10)。

Excelレポートと同じ情報を、Excelを開かなくても閲覧・印刷しやすいPDF1枚ものとして出力する。
追加の依存ライブラリは入れず、PyMuPDF(fitz)だけでPDFを新規生成する。
"""
import io
from datetime import datetime
from typing import Callable, List, Optional

import fitz  # PyMuPDF
from PIL import Image

from ..core import (
    AlignmentResult,
    PageLine,
    PageStatus,
    diff_page_pair,
    draw_highlights,
    render_page,
)
from .image_size import DEFAULT_IMAGE_SIZE, resolve_long_edge_max_px

_FONT = "japan"  # 日本語を描画するための組み込みCJKフォント名

_STATUS_LABEL = {
    "unchanged": "差分なし",
    "changed": "差分あり",
    "inserted": "追加ページ(Bのみ)",
    "deleted": "削除ページ(Aのみ)",
}

_PORTRAIT = fitz.paper_rect("a4")
_LANDSCAPE_WIDTH = _PORTRAIT.height
_LANDSCAPE_HEIGHT = _PORTRAIT.width
_JPEG_QUALITY = 85  # 埋め込みJPEGの画質(#新機能11)。PNGよりはるかに小さく、見た目の劣化も目立たない

_SUMMARY_MARGIN_X = 56
_SUMMARY_LIST_TOP = 230
_SUMMARY_LIST_BOTTOM = 800
_SUMMARY_LINE_HEIGHT = 15


def _shrink_for_embed(image: Image.Image, max_dim: int) -> bytes:
    """埋め込み前にサムネイル化(長辺max_dimまで)し、JPEGバイト列にして返す。

    ページ描画のような写真的でない(アンチエイリアスのかかった線・文字主体の)画像でも、
    PNGよりJPEGの方が大幅に小さくなるため(#新機能11でPNGから変更)、JPEGで保存する。
    """
    thumb = image.copy()
    if max(thumb.size) > max_dim:
        thumb.thumbnail((max_dim, max_dim))
    if thumb.mode != "RGB":
        thumb = thumb.convert("RGB")
    buf = io.BytesIO()
    thumb.save(buf, format="JPEG", quality=_JPEG_QUALITY)
    return buf.getvalue()


def _status_line(status: PageStatus) -> str:
    a_disp = status.a_page + 1 if status.a_page is not None else "-"
    b_disp = status.b_page + 1 if status.b_page is not None else "-"
    moved_tag = "(ページ移動)" if status.moved else ""
    visual_tag = "(見た目のみ)" if status.visual_only else ""
    return f"A{a_disp} <-> B{b_disp}  [{_STATUS_LABEL[status.status]}]{moved_tag}{visual_tag}"


def _build_summary_pages(
    doc: "fitz.Document",
    pdf_a_path: str,
    pdf_b_path: str,
    pages_a: List[List[PageLine]],
    pages_b: List[List[PageLine]],
    alignment: AlignmentResult,
) -> None:
    page = doc.new_page(width=_PORTRAIT.width, height=_PORTRAIT.height)
    page.insert_text((_SUMMARY_MARGIN_X, 80), "PDF差分レポート", fontname=_FONT, fontsize=24)

    total_diff = len(alignment.changed_pages())
    info_lines = [
        f"ファイルA: {pdf_a_path}",
        f"ファイルB: {pdf_b_path}",
        f"作成日時: {datetime.now():%Y-%m-%d %H:%M:%S}",
        f"総ページ数(A/B): {len(pages_a)} / {len(pages_b)}",
        f"差分件数: {total_diff}",
    ]
    y = 120
    for line in info_lines:
        page.insert_text((_SUMMARY_MARGIN_X, y), line, fontname=_FONT, fontsize=11)
        y += 18

    page.insert_text(
        (_SUMMARY_MARGIN_X, _SUMMARY_LIST_TOP - 20), "ページ別ステータス一覧", fontname=_FONT, fontsize=13
    )

    y = _SUMMARY_LIST_TOP
    for status in alignment.page_statuses:
        if y > _SUMMARY_LIST_BOTTOM:
            page = doc.new_page(width=_PORTRAIT.width, height=_PORTRAIT.height)
            y = 60
        page.insert_text((_SUMMARY_MARGIN_X, y), _status_line(status), fontname=_FONT, fontsize=10)
        y += _SUMMARY_LINE_HEIGHT


def _build_changed_page(
    doc: "fitz.Document", status: PageStatus, pdf_a_path: str, pdf_b_path: str, dpi: int, threshold: int, max_dim: int
) -> None:
    page = doc.new_page(width=_LANDSCAPE_WIDTH, height=_LANDSCAPE_HEIGHT)
    page.insert_text((30, 30), _status_line(status), fontname=_FONT, fontsize=13)

    # 画像差分の感度(#新機能7)。呼び出し元(build_pdf_report)経由でGUIの設定値を受け取る。
    img_result = diff_page_pair(pdf_a_path, status.a_page, pdf_b_path, status.b_page, dpi=dpi, threshold=threshold)
    img_a = draw_highlights(render_page(pdf_a_path, status.a_page, dpi=dpi), img_result.regions, color="red")
    img_b = draw_highlights(render_page(pdf_b_path, status.b_page, dpi=dpi), img_result.regions, color="red")

    half_width = (_LANDSCAPE_WIDTH - 60) / 2
    rect_a = fitz.Rect(20, 50, 20 + half_width, _LANDSCAPE_HEIGHT - 20)
    rect_b = fitz.Rect(40 + half_width, 50, 40 + half_width * 2, _LANDSCAPE_HEIGHT - 20)
    page.insert_image(rect_a, stream=_shrink_for_embed(img_a, max_dim))
    page.insert_image(rect_b, stream=_shrink_for_embed(img_b, max_dim))


def _build_single_side_page(
    doc: "fitz.Document", status: PageStatus, pdf_path: str, page_index: int, side_label: str, dpi: int, max_dim: int
) -> None:
    page = doc.new_page(width=_LANDSCAPE_WIDTH, height=_LANDSCAPE_HEIGHT)
    header = f"{side_label}{page_index + 1}  [{_STATUS_LABEL[status.status]}]"
    page.insert_text((30, 30), header, fontname=_FONT, fontsize=13)

    img = render_page(pdf_path, page_index, dpi=dpi)
    width = _LANDSCAPE_WIDTH * 0.6
    x0 = (_LANDSCAPE_WIDTH - width) / 2
    rect = fitz.Rect(x0, 50, x0 + width, _LANDSCAPE_HEIGHT - 20)
    page.insert_image(rect, stream=_shrink_for_embed(img, max_dim))


def build_pdf_report(
    pdf_a_path: str,
    pdf_b_path: str,
    pages_a: List[List[PageLine]],
    pages_b: List[List[PageLine]],
    alignment: AlignmentResult,
    output_path: str,
    dpi: int = 150,
    threshold: int = 30,
    image_size: str = DEFAULT_IMAGE_SIZE,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> None:
    """比較結果をPDFレポートとして書き出す。

    1ページ目はサマリー(タイトル・ファイル情報・全ページのステータス一覧、
    一覧が入りきらない場合はサマリーの続きページを追加する)。
    続けて、差分のあるページ(status != "unchanged")ごとにA4横向き1ページを割り当てる。
    A/B両方に存在するページはキャプチャ(差分ハイライト付き)を左右に並べ、
    片側のみに存在するページ(inserted/deleted)は1枚だけを中央に表示する。
    埋め込み画像はimage_size(#新機能11、"small"/"medium"/"large")に応じた長辺サイズへ
    縮小し、JPEGとして埋め込むことでファイルサイズを抑える。
    thresholdは画像差分の感度(0-100、小さいほど敏感。GUIの表示設定と同じ値を渡せる)。
    """
    max_dim = resolve_long_edge_max_px(image_size)
    doc = fitz.open()
    try:
        _build_summary_pages(doc, pdf_a_path, pdf_b_path, pages_a, pages_b, alignment)

        total = len(alignment.page_statuses)
        for i, status in enumerate(alignment.page_statuses):
            if status.status == "changed" and status.a_page is not None and status.b_page is not None:
                _build_changed_page(doc, status, pdf_a_path, pdf_b_path, dpi, threshold, max_dim)
            elif status.status == "inserted" and status.b_page is not None:
                _build_single_side_page(doc, status, pdf_b_path, status.b_page, "B", dpi, max_dim)
            elif status.status == "deleted" and status.a_page is not None:
                _build_single_side_page(doc, status, pdf_a_path, status.a_page, "A", dpi, max_dim)

            if progress_callback:
                progress_callback(i + 1, total)

        doc.save(output_path)
    finally:
        doc.close()
