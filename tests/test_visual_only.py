"""テキストは同一だが見た目(画像)だけ違うページが、align_documents単独では
見逃されること、detect_visual_only_changesで正しく検出されることを確認する回帰テスト。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fitz

from ymb_pdf_diff.core import align_documents, detect_visual_only_changes, load_pdf_pages


def _build(path: Path, box_color: tuple) -> None:
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((72, 72), "Page one identical text and identical visual.")
    p2 = doc.new_page()
    p2.insert_text((72, 72), "Page two identical text but the box color differs.")
    p2.draw_rect(fitz.Rect(72, 120, 300, 220), color=box_color, fill=box_color, width=0)
    doc.save(str(path))
    doc.close()


def test_visual_only_change_is_missed_by_text_alignment_alone():
    tmp_dir = Path(__file__).resolve().parent.parent
    path_a = tmp_dir / "visual_only_a.pdf"
    path_b = tmp_dir / "visual_only_b.pdf"
    try:
        _build(path_a, (0, 0, 1))
        _build(path_b, (1, 0, 0))

        pages_a = load_pdf_pages(str(path_a))
        pages_b = load_pdf_pages(str(path_b))
        alignment = align_documents(pages_a, pages_b)

        # テキストだけでは両ページとも「差分なし」になってしまう(既知の限界)
        assert all(s.status == "unchanged" for s in alignment.page_statuses)

        detect_visual_only_changes(alignment, str(path_a), str(path_b))

        statuses = {s.a_page: s for s in alignment.page_statuses}
        assert statuses[0].status == "unchanged"
        assert statuses[0].visual_only is False
        assert statuses[1].status == "changed"
        assert statuses[1].visual_only is True

        print("OK: test_visual_only_change_is_missed_by_text_alignment_alone")
    finally:
        path_a.unlink(missing_ok=True)
        path_b.unlink(missing_ok=True)


if __name__ == "__main__":
    test_visual_only_change_is_missed_by_text_alignment_alone()
