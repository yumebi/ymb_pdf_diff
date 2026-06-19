import difflib
from collections import Counter
from typing import Callable, List, Optional, Set, Tuple

from .image_diff import diff_page_pair
from .models import PageLine, PageStatus


class AlignmentResult:
    def __init__(self, page_statuses: List[PageStatus]):
        self.page_statuses = page_statuses

    def changed_pages(self) -> List[PageStatus]:
        return [p for p in self.page_statuses if p.status != "unchanged"]


def _flatten(pages: List[List[PageLine]]) -> List[PageLine]:
    return [line for page_lines in pages for line in page_lines]


def align_documents(pages_a: List[List[PageLine]], pages_b: List[List[PageLine]]) -> AlignmentResult:
    """文書全体を1本の行シーケンスとして整列し、ページ番号のズレに強いページ対応表を作る。

    equalブロックの行ペアから「本来比べるべきページ同士」を多数決で決定するため、
    1文の増減でページ構成がズレても、実際に内容が変わったページだけが changed になる。
    """
    seq_a = _flatten(pages_a)
    seq_b = _flatten(pages_b)
    matcher = difflib.SequenceMatcher(a=[l.text for l in seq_a], b=[l.text for l in seq_b], autojunk=False)
    opcodes = matcher.get_opcodes()

    equal_pair_count: Counter = Counter()
    changed_pages_a: Set[int] = set()
    changed_pages_b: Set[int] = set()
    block_pairs: List[Tuple[Set[int], Set[int]]] = []

    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            for offset in range(i2 - i1):
                a_page = seq_a[i1 + offset].page
                b_page = seq_b[j1 + offset].page
                equal_pair_count[(a_page, b_page)] += 1
        else:
            pages_a_in_block = {seq_a[k].page for k in range(i1, i2)}
            pages_b_in_block = {seq_b[k].page for k in range(j1, j2)}
            changed_pages_a |= pages_a_in_block
            changed_pages_b |= pages_b_in_block
            block_pairs.append((pages_a_in_block, pages_b_in_block))

    def best_equal_match(a_page: int) -> Optional[int]:
        candidates = {b: c for (a, b), c in equal_pair_count.items() if a == a_page}
        if not candidates:
            return None
        return max(candidates, key=candidates.get)

    def fallback_match(a_page: int) -> Optional[int]:
        for pages_a_in_block, pages_b_in_block in block_pairs:
            if a_page in pages_a_in_block and pages_b_in_block:
                sorted_a = sorted(pages_a_in_block)
                sorted_b = sorted(pages_b_in_block)
                idx = min(sorted_a.index(a_page), len(sorted_b) - 1)
                return sorted_b[idx]
        return None

    mapped_b_used: Set[int] = set()
    page_statuses: List[PageStatus] = []

    for a_page in range(len(pages_a)):
        b_page = best_equal_match(a_page)
        if b_page is None:
            b_page = fallback_match(a_page)

        if b_page is None:
            status = "deleted"
        elif a_page in changed_pages_a or b_page in changed_pages_b:
            status = "changed"
        else:
            status = "unchanged"

        moved = b_page is not None and b_page != a_page
        page_statuses.append(PageStatus(a_page=a_page, b_page=b_page, status=status, moved=moved))
        if b_page is not None:
            mapped_b_used.add(b_page)

    for b_page in range(len(pages_b)):
        if b_page not in mapped_b_used:
            page_statuses.append(PageStatus(a_page=None, b_page=b_page, status="inserted", moved=False))

    big = len(pages_a) + len(pages_b) + 1
    page_statuses.sort(key=lambda p: (p.a_page if p.a_page is not None else big, p.b_page if p.b_page is not None else big))
    return AlignmentResult(page_statuses)


def detect_visual_only_changes(
    alignment: AlignmentResult,
    pdf_a_path: str,
    pdf_b_path: str,
    dpi: int = 150,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> None:
    """テキストは同一でも見た目(画像)が異なるページを検出し、statusを"changed"に格上げする(in-place)。

    align_documentsはテキストのみで判定するため、画像・図表・色だけが変わったページは
    そのままだと見逃される。テキスト一致で"unchanged"になった全ページ対を画素比較し直す。
    """
    total = len(alignment.page_statuses)
    for i, status in enumerate(alignment.page_statuses):
        if status.status == "unchanged" and status.a_page is not None and status.b_page is not None:
            result = diff_page_pair(pdf_a_path, status.a_page, pdf_b_path, status.b_page, dpi=dpi)
            if result.has_diff:
                status.status = "changed"
                status.visual_only = True
        if progress_callback:
            progress_callback(i + 1, total)
