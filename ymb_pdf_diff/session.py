import io
import json
import zipfile
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List, Optional

from PIL import Image

from . import __version__
from .core import (
    AlignmentResult,
    DiffEntry,
    PageLine,
    PageStatus,
    diff_page_lines,
    diff_page_pair,
    draw_highlights,
    render_page,
)

SESSION_FORMAT_VERSION = 1


@dataclass
class LoadedSession:
    meta: dict
    captures: Dict[str, bytes]

    def page_statuses(self) -> List[PageStatus]:
        return [
            PageStatus(a_page=e["a_page"], b_page=e["b_page"], status=e["status"], moved=e["moved"])
            for e in self.meta["page_statuses"]
        ]

    def text_diff_for(self, idx: int) -> List[DiffEntry]:
        entry = self.meta["page_statuses"][idx]
        return [DiffEntry(kind=d["kind"], before=d["before"], after=d["after"]) for d in entry["text_diff"]]

    def capture_image(self, idx: int, side: str) -> Optional[Image.Image]:
        name = self.meta["page_statuses"][idx].get(f"capture_{side}")
        if not name:
            return None
        return Image.open(io.BytesIO(self.captures[name]))


def save_session(
    output_path: str,
    pdf_a_path: str,
    pdf_b_path: str,
    pages_a: List[List[PageLine]],
    pages_b: List[List[PageLine]],
    alignment: AlignmentResult,
    dpi: int = 150,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> None:
    """比較結果を自己完結のzip(.ymbdiff)に保存する。差分のあるページのみキャプチャ・テキスト差分を同梱する。"""
    meta = {
        "format_version": SESSION_FORMAT_VERSION,
        "app_version": __version__,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "pdf_a_path": pdf_a_path,
        "pdf_b_path": pdf_b_path,
        "pages_a_count": len(pages_a),
        "pages_b_count": len(pages_b),
        "page_statuses": [],
    }

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for idx, status in enumerate(alignment.page_statuses):
            entry = {
                "a_page": status.a_page,
                "b_page": status.b_page,
                "status": status.status,
                "moved": status.moved,
                "text_diff": [],
                "capture_a": None,
                "capture_b": None,
            }

            if status.status != "unchanged":
                regions: list = []
                if status.status == "changed" and status.a_page is not None and status.b_page is not None:
                    entry["text_diff"] = [
                        {"kind": e.kind, "before": e.before, "after": e.after}
                        for e in diff_page_lines(pages_a[status.a_page], pages_b[status.b_page])
                    ]
                    regions = diff_page_pair(pdf_a_path, status.a_page, pdf_b_path, status.b_page, dpi=dpi).regions

                if status.a_page is not None:
                    img_a = render_page(pdf_a_path, status.a_page, dpi=dpi)
                    if regions:
                        img_a = draw_highlights(img_a, regions, color="red")
                    name = f"captures/{idx:03d}_a.png"
                    buf = io.BytesIO()
                    img_a.save(buf, format="PNG")
                    zf.writestr(name, buf.getvalue())
                    entry["capture_a"] = name

                if status.b_page is not None:
                    img_b = render_page(pdf_b_path, status.b_page, dpi=dpi)
                    if regions:
                        img_b = draw_highlights(img_b, regions, color="red")
                    name = f"captures/{idx:03d}_b.png"
                    buf = io.BytesIO()
                    img_b.save(buf, format="PNG")
                    zf.writestr(name, buf.getvalue())
                    entry["capture_b"] = name

            meta["page_statuses"].append(entry)
            if progress_callback:
                progress_callback(idx + 1, len(alignment.page_statuses))

        zf.writestr("result.json", json.dumps(meta, ensure_ascii=False, indent=2))


def load_session(path: str) -> LoadedSession:
    with zipfile.ZipFile(path, "r") as zf:
        meta = json.loads(zf.read("result.json").decode("utf-8"))
        captures = {}
        for entry in meta["page_statuses"]:
            for key in ("capture_a", "capture_b"):
                name = entry.get(key)
                if name:
                    captures[name] = zf.read(name)
    return LoadedSession(meta=meta, captures=captures)
