import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ymb_pdf_diff.core.text_diff import char_diff_segments


def test_identical_strings_produce_single_equal_segment():
    segs_a, segs_b = char_diff_segments("Hello world", "Hello world")
    assert segs_a == [("equal", "Hello world")]
    assert segs_b == [("equal", "Hello world")]
    print("OK: test_identical_strings_produce_single_equal_segment")


def test_one_char_change_marks_only_that_region_as_diff():
    segs_a, segs_b = char_diff_segments("Hello world", "Hallo world")
    # "e"->"a" の1文字だけがdiffになり、前後は一致(equal)のまま残るはず
    assert [kind for kind, _ in segs_a] == ["equal", "diff", "equal"]
    assert [kind for kind, _ in segs_b] == ["equal", "diff", "equal"]
    diff_text_a = "".join(text for kind, text in segs_a if kind == "diff")
    diff_text_b = "".join(text for kind, text in segs_b if kind == "diff")
    assert diff_text_a == "e"
    assert diff_text_b == "a"
    print("OK: test_one_char_change_marks_only_that_region_as_diff")


def test_empty_vs_text_works():
    segs_a, segs_b = char_diff_segments("", "new text")
    assert segs_a == []
    assert segs_b == [("diff", "new text")]

    segs_a2, segs_b2 = char_diff_segments("old text", "")
    assert segs_a2 == [("diff", "old text")]
    assert segs_b2 == []
    print("OK: test_empty_vs_text_works")


if __name__ == "__main__":
    test_identical_strings_produce_single_equal_segment()
    test_one_char_change_marks_only_that_region_as_diff()
    test_empty_vs_text_works()
