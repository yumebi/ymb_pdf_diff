"""大きめのPDF(既定120ページ)でパイプライン全体の処理時間を計測するベンチマークスクリプト。

読み込み・整列・見た目差分検出・行差分・レポート出力(Excel/PDF/セッション)の各フェーズを
個別に time.perf_counter で計測し、どこが処理時間のボトルネックになっているかを
日本語の表で表示する。既存のアプリのソースコードは一切変更せず、このスクリプト単体で
合成PDFを生成→計測→(既定で)後片付け、まで完結する。

使い方:
    python scripts/benchmark.py                  # 既定: 120ページ、レポート出力も含めて計測
    python scripts/benchmark.py --pages 30       # 30ページで計測(スケーリング確認用)
    python scripts/benchmark.py --skip-reports   # Excel/PDF/セッション保存のフェーズを省略
    python scripts/benchmark.py --keep           # 生成したPDF/レポートを削除せず残す(確認用)
    python scripts/benchmark.py --changed-ratio 0.2  # Bで文章を変更するページの割合を変える
"""
import argparse
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Tuple

import fitz  # PyMuPDF

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ymb_pdf_diff.core import align_documents, detect_visual_only_changes, diff_page_lines, load_pdf_pages
from ymb_pdf_diff.report import build_excel_report, build_pdf_report
from ymb_pdf_diff.session import save_session

PAGE_SIZE = (595, 842)  # A4
FONT = "japan"
MARGIN = 72
LINES_PER_PAGE = 8


def _body_lines(page_no: int, changed: bool) -> List[str]:
    """ページごとに一意な本文行を8行生成する(ページ番号を織り込み、整列が意味を持つようにする)。

    changed=Trueの場合は末尾2行を書き換え、テキスト差分(diff_page_lines)が発生するようにする。
    """
    lines = [
        f"これは{page_no}ページ目の本文です。第{line_no}行目の内容であり、他のページとは異なる文章になっています。"
        for line_no in range(1, LINES_PER_PAGE + 1)
    ]
    if changed:
        lines[-2] = f"これは{page_no}ページ目の本文ですが、第{LINES_PER_PAGE - 1}行目の内容が変更されました。"
        lines[-1] = f"これは{page_no}ページ目の本文ですが、第{LINES_PER_PAGE}行目の内容も変更されました。"
    return lines


def _add_text_page(doc: "fitz.Document", heading: str, lines: List[str]) -> None:
    page = doc.new_page(width=PAGE_SIZE[0], height=PAGE_SIZE[1])
    page.insert_text((MARGIN, 90), heading, fontname=FONT, fontsize=18)
    rect = fitz.Rect(MARGIN, 120, PAGE_SIZE[0] - MARGIN, PAGE_SIZE[1] - MARGIN)
    page.insert_textbox(rect, "\n".join(lines), fontname=FONT, fontsize=11, lineheight=1.6)


def build_documents(pages: int, changed_ratio: float, out_dir: Path) -> Tuple[Path, Path, int]:
    """検証用の合成PDF A/Bを生成する。

    Bには
    - changed_ratioに応じた件数のページに文章変更(テキスト差分の発生源)
    - 中間位置に1ページ追加(ページ移動整列=align_documentsの頑健性を試す)
    を仕込む。戻り値は (path_a, path_b, 実際に変更したページ数)。
    """
    changed_count = max(1, round(pages * changed_ratio))
    step = max(1, pages // changed_count)
    changed_indices = sorted(set(range(0, pages, step)))[:changed_count]
    changed_set = set(changed_indices)

    insert_after = pages // 2  # 0-based。このページの直後に新規ページを1枚挿入する

    path_a = out_dir / "bench_A.pdf"
    path_b = out_dir / "bench_B.pdf"

    doc_a = fitz.open()
    for i in range(pages):
        _add_text_page(doc_a, f"第{i + 1}ページ - 見出しテキスト", _body_lines(i + 1, changed=False))
    doc_a.save(str(path_a))
    doc_a.close()

    doc_b = fitz.open()
    for i in range(pages):
        _add_text_page(doc_b, f"第{i + 1}ページ - 見出しテキスト", _body_lines(i + 1, changed=i in changed_set))
        if i == insert_after:
            extra_lines = [
                f"このページは差し込みで追加された新規ページです。第{line_no}行目。"
                for line_no in range(1, LINES_PER_PAGE + 1)
            ]
            _add_text_page(doc_b, f"第{i + 1}.5ページ - 追加ページ(Bのみ)", extra_lines)
    doc_b.save(str(path_b))
    doc_b.close()

    return path_a, path_b, len(changed_indices)


def _fmt(seconds: float) -> str:
    return f"{seconds:.3f}"


def main() -> None:
    parser = argparse.ArgumentParser(description="PDF差分パイプラインの処理時間ベンチマーク")
    parser.add_argument("--pages", type=int, default=120, help="生成するPDFのページ数(既定: 120)")
    parser.add_argument(
        "--changed-ratio", type=float, default=0.1, help="Bで文章を変更するページの割合(既定: 0.1 = 約10%%)"
    )
    parser.add_argument("--keep", action="store_true", help="生成したPDF/レポートを削除せず残す")
    parser.add_argument(
        "--skip-reports", action="store_true", help="Excel/PDF/セッション保存フェーズを省略する(高速化)"
    )
    args = parser.parse_args()

    tmp_dir = Path(tempfile.mkdtemp(prefix="ymb_pdf_diff_bench_"))
    print(f"作業ディレクトリ: {tmp_dir}")

    results: List[Tuple[str, float, int]] = []  # (フェーズ名, 秒, ページあたりms算出用の件数(0なら非表示))

    try:
        t0 = time.perf_counter()
        path_a, path_b, changed_count = build_documents(args.pages, args.changed_ratio, tmp_dir)
        gen_time = time.perf_counter() - t0
        print(
            f"サンプルPDF生成完了: {args.pages}ページ x2 "
            f"(B側は文章変更 {changed_count}ページ + 追加1ページ、{gen_time:.3f}秒)"
        )

        t0 = time.perf_counter()
        pages_a = load_pdf_pages(str(path_a))
        t_load_a = time.perf_counter() - t0
        results.append(("読み込み(A) load_pdf_pages", t_load_a, args.pages))

        t0 = time.perf_counter()
        pages_b = load_pdf_pages(str(path_b))
        t_load_b = time.perf_counter() - t0
        results.append(("読み込み(B) load_pdf_pages", t_load_b, len(pages_b)))

        t0 = time.perf_counter()
        alignment = align_documents(pages_a, pages_b)
        t_align = time.perf_counter() - t0
        results.append(("整列 align_documents", t_align, args.pages))

        t0 = time.perf_counter()
        detect_visual_only_changes(alignment, str(path_a), str(path_b))
        t_visual = time.perf_counter() - t0
        # 見た目差分検出は"unchanged"だったページ対のみ再レンダリングするため、その件数を分母にする
        unchanged_before_visual = sum(
            1
            for s in alignment.page_statuses
            if s.a_page is not None and s.b_page is not None and not s.visual_only
        )
        results.append(("見た目差分検出 detect_visual_only_changes", t_visual, args.pages))

        changed_pairs = [
            s for s in alignment.changed_pages() if s.a_page is not None and s.b_page is not None
        ]
        t0 = time.perf_counter()
        for status in changed_pairs:
            diff_page_lines(pages_a[status.a_page], pages_b[status.b_page])
        t_diff_lines = time.perf_counter() - t0
        results.append((f"行差分 diff_page_lines (差分{len(changed_pairs)}ページ分)", t_diff_lines, len(changed_pairs) or 1))

        if not args.skip_reports:
            excel_path = tmp_dir / "report.xlsx"
            t0 = time.perf_counter()
            build_excel_report(str(path_a), str(path_b), pages_a, pages_b, alignment, str(excel_path))
            t_excel = time.perf_counter() - t0
            results.append(("Excelレポート build_excel_report", t_excel, args.pages))

            pdf_report_path = tmp_dir / "report.pdf"
            t0 = time.perf_counter()
            build_pdf_report(str(path_a), str(path_b), pages_a, pages_b, alignment, str(pdf_report_path))
            t_pdf_report = time.perf_counter() - t0
            results.append(("PDFレポート build_pdf_report", t_pdf_report, args.pages))

            session_path = tmp_dir / "session.ymbdiff"
            t0 = time.perf_counter()
            save_session(str(session_path), str(path_a), str(path_b), pages_a, pages_b, alignment)
            t_session = time.perf_counter() - t0
            results.append(("セッション保存 save_session", t_session, args.pages))

        total = sum(t for _, t, _ in results)

        print()
        print(f"=== 計測結果({args.pages}ページ、changed-ratio={args.changed_ratio}) ===")
        header = f"{'フェーズ':45s} {'秒':>10s} {'ページあたり(ms)':>18s}"
        print(header)
        print("-" * len(header))
        for name, seconds, count in results:
            per_page = f"{(seconds / count) * 1000:.2f}" if count else "-"
            print(f"{name:45s} {_fmt(seconds):>10s} {per_page:>18s}")
        print("-" * len(header))
        print(f"{'合計':45s} {_fmt(total):>10s}")
        print(f"(参考)未変更ページ対の残数(見た目差分検出後): {unchanged_before_visual}")

        # 単純な線形外挿によるスケーリング目安(見た目差分検出がページ数に比例して支配的になる前提)。
        # 実測値ではないため、あくまで「このくらいのオーダーになりそう」という参考値。
        if args.pages > 0:
            per_page_total = total / args.pages
            for projected_pages in (250, 500):
                print(
                    f"projection目安: {projected_pages}ページなら約 {per_page_total * projected_pages:.1f}秒 "
                    f"(現在の{args.pages}ページの結果を単純に比例外挿しただけの参考値)"
                )

    finally:
        if args.keep:
            print(f"--keep指定のため生成物を保持: {tmp_dir}")
        else:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            print(f"作業ディレクトリを削除しました: {tmp_dir}")


if __name__ == "__main__":
    main()
