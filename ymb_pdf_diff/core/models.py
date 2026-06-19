from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class PageLine:
    page: int
    text: str
    bbox: Optional[Tuple[float, float, float, float]] = None


@dataclass
class DiffEntry:
    kind: str  # "insert" | "delete" | "replace"
    before: list
    after: list


@dataclass
class PageStatus:
    a_page: Optional[int]  # 0-based page index in file A, None if page exists only in B
    b_page: Optional[int]  # 0-based page index in file B, None if page exists only in A
    status: str            # "unchanged" | "changed" | "inserted" | "deleted"
    moved: bool = False     # True if a_page/b_page correspond but at different physical positions
    visual_only: bool = False  # True if text is identical but rendered image differs (image-diffで判明)


@dataclass
class ImageDiffResult:
    has_diff: bool
    diff_ratio: float                      # 差分ピクセルの割合(0.0-1.0)
    regions: List[Tuple[int, int, int, int]] = field(default_factory=list)  # (x0,y0,x1,y1) ピクセル座標
    size_a: Tuple[int, int] = (0, 0)
    size_b: Tuple[int, int] = (0, 0)
