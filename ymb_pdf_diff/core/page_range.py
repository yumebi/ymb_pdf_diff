"""ページ範囲指定による比較対象の絞り込み(#新機能8)。

「3-10」「5」「1-3,7,9-12」のようなカンマ区切り・1始まり両端含む形式の文字列を解析し、
align_documentsを部分的なページ集合だけに対して実行できるようにする。
"""
from typing import List, Set

from .aligner import AlignmentResult, align_documents
from .models import PageLine


def parse_page_range(spec: str, page_count: int) -> List[int]:
    """"3-10" "5" "1-3,7,9-12" 形式のページ範囲指定を解析する。

    1始まり・両端を含む区間指定をカンマ区切りで並べたものを受け付け、
    0始まりのページインデックス一覧(重複なし・昇順)を返す。
    書式が不正、またはpage_countの範囲外を指定した場合はValueError(日本語メッセージ)を送出する。
    """
    if spec is None or not spec.strip():
        raise ValueError("ページ範囲が指定されていません。")

    indices: Set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue

        if "-" in part:
            bounds = part.split("-")
            if len(bounds) != 2 or not bounds[0].strip().isdigit() or not bounds[1].strip().isdigit():
                raise ValueError(f"ページ範囲の指定が不正です: '{part}'")
            start, end = int(bounds[0].strip()), int(bounds[1].strip())
            if start < 1 or end < 1:
                raise ValueError(f"ページ番号は1以上を指定してください: '{part}'")
            if start > end:
                raise ValueError(f"ページ範囲の開始が終了より大きいです: '{part}'")
            if end > page_count:
                raise ValueError(f"ページ番号が総ページ数({page_count})を超えています: '{part}'")
            indices.update(range(start - 1, end))
        else:
            if not part.isdigit():
                raise ValueError(f"ページ範囲の指定が不正です: '{part}'")
            page = int(part)
            if page < 1:
                raise ValueError(f"ページ番号は1以上を指定してください: '{part}'")
            if page > page_count:
                raise ValueError(f"ページ番号が総ページ数({page_count})を超えています: '{part}'")
            indices.add(page - 1)

    if not indices:
        raise ValueError("ページ範囲が指定されていません。")

    return sorted(indices)


def slice_pages(pages: List[List[PageLine]], indices: List[int]) -> List[List[PageLine]]:
    """指定したページ(0始まりインデックス)だけを抜き出したページリストを作る。

    align_documentsはPageLine.pageの値をそのまま「本来のページ番号」として扱い、
    range(len(pages))でページ配列にアクセスするため、元のページ番号のままスライスすると
    インデックスとPageLine.pageの値がズレてしまう。そのためスライス後のローカルな
    連番(0始まり)へPageLine.pageを振り直す。
    """
    sliced: List[List[PageLine]] = []
    for local_index, orig_index in enumerate(indices):
        sliced.append(
            [PageLine(page=local_index, text=line.text, bbox=line.bbox) for line in pages[orig_index]]
        )
    return sliced


def align_documents_in_range(
    pages_a: List[List[PageLine]],
    pages_b: List[List[PageLine]],
    indices_a: List[int],
    indices_b: List[int],
) -> AlignmentResult:
    """指定範囲(0始まりインデックス一覧)だけを整列し、結果のページ番号を元のページ番号に戻す。

    detect_visual_only_changesは元PDFファイルをa_page/b_pageのインデックスで再描画するため、
    この関数の戻り値(=ページ番号がすでに元に戻っている状態)を渡してから呼び出すこと。
    """
    sub_a = slice_pages(pages_a, indices_a)
    sub_b = slice_pages(pages_b, indices_b)
    result = align_documents(sub_a, sub_b)
    for status in result.page_statuses:
        if status.a_page is not None:
            status.a_page = indices_a[status.a_page]
        if status.b_page is not None:
            status.b_page = indices_b[status.b_page]
    return result
