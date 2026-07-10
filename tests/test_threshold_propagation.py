"""画像差分の感度(threshold)設定が、GUIの比較処理だけでなく
Excel/PDFレポート出力・セッション保存・CLIの各出力経路にも伝播することを確認する回帰テスト。

薄いグレーの矩形(RGB(230,230,230) on 白)を使う。ImageChops.differenceでの差分量は
255-230=25になるため、threshold=30(デフォルト)では検出されず、threshold=10では検出される
――という「見た目のみの差分」を題材に、各エントリポイントがthresholdを実際に
diff_page_pair/detect_visual_only_changesへ渡していることを検証する。
"""
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fitz

from ymb_pdf_diff.core import align_documents, detect_visual_only_changes, load_pdf_pages
from ymb_pdf_diff.core.image_diff import diff_page_pair as real_diff_page_pair
from ymb_pdf_diff.report import build_excel_report, build_pdf_report
from ymb_pdf_diff.session import save_session

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 白背景に対して差分量25になる薄いグレー(fitzの色は0-1のfloatで指定する)
_LIGHT_GRAY = (230 / 255, 230 / 255, 230 / 255)


def _build_pair(path_a: Path, path_b: Path) -> None:
    """テキストは完全に同一だが、Bのページ2にだけ薄いグレーの矩形を追加した2ファイルを作る。"""
    doc_a = fitz.open()
    doc_a.new_page().insert_text((72, 72), "Page one identical text and identical visual.")
    doc_a.new_page().insert_text((72, 72), "Page two identical text but the box differs subtly.")
    doc_a.save(str(path_a))
    doc_a.close()

    doc_b = fitz.open()
    doc_b.new_page().insert_text((72, 72), "Page one identical text and identical visual.")
    p2 = doc_b.new_page()
    p2.insert_text((72, 72), "Page two identical text but the box differs subtly.")
    p2.draw_rect(fitz.Rect(72, 120, 300, 220), color=_LIGHT_GRAY, fill=_LIGHT_GRAY, width=0)
    doc_b.save(str(path_b))
    doc_b.close()


def test_threshold_changes_visual_only_detection_via_aligner():
    """detect_visual_only_changes: threshold=30(既定)では見逃し、threshold=10では検出する。"""
    path_a = _PROJECT_ROOT / "threshold_prop_a.pdf"
    path_b = _PROJECT_ROOT / "threshold_prop_b.pdf"
    try:
        _build_pair(path_a, path_b)
        pages_a = load_pdf_pages(str(path_a))
        pages_b = load_pdf_pages(str(path_b))

        alignment_default = align_documents(pages_a, pages_b)
        assert all(s.status == "unchanged" for s in alignment_default.page_statuses)
        detect_visual_only_changes(alignment_default, str(path_a), str(path_b), threshold=30)
        assert all(s.status == "unchanged" for s in alignment_default.page_statuses), (
            "threshold=30(既定)では薄いグレーの矩形(差分量25)は検出されないはず"
        )

        alignment_sensitive = align_documents(pages_a, pages_b)
        detect_visual_only_changes(alignment_sensitive, str(path_a), str(path_b), threshold=10)
        page2 = next(s for s in alignment_sensitive.page_statuses if s.a_page == 1)
        assert page2.status == "changed" and page2.visual_only is True, (
            "threshold=10ではより敏感になり、薄いグレーの矩形の差分を検出するはず"
        )

        print("OK: test_threshold_changes_visual_only_detection_via_aligner")
    finally:
        path_a.unlink(missing_ok=True)
        path_b.unlink(missing_ok=True)


def test_report_and_session_functions_pass_threshold_through():
    """build_excel_report/build_pdf_report/save_sessionが、内部のdiff_page_pair呼び出しに
    受け取ったthresholdをそのまま渡していることを確認する(モックでスパイする)。
    """
    path_a = _PROJECT_ROOT / "threshold_prop_report_a.pdf"
    path_b = _PROJECT_ROOT / "threshold_prop_report_b.pdf"
    excel_path = _PROJECT_ROOT / "threshold_prop_report.xlsx"
    pdf_path = _PROJECT_ROOT / "threshold_prop_report.pdf"
    session_path = _PROJECT_ROOT / "threshold_prop_report.ymbdiff"
    try:
        # 通常のテキスト差分ページを1つ作る(statusが"changed"になり、diff_page_pairが呼ばれる)
        doc_a = fitz.open()
        doc_a.new_page().insert_text((72, 72), "Report entry point text A.")
        doc_a.save(str(path_a))
        doc_a.close()
        doc_b = fitz.open()
        doc_b.new_page().insert_text((72, 72), "Report entry point text B CHANGED.")
        doc_b.save(str(path_b))
        doc_b.close()

        pages_a = load_pdf_pages(str(path_a))
        pages_b = load_pdf_pages(str(path_b))
        alignment = align_documents(pages_a, pages_b)
        assert alignment.page_statuses[0].status == "changed"

        recorded_thresholds = []

        def _spy(*args, **kwargs):
            recorded_thresholds.append(kwargs.get("threshold"))
            return real_diff_page_pair(*args, **kwargs)

        with patch("ymb_pdf_diff.report.excel_report.diff_page_pair", side_effect=_spy):
            build_excel_report(str(path_a), str(path_b), pages_a, pages_b, alignment, str(excel_path), threshold=77)
        assert 77 in recorded_thresholds, "build_excel_reportがthresholdをdiff_page_pairへ渡していない"

        recorded_thresholds.clear()
        with patch("ymb_pdf_diff.report.pdf_report.diff_page_pair", side_effect=_spy):
            build_pdf_report(str(path_a), str(path_b), pages_a, pages_b, alignment, str(pdf_path), threshold=63)
        assert 63 in recorded_thresholds, "build_pdf_reportがthresholdをdiff_page_pairへ渡していない"

        recorded_thresholds.clear()
        with patch("ymb_pdf_diff.session.diff_page_pair", side_effect=_spy):
            save_session(str(session_path), str(path_a), str(path_b), pages_a, pages_b, alignment, threshold=8)
        assert 8 in recorded_thresholds, "save_sessionがthresholdをdiff_page_pairへ渡していない"

        print("OK: test_report_and_session_functions_pass_threshold_through")
    finally:
        for p in (path_a, path_b, excel_path, pdf_path, session_path):
            p.unlink(missing_ok=True)


def test_cli_threshold_option_affects_single_mode_detection():
    """CLIの--thresholdオプションが検出結果に反映されることをsubprocess経由で確認する。"""
    tmp_dir = _PROJECT_ROOT / "_tmp_cli_threshold_test"
    try:
        tmp_dir.mkdir(parents=True)
        path_a = tmp_dir / "cli_threshold_a.pdf"
        path_b = tmp_dir / "cli_threshold_b.pdf"
        _build_pair(path_a, path_b)

        result_default = subprocess.run(
            [sys.executable, "-m", "ymb_pdf_diff.cli", str(path_a), str(path_b), "--threshold", "30"],
            cwd=str(_PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        assert result_default.returncode == 0, f"stderr: {result_default.stderr}"
        assert "visual-only" not in result_default.stdout, (
            "--threshold 30(既定)では薄いグレーの矩形は検出されないはず"
        )

        result_sensitive = subprocess.run(
            [sys.executable, "-m", "ymb_pdf_diff.cli", str(path_a), str(path_b), "--threshold", "10"],
            cwd=str(_PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        assert result_sensitive.returncode == 0, f"stderr: {result_sensitive.stderr}"
        assert "visual-only" in result_sensitive.stdout, (
            "--threshold 10ではより敏感になり、薄いグレーの矩形の差分を検出するはず"
        )

        print("OK: test_cli_threshold_option_affects_single_mode_detection")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    test_threshold_changes_visual_only_detection_via_aligner()
    test_report_and_session_functions_pass_threshold_through()
    test_cli_threshold_option_affects_single_mode_detection()
