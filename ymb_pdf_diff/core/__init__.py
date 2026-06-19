from .models import DiffEntry, ImageDiffResult, PageLine, PageStatus
from .pdf_loader import OcrUnavailableError, load_pdf_pages
from .aligner import AlignmentResult, align_documents, detect_visual_only_changes
from .text_diff import diff_page_lines
from .image_diff import diff_images, diff_page_pair, draw_highlights, pad_to_same_size, render_page

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
    "diff_images",
    "diff_page_pair",
    "draw_highlights",
    "pad_to_same_size",
    "render_page",
]
