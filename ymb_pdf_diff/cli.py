import argparse
import sys

from .core import align_documents, detect_visual_only_changes, diff_page_lines, diff_page_pair, load_pdf_pages
from .report import build_excel_report


def main() -> None:
    parser = argparse.ArgumentParser(description="YMB PDF DIFF - core engine CLI")
    parser.add_argument("pdf_a")
    parser.add_argument("pdf_b")
    parser.add_argument("--excel", help="比較結果をExcelレポートとして出力するパス")
    args = parser.parse_args()

    pages_a = load_pdf_pages(args.pdf_a)
    pages_b = load_pdf_pages(args.pdf_b)
    result = align_documents(pages_a, pages_b)
    detect_visual_only_changes(result, args.pdf_a, args.pdf_b)

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

            img_result = diff_page_pair(args.pdf_a, status.a_page, args.pdf_b, status.b_page)
            print(f"    image_diff: ratio={img_result.diff_ratio:.3%} regions={len(img_result.regions)}")

    if args.excel:
        build_excel_report(args.pdf_a, args.pdf_b, pages_a, pages_b, result, args.excel)
        print(f"Excelレポート出力: {args.excel}")


if __name__ == "__main__":
    sys.exit(main())
