import difflib
from typing import List, Tuple

from .models import DiffEntry, PageLine


def diff_page_lines(lines_a: List[PageLine], lines_b: List[PageLine]) -> List[DiffEntry]:
    """対応付け済みの1ページ分の行リストどうしで、行単位のテキスト差異を抽出する。"""
    text_a = [l.text for l in lines_a]
    text_b = [l.text for l in lines_b]
    matcher = difflib.SequenceMatcher(a=text_a, b=text_b, autojunk=False)

    entries: List[DiffEntry] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        entries.append(DiffEntry(kind=tag, before=text_a[i1:i2], after=text_b[j1:j2]))
    return entries


def char_diff_segments(a: str, b: str) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    """"replace"種別の行内で、文字単位でどこが変わったかをセグメント列として返す。

    difflib.SequenceMatcherを文字列(=文字のシーケンス)に対して使い、
    A側・B側それぞれについて [(種別, テキスト), ...] を返す。種別は "equal" | "diff"。
    呼び出し側でセグメントごとにスタイルを変えれば、行内のどこが変わったかを強調表示できる。
    """
    matcher = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    segments_a: List[Tuple[str, str]] = []
    segments_b: List[Tuple[str, str]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        kind = "equal" if tag == "equal" else "diff"
        if i2 > i1:
            segments_a.append((kind, a[i1:i2]))
        if j2 > j1:
            segments_b.append((kind, b[j1:j2]))
    return segments_a, segments_b
