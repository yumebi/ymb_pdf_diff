"""ページ範囲指定(#新機能8)の解析・整列remapを確認するテスト。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ymb_pdf_diff.core import PageLine, align_documents_in_range, parse_page_range


def _make_lines(page: int, texts):
    return [PageLine(page=page, text=t) for t in texts]


def test_parse_page_range_valid_specs():
    assert parse_page_range("3", 10) == [2]
    assert parse_page_range("1-3", 10) == [0, 1, 2]
    assert parse_page_range("1-2,5", 10) == [0, 1, 4]
    assert parse_page_range("1-3,7,9-12", 12) == [0, 1, 2, 6, 8, 9, 10, 11]
    # 重複・逆順に指定しても昇順・重複なしで返す
    assert parse_page_range("5,1-3,3", 10) == [0, 1, 2, 4]
    print("OK: test_parse_page_range_valid_specs")


def test_parse_page_range_invalid_specs():
    bad_specs = ["0", "abc", "5-2", "100", "1-100", "", "  ", "1-", "-3"]
    for spec in bad_specs:
        try:
            parse_page_range(spec, 10)
        except ValueError:
            continue
        raise AssertionError(f"ValueErrorが送出されるべき: '{spec}'")
    print("OK: test_parse_page_range_invalid_specs")


def test_align_documents_in_range_remaps_to_original_indices():
    # file A: 4ページ、file B: 4ページ。2-3ページ目(0始まり index 1,2)だけを範囲指定する。
    pages_a = [
        _make_lines(0, ["A_P1"]),
        _make_lines(1, ["A_P2_before"]),
        _make_lines(2, ["A_P3_same"]),
        _make_lines(3, ["A_P4"]),
    ]
    pages_b = [
        _make_lines(0, ["B_P1"]),
        _make_lines(1, ["A_P2_after"]),
        _make_lines(2, ["A_P3_same"]),
        _make_lines(3, ["B_P4"]),
    ]

    indices_a = [1, 2]  # 元のページ番号(0始まり) = 2ページ目・3ページ目
    indices_b = [1, 2]

    result = align_documents_in_range(pages_a, pages_b, indices_a, indices_b)
    statuses = {s.a_page: s for s in result.page_statuses if s.a_page is not None}

    # a_page/b_pageが元のページ番号(1,2)にremapされていること(スライス後のローカル番号0,1ではない)
    assert set(statuses.keys()) == {1, 2}
    assert statuses[1].b_page == 1
    assert statuses[2].b_page == 2
    assert statuses[1].status == "changed"
    assert statuses[2].status == "unchanged"

    print("OK: test_align_documents_in_range_remaps_to_original_indices")


if __name__ == "__main__":
    test_parse_page_range_valid_specs()
    test_parse_page_range_invalid_specs()
    test_align_documents_in_range_remaps_to_original_indices()
