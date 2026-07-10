import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from .core import (
    align_documents,
    align_documents_in_range,
    detect_visual_only_changes,
    diff_page_lines,
    diff_page_pair,
    load_pdf_pages,
    parse_page_range,
)
from .report import DEFAULT_IMAGE_SIZE, IMAGE_SIZE_CHOICES, build_excel_report, build_pdf_report


def _print_page_statuses(pdf_a: str, pdf_b: str, pages_a, pages_b, result, threshold: int = 30) -> None:
    for status in result.page_statuses:
        a_disp = status.a_page + 1 if status.a_page is not None else "-"
        b_disp = status.b_page + 1 if status.b_page is not None else "-"
        moved_tag = " (moved)" if status.moved else ""
        visual_tag = " (visual-only)" if status.visual_only else ""
        print(f"A:{a_disp} <-> B:{b_disp}  [{status.status}]{moved_tag}{visual_tag}")

        if status.status == "changed" and status.a_page is not None and status.b_page is not None:
            entries = diff_page_lines(pages_a[status.a_page], pages_b[status.b_page])
            for entry in entries:
                print(f"    {entry.kind}: -{entry.before} +{entry.after}")

            img_result = diff_page_pair(pdf_a, status.a_page, pdf_b, status.b_page, threshold=threshold)
            print(f"    image_diff: ratio={img_result.diff_ratio:.3%} regions={len(img_result.regions)}")


def _run_single(args: argparse.Namespace) -> None:
    """PDF2ファイルの通常比較モード(--range-a/--range-bでページ範囲を絞り込み可能)。"""
    pages_a = load_pdf_pages(args.pdf_a)
    pages_b = load_pdf_pages(args.pdf_b)

    if args.range_a or args.range_b:
        indices_a = parse_page_range(args.range_a, len(pages_a)) if args.range_a else list(range(len(pages_a)))
        indices_b = parse_page_range(args.range_b, len(pages_b)) if args.range_b else list(range(len(pages_b)))
        result = align_documents_in_range(pages_a, pages_b, indices_a, indices_b)
    else:
        result = align_documents(pages_a, pages_b)

    detect_visual_only_changes(result, args.pdf_a, args.pdf_b, threshold=args.threshold)
    _print_page_statuses(args.pdf_a, args.pdf_b, pages_a, pages_b, result, threshold=args.threshold)

    if args.excel:
        build_excel_report(
            args.pdf_a, args.pdf_b, pages_a, pages_b, result, args.excel,
            threshold=args.threshold, image_size=args.image_size,
        )
        print(f"Excelレポート出力: {args.excel}")

    if args.pdf:
        build_pdf_report(
            args.pdf_a, args.pdf_b, pages_a, pages_b, result, args.pdf,
            threshold=args.threshold, image_size=args.image_size,
        )
        print(f"PDFレポート出力: {args.pdf}")


def _run_batch(
    dir_a: str, dir_b: str, out_dir: str, excel_only: bool = False, threshold: int = 30,
    image_size: str = DEFAULT_IMAGE_SIZE,
) -> None:
    """フォルダ一括比較モード(#新機能9)。

    dir_a/dir_bそれぞれ直下(非再帰)にある同名の*.pdfペアだけを比較する。
    デフォルトではExcelレポートに加えPDFレポートも出力する(--excel-onlyでExcelのみに絞れる)。
    どちらか片方にしか存在しないファイルは比較対象から除外し、最後にスキップ一覧として表示する。
    """
    dir_a_path = Path(dir_a)
    dir_b_path = Path(dir_b)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    files_a: Dict[str, Path] = {p.name: p for p in sorted(dir_a_path.glob("*.pdf"))}
    files_b: Dict[str, Path] = {p.name: p for p in sorted(dir_b_path.glob("*.pdf"))}
    common_names = sorted(set(files_a) & set(files_b))
    only_in_a = sorted(set(files_a) - set(files_b))
    only_in_b = sorted(set(files_b) - set(files_a))

    rows: List[Tuple[str, int, int, int, str, str]] = []
    for name in common_names:
        pdf_a_path = str(files_a[name])
        pdf_b_path = str(files_b[name])

        pages_a = load_pdf_pages(pdf_a_path)
        pages_b = load_pdf_pages(pdf_b_path)
        alignment = align_documents(pages_a, pages_b)
        detect_visual_only_changes(alignment, pdf_a_path, pdf_b_path, threshold=threshold)
        diff_count = len(alignment.changed_pages())

        stem = Path(name).stem
        excel_path = out_path / f"{stem}_diff.xlsx"
        build_excel_report(
            pdf_a_path, pdf_b_path, pages_a, pages_b, alignment, str(excel_path),
            threshold=threshold, image_size=image_size,
        )

        pdf_report_path = ""
        if not excel_only:
            pdf_report_path_obj = out_path / f"{stem}_diff.pdf"
            build_pdf_report(
                pdf_a_path, pdf_b_path, pages_a, pages_b, alignment, str(pdf_report_path_obj),
                threshold=threshold, image_size=image_size,
            )
            pdf_report_path = str(pdf_report_path_obj)

        rows.append((name, len(pages_a), len(pages_b), diff_count, str(excel_path), pdf_report_path))

    print("=== バッチ比較 結果サマリー ===")
    print(f"{'ファイル名':30} {'A頁':>5} {'B頁':>5} {'差分頁':>6}  出力先")
    for name, pa, pb, diff_count, excel_path, pdf_report_path in rows:
        outputs = excel_path if not pdf_report_path else f"{excel_path} / {pdf_report_path}"
        print(f"{name:30} {pa:>5} {pb:>5} {diff_count:>6}  {outputs}")

    if not rows:
        print("(比較対象のペアはありませんでした)")

    if only_in_a:
        print("\nスキップ(Bに対応ファイルなし):")
        for name in only_in_a:
            print(f"  {name}")
    if only_in_b:
        print("\nスキップ(Aに対応ファイルなし):")
        for name in only_in_b:
            print(f"  {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="YMB PDF DIFF - core engine CLI")
    parser.add_argument("pdf_a", nargs="?", help="比較元PDF(通常モード)")
    parser.add_argument("pdf_b", nargs="?", help="比較先PDF(通常モード)")
    parser.add_argument("--excel", help="比較結果をExcelレポートとして出力するパス")
    parser.add_argument("--pdf", help="比較結果をPDFレポートとして出力するパス(通常モードのみ)")
    parser.add_argument(
        "--range-a", dest="range_a", help="ファイルAの比較対象ページ範囲(例: 1-5,8)。省略時は全ページ"
    )
    parser.add_argument(
        "--range-b", dest="range_b", help="ファイルBの比較対象ページ範囲(例: 1-5,8)。省略時は全ページ"
    )
    parser.add_argument(
        "--batch",
        nargs=2,
        metavar=("DIR_A", "DIR_B"),
        help="フォルダ一括比較モード: DIR_A/DIR_B直下にある同名PDFペアをすべて比較する",
    )
    parser.add_argument("--out", help="バッチモードの出力先フォルダ(--batch使用時は必須)")
    parser.add_argument(
        "--excel-only",
        action="store_true",
        help="バッチモードでExcelレポートのみ出力する(PDFレポートを省略する)",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=30,
        help="画像差分の感度(0-100、小さいほど敏感。既定値30。単体/バッチモード共通)",
    )
    parser.add_argument(
        "--image-size",
        dest="image_size",
        choices=IMAGE_SIZE_CHOICES,
        default=DEFAULT_IMAGE_SIZE,
        help="レポートに埋め込む画像のサイズ(#新機能11。small/medium/large、既定値medium。単体/バッチモード共通)",
    )
    args = parser.parse_args()

    if args.batch:
        if not args.out:
            parser.error("--batchモードでは--outの指定が必須です。")
        _run_batch(
            args.batch[0], args.batch[1], args.out, excel_only=args.excel_only,
            threshold=args.threshold, image_size=args.image_size,
        )
        return

    if not args.pdf_a or not args.pdf_b:
        parser.error("pdf_aとpdf_bの両方を指定してください(フォルダ一括比較には--batchを使用してください)。")

    try:
        _run_single(args)
    except ValueError as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
