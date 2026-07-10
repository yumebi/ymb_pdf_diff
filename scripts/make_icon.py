"""YMB PDF DIFF用アプリアイコンを生成する。

デザイン: 右上の角を折った「PDFファイル」定番シルエットに、白抜き太字の
"PDF" ロゴを載せたもの。背後にもう1枚シートをずらして配置し、2つの文書を
比較する「diff」ツールであることを示す。

使い方:
    python scripts/make_icon.py
出力:
    assets/icon.png (1024x1024, Mac側の.icns変換の元データ)
    assets/icon.ico (Windows用, 複数解像度同梱)
    assets/icon.icns (macOS用, 複数解像度同梱)
"""
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
SIZE = 1024

# PDFの定番色(Adobe系アプリでおなじみの赤)。
RED_FILL = (217, 48, 37, 255)  # #D93025
RED_FLAP = (163, 33, 24, 255)  # 折り目の陰(少し暗い赤)
RED_BORDER = (255, 255, 255, 255)  # 白縁取り。明暗どちらのタスクバーでも視認できるように。

BACK_SHEET_FILL = (246, 247, 249, 255)  # ほぼ白(背後にずらす2枚目のシート)
BACK_SHEET_FLAP = (222, 226, 233, 255)
BACK_SHEET_BORDER = (196, 202, 212, 255)

SHADOW_COLOR = (0, 0, 0, 110)

# 太字TrueTypeフォントの候補(見つかった順に使う)。
FONTS_DIR = Path(r"C:\Windows\Fonts")
BOLD_FONT_CANDIDATES = [
    "arialbd.ttf",
    "Arialbd.ttf",
    "ARIALBD.TTF",
    "segoeuib.ttf",
    "seguisb.ttf",
    "tahomabd.ttf",
    "verdanab.ttf",
]


def _load_bold_font(size: int) -> ImageFont.FreeTypeFont:
    """C:\\Windows\\Fonts から太字フォントを探して読み込む。見つからなければ明示的にエラーにする。"""
    tried = []
    for name in BOLD_FONT_CANDIDATES:
        path = FONTS_DIR / name
        tried.append(str(path))
        if path.exists():
            return ImageFont.truetype(str(path), size)
    raise RuntimeError(
        "太字のTrueTypeフォントが見つからない。以下を試したが全て存在しない: " + ", ".join(tried)
    )


def _fit_bold_font(text: str, target_width: float, initial_size: int) -> ImageFont.FreeTypeFont:
    """指定した幅に収まるようフォントサイズを1回計測して合わせる。"""
    probe = Image.new("RGBA", (10, 10))
    probe_draw = ImageDraw.Draw(probe)

    font = _load_bold_font(initial_size)
    measured_width = probe_draw.textlength(text, font=font)
    if measured_width <= 0:
        return font

    scale = target_width / measured_width
    fitted_size = max(1, int(initial_size * scale))
    return _load_bold_font(fitted_size)


def _dogear_polygon(x0: int, y0: int, x1: int, y1: int, fold: int) -> list:
    """右上の角を折った「PDFファイル」定番シルエット(五角形)の頂点列。"""
    return [
        (x0, y0),
        (x1 - fold, y0),
        (x1, y0 + fold),
        (x1, y1),
        (x0, y1),
    ]


def _draw_sheet(
    canvas: Image.Image,
    box: tuple,
    fold: int,
    fill: tuple,
    border: tuple,
    flap_fill: tuple,
    border_width: int,
) -> None:
    """右上を折ったシート(ページ)を1枚描く。"""
    x0, y0, x1, y1 = box
    draw = ImageDraw.Draw(canvas)
    poly = _dogear_polygon(x0, y0, x1, y1, fold)
    draw.polygon(poly, fill=fill, outline=border, width=border_width)

    # 折り目の三角形(dog-ear)を少し暗い色で重ね描きし、紙が折れている質感を出す。
    flap = [(x1 - fold, y0), (x1, y0 + fold), (x1 - fold, y0 + fold)]
    draw.polygon(flap, fill=flap_fill, outline=border, width=max(2, border_width // 2))


def build_icon() -> Image.Image:
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))

    # --- 背後の2枚目のシート(diff = 2文書比較を示す控えめな要素) ---
    back_box = (150, 180, 620, 830)
    _draw_sheet(
        canvas,
        back_box,
        fold=70,
        fill=BACK_SHEET_FILL,
        border=BACK_SHEET_BORDER,
        flap_fill=BACK_SHEET_FLAP,
        border_width=10,
    )

    # --- 前面シートの影 ---
    front_box = (330, 140, 900, 900)
    shadow_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    fx0, fy0, fx1, fy1 = front_box
    shadow_poly = _dogear_polygon(fx0 + 16, fy0 + 20, fx1 + 16, fy1 + 20, 130)
    shadow_draw.polygon(shadow_poly, fill=SHADOW_COLOR)
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(20))
    canvas.alpha_composite(shadow_layer)

    # --- 前面のメインシート(PDFの定番赤 + 白縁取りで視認性を確保) ---
    _draw_sheet(
        canvas,
        front_box,
        fold=130,
        fill=RED_FILL,
        border=RED_BORDER,
        flap_fill=RED_FLAP,
        border_width=26,
    )

    # --- "PDF" 白抜き太字ロゴ。シート幅に合わせて自動でフォントサイズを決める ---
    sheet_width = fx1 - fx0
    target_text_width = sheet_width * 0.82  # 文字1つあたりおよそ幅の1/3になるよう余白を残す
    font = _fit_bold_font("PDF", target_text_width, initial_size=int(sheet_width * 0.55))

    cx = (fx0 + fx1) / 2
    cy = fy0 + (fy1 - fy0) * 0.60  # 折り目より下、シートの重心よりやや下に配置
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (cx, cy),
        "PDF",
        font=font,
        fill=(255, 255, 255, 255),
        anchor="mm",
        stroke_width=6,
        stroke_fill=RED_FLAP,
    )

    return canvas


def _write_icns_fallback(img: Image.Image, path: Path) -> None:
    """Pillowが書き込めない環境向けの最小限のICNSライター。

    icnsは単純なコンテナ形式: マジック"icns" + 全体長(4byte) の後に、
    "OSType(4byte) + チャンク長(4byte) + PNGデータ" というチャンクが並ぶ。
    """
    size_to_ostype = {
        16: b"icp4",
        32: b"icp5",
        64: b"ic12",
        128: b"ic07",
        256: b"ic08",
        512: b"ic09",
        1024: b"ic10",
    }

    import io

    chunks = b""
    for size, ostype in size_to_ostype.items():
        resized = img.resize((size, size), Image.LANCZOS)
        png_bytes_io = io.BytesIO()
        resized.save(png_bytes_io, format="PNG")
        png_bytes = png_bytes_io.getvalue()
        chunk_len = 8 + len(png_bytes)
        chunks += ostype + struct.pack(">I", chunk_len) + png_bytes

    total_len = 8 + len(chunks)
    with open(path, "wb") as f:
        f.write(b"icns")
        f.write(struct.pack(">I", total_len))
        f.write(chunks)


def save_icns(img: Image.Image, path: Path) -> None:
    """assets/icon.icns を書き出す。まずPillow標準機能を試し、駄目なら自前実装にフォールバックする。"""
    sizes = [(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512), (1024, 1024)]
    try:
        img.save(path, format="ICNS", sizes=sizes)
        # 実際にICNSとして書き込めたか確認する。
        with Image.open(path) as check:
            if check.format != "ICNS":
                raise ValueError(f"unexpected format: {check.format}")
    except Exception as exc:  # noqa: BLE001 - Pillow非対応環境のフォールバックに切り替えるため広く捕捉
        print(f"[情報] Pillow標準のICNS書き出しに失敗したため自前実装で書き出す({exc})")
        _write_icns_fallback(img, path)


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    icon = build_icon()

    png_path = ASSETS_DIR / "icon.png"
    icon.save(png_path, format="PNG")

    ico_path = ASSETS_DIR / "icon.ico"
    icon.save(
        ico_path,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )

    icns_path = ASSETS_DIR / "icon.icns"
    save_icns(icon, icns_path)

    print(f"saved: {png_path}")
    print(f"saved: {ico_path}")
    print(f"saved: {icns_path}")


if __name__ == "__main__":
    main()
