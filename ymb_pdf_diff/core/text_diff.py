import difflib
from typing import List

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
