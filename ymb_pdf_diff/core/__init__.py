from .models import DiffEntry, ImageDiffResult, PageLine, PageStatus
from .pdf_loader import OcrUnavailableError, load_pdf_pages
from .aligner import AlignmentResult, align_documents, detect_visual_only_changes
from .text_diff import char_diff_segments, diff_page_lines
from .image_diff import diff_images, diff_page_pair, draw_highlights, overlay_images, pad_to_same_size, render_page
from .page_range import align_documents_in_range, parse_page_range, slice_pages

__all__ = [
    "DiffEntry",
    "ImageDiffResult",
    "PageLine",
    "PageStatus",
    "OcrUnavailableError",
    "load_pdf_pages",
    "AlignmentResult",
    "align_documents",
    "detect_visual_only_changes",
    "diff_page_lines",
    "char_diff_segments",
    "diff_images",
    "diff_page_pair",
    "draw_highlights",
    "overlay_images",
    "pad_to_same_size",
    "render_page",
    "parse_page_range",
    "slice_pages",
    "align_documents_in_range",
]
