import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fitz

from ymb_pdf_diff.core import align_documents, load_pdf_pages
from ymb_pdf_diff.session import load_session, save_session


def _make_sample_pdfs(tmp_dir: Path):
    doc_a = fitz.open()
    doc_a.new_page().insert_text((72, 72), "Page A1 alpha text here.")
    doc_a.new_page().insert_text((72, 72), "Page A2 beta text here unchanged.")
    path_a = tmp_dir / "session_sample_a.pdf"
    doc_a.save(str(path_a))

    doc_b = fitz.open()
    doc_b.new_page().insert_text((72, 72), "Page A1 alpha text here CHANGED.")
    doc_b.new_page().insert_text((72, 72), "Page A2 beta text here unchanged.")
    path_b = tmp_dir / "session_sample_b.pdf"
    doc_b.save(str(path_b))
    return path_a, path_b


def test_save_and_load_session_round_trip():
    tmp_dir = Path(__file__).resolve().parent.parent
    path_a, path_b = _make_sample_pdfs(tmp_dir)
    session_path = tmp_dir / "session_sample.ymbdiff"
    try:
        pages_a = load_pdf_pages(str(path_a))
        pages_b = load_pdf_pages(str(path_b))
        alignment = align_documents(pages_a, pages_b)

        save_session(str(session_path), str(path_a), str(path_b), pages_a, pages_b, alignment)
        assert session_path.exists()

        loaded = load_session(str(session_path))
        statuses = loaded.page_statuses()
        assert len(statuses) == len(alignment.page_statuses)
        assert [s.status for s in statuses] == [s.status for s in alignment.page_statuses]

        changed_idx = next(i for i, s in enumerate(statuses) if s.status == "changed")
        unchanged_idx = next(i for i, s in enumerate(statuses) if s.status == "unchanged")

        entries = loaded.text_diff_for(changed_idx)
        assert len(entries) == 1
        assert entries[0].kind == "replace"

        img_a = loaded.capture_image(changed_idx, "a")
        img_b = loaded.capture_image(changed_idx, "b")
        assert img_a is not None and img_b is not None

        # 未変更ページはキャプチャを保存しない(ファイルサイズ削減)
        assert loaded.capture_image(unchanged_idx, "a") is None

        print("OK: test_save_and_load_session_round_trip")
    finally:
        path_a.unlink(missing_ok=True)
        path_b.unlink(missing_ok=True)
        session_path.unlink(missing_ok=True)


if __name__ == "__main__":
    test_save_and_load_session_round_trip()
