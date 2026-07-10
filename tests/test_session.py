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


def test_session_captures_are_jpeg_and_respect_image_size():
    """#新機能11: セッションのキャプチャはPNGではなく.jpg名で保存され、
    image_sizeプリセットに応じて長辺サイズが変わり、load_session/capture_imageで
    問題なく読み込めることを確認する。
    """
    tmp_dir = Path(__file__).resolve().parent.parent
    path_a, path_b = _make_sample_pdfs(tmp_dir)
    session_small = tmp_dir / "session_sample_small.ymbdiff"
    session_large = tmp_dir / "session_sample_large.ymbdiff"
    try:
        pages_a = load_pdf_pages(str(path_a))
        pages_b = load_pdf_pages(str(path_b))
        alignment = align_documents(pages_a, pages_b)

        save_session(
            str(session_small), str(path_a), str(path_b), pages_a, pages_b, alignment, image_size="small"
        )
        save_session(
            str(session_large), str(path_a), str(path_b), pages_a, pages_b, alignment, image_size="large"
        )

        loaded_small = load_session(str(session_small))
        loaded_large = load_session(str(session_large))

        changed_idx = next(i for i, s in enumerate(loaded_small.page_statuses()) if s.status == "changed")

        # captures/*.jpgという名前でzipに保存されているはず(.pngではない)
        name_small = loaded_small.meta["page_statuses"][changed_idx]["capture_a"]
        assert name_small.endswith(".jpg")

        img_small = loaded_small.capture_image(changed_idx, "a")
        img_large = loaded_large.capture_image(changed_idx, "a")
        assert img_small is not None and img_large is not None
        assert img_small.format == "JPEG"

        # largeプリセットの方がsmallより長辺が大きい(縮小の上限が違う)
        assert max(img_large.size) >= max(img_small.size)

        print("OK: test_session_captures_are_jpeg_and_respect_image_size")
    finally:
        path_a.unlink(missing_ok=True)
        path_b.unlink(missing_ok=True)
        session_small.unlink(missing_ok=True)
        session_large.unlink(missing_ok=True)


if __name__ == "__main__":
    test_save_and_load_session_round_trip()
    test_session_captures_are_jpeg_and_respect_image_size()
