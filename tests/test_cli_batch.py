"""CLIのフォルダ一括比較モード(#新機能9)を確認するテスト。

python -m ymb_pdf_diff.cli --batch DIR_A DIR_B --out OUT_DIR [--excel-only] をsubprocessで実行し、
・DIR_A/DIR_Bに共通するPDFペアだけがExcelレポートとして出力されること
・片方にしか存在しないファイルが「スキップ」として標準出力に報告されること
・既存の2ファイル位置引数モード(python -m ymb_pdf_diff.cli a.pdf b.pdf --excel out.xlsx)が
  引き続き動作すること(後方互換)
を確認する。
"""
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fitz

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _make_pdf(path: Path, text: str) -> None:
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


def test_batch_mode_compares_matching_pairs_and_reports_skipped_files():
    tmp_dir = _PROJECT_ROOT / "_tmp_cli_batch_test"
    dir_a = tmp_dir / "dir_a"
    dir_b = tmp_dir / "dir_b"
    out_dir = tmp_dir / "out"
    try:
        dir_a.mkdir(parents=True)
        dir_b.mkdir(parents=True)

        # 共通ペア2組
        _make_pdf(dir_a / "report1.pdf", "Report one version A")
        _make_pdf(dir_b / "report1.pdf", "Report one version B CHANGED")
        _make_pdf(dir_a / "report2.pdf", "Report two identical content")
        _make_pdf(dir_b / "report2.pdf", "Report two identical content")

        # 片方にしか存在しないファイル
        _make_pdf(dir_a / "only_in_a.pdf", "Only in A")
        _make_pdf(dir_b / "only_in_b.pdf", "Only in B")

        result = subprocess.run(
            [
                sys.executable, "-m", "ymb_pdf_diff.cli",
                "--batch", str(dir_a), str(dir_b),
                "--out", str(out_dir),
                "--excel-only",
            ],
            cwd=str(_PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"

        assert (out_dir / "report1_diff.xlsx").exists()
        assert (out_dir / "report2_diff.xlsx").exists()
        # --excel-only指定時はPDFレポートを出力しない
        assert not (out_dir / "report1_diff.pdf").exists()

        assert "only_in_a.pdf" in result.stdout
        assert "only_in_b.pdf" in result.stdout
        assert "スキップ" in result.stdout

        print("OK: test_batch_mode_compares_matching_pairs_and_reports_skipped_files")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_single_pair_positional_mode_still_works():
    tmp_dir = _PROJECT_ROOT / "_tmp_cli_single_test"
    try:
        tmp_dir.mkdir(parents=True)
        path_a = tmp_dir / "single_a.pdf"
        path_b = tmp_dir / "single_b.pdf"
        excel_path = tmp_dir / "single_out.xlsx"
        _make_pdf(path_a, "Single mode A text")
        _make_pdf(path_b, "Single mode B text CHANGED")

        result = subprocess.run(
            [sys.executable, "-m", "ymb_pdf_diff.cli", str(path_a), str(path_b), "--excel", str(excel_path)],
            cwd=str(_PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert excel_path.exists()
        print("OK: test_single_pair_positional_mode_still_works")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    test_batch_mode_compares_matching_pairs_and_reports_skipped_files()
    test_single_pair_positional_mode_still_works()
