"""YMB PDF DIFF用アプリアイコンを生成する。

使い方:
    python scripts/make_icon.py
出力:
    assets/icon.png (1024x1024, Mac側の.icns変換の元データ)
    assets/icon.ico (Windows用, 複数解像度同梱)
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
SIZE = 1024

BG_COLOR = (33, 47, 71, 255)
PAGE_COLOR = (255, 255, 255, 255)
PAGE_BORDER = (180, 188, 201, 255)
LINE_COLOR = (150, 160, 175, 255)
HIGHLIGHT_FILL = (255, 86, 86, 80)
HIGHLIGHT_BORDER = (217, 48, 48, 255)
SHADOW_COLOR = (0, 0, 0, 110)


def _rounded_page(draw_layer: Image.Image, box, radius: int, fill, border, border_width: int = 6) -> None:
    draw = ImageDraw.Draw(draw_layer)
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=border, width=border_width)


def build_icon() -> Image.Image:
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    bg_margin = 40
    draw.rounded_rectangle(
        [bg_margin, bg_margin, SIZE - bg_margin, SIZE - bg_margin], radius=180, fill=BG_COLOR
    )

    back_box = [300, 150, 720, 760]
    front_box = [370, 220, 790, 830]

    # 影(背面ページの少し下にずらしたぼかし矩形)
    shadow_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    shadow_draw.rounded_rectangle(
        [front_box[0] + 14, front_box[1] + 18, front_box[2] + 14, front_box[3] + 18],
        radius=36,
        fill=SHADOW_COLOR,
    )
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(18))
    canvas.alpha_composite(shadow_layer)

    _rounded_page(canvas, back_box, radius=32, fill=PAGE_COLOR, border=PAGE_BORDER)
    _rounded_page(canvas, front_box, radius=32, fill=PAGE_COLOR, border=PAGE_BORDER)

    # 前面ページに本文行(横線)を描く。1本だけ差分ハイライト風に強調する。
    draw = ImageDraw.Draw(canvas)
    line_x0, line_x1 = front_box[0] + 50, front_box[2] - 50
    line_y_start = front_box[1] + 70
    line_gap = 56
    line_height = 14
    highlight_line_index = 2

    for i in range(6):
        y0 = line_y_start + i * line_gap
        y1 = y0 + line_height
        width_ratio = 1.0 if i != 5 else 0.55
        x1 = line_x0 + (line_x1 - line_x0) * width_ratio
        if i == highlight_line_index:
            draw.rounded_rectangle(
                [line_x0 - 14, y0 - 10, x1 + 14, y1 + 10], radius=12, fill=HIGHLIGHT_FILL, outline=HIGHLIGHT_BORDER, width=5
            )
        draw.rounded_rectangle([line_x0, y0, x1, y1], radius=7, fill=LINE_COLOR)

    return canvas


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
    print(f"saved: {png_path}")
    print(f"saved: {ico_path}")


if __name__ == "__main__":
    main()
