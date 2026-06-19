"""1文挿入によるページズレで、無関係なページまで差分扱いにならないことを確認する回帰テスト。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ymb_pdf_diff.core import PageLine, align_documents


def make_lines(page: int, texts):
    return [PageLine(page=page, text=t) for t in texts]


def test_single_insertion_does_not_mark_downstream_pages_as_changed():
    # file A: 2ページ x 5行
    pages_a = [
        make_lines(0, ["P1L1", "P1L2", "P1L3", "P1L4", "P1L5"]),
        make_lines(1, ["P2L1", "P2L2", "P2L3", "P2L4", "P2L5"]),
    ]
    # file B: 先頭に1行追加 → 5行/ページの固定ページ送りで以降が1行分ズレる
    flat_b = ["NEW SENTENCE"] + [
        "P1L1", "P1L2", "P1L3", "P1L4", "P1L5", "P2L1", "P2L2", "P2L3", "P2L4", "P2L5"
    ]
    pages_b = []
    for i, t in enumerate(flat_b):
        page = i // 5
        while len(pages_b) <= page:
            pages_b.append([])
        pages_b[page].append(PageLine(page=page, text=t))

    result = align_documents(pages_a, pages_b)
    statuses = {s.a_page: s for s in result.page_statuses if s.a_page is not None}

    assert statuses[0].status == "changed", "新しい文が入ったページは差分ありになるべき"
    assert statuses[1].status == "unchanged", "内容が変わっていない後続ページは差分なしのままであるべき"

    print("OK: single_insertion_does_not_mark_downstream_pages_as_changed")


if __name__ == "__main__":
    test_single_insertion_does_not_mark_downstream_pages_as_changed()
