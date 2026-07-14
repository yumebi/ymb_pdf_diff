"""位置ズレ許容(#新機能12: shift_tolerance)の効果を確認するテスト。

レンダリングツール・余白の違いなどで生じる「内容は同一だが数ピクセルだけ位置がズレている」
画像ペアに対し、shift_tolerance=0(従来通り)では差分として検出されてしまうが、
shift_tolerance>0(ガウスぼかしを掛けて比較)にすると差分が大幅に減る(誤検出が減る)ことを確認する。
また、位置ズレとは無関係な本物の内容変化(新規の黒塗り矩形)は、shift_tolerance>0でも
引き続き検出されること(見逃されないこと)も確認する。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageDraw

from ymb_pdf_diff.core.image_diff import diff_images

_SHIFT_DX = 2
_SHIFT_DY = 2


def _make_base_image() -> Image.Image:
    """細かい格子模様(文字や罫線の集合を模したもの)を描いた画像を作る。

    格子模様は数ピクセルのズレでも輪郭がずれて大きな画素差になりやすく、
    「わずかな位置ズレによる誤検出」を再現しやすい題材になる。
    """
    img = Image.new("RGB", (400, 300), "white")
    draw = ImageDraw.Draw(img)
    for x in range(20, 380, 20):
        draw.line([(x, 20), (x, 280)], fill="black", width=2)
    for y in range(20, 280, 20):
        draw.line([(20, y), (380, y)], fill="black", width=2)
    return img


def _shift_image(img: Image.Image, dx: int, dy: int) -> Image.Image:
    """imgを(dx, dy)だけずらして白背景のキャンバスに貼り付けたコピーを返す(内容は同一)。"""
    canvas = Image.new("RGB", img.size, "white")
    canvas.paste(img, (dx, dy))
    return canvas


def test_shift_only_difference_is_suppressed_by_tolerance():
    """内容が同一で数ピクセルだけズレたペアは、shift_tolerance=0では検出され、
    shift_tolerance=5では検出されなくなる(または差分比率が大幅に小さくなる)ことを確認する。
    """
    img_a = _make_base_image()
    img_b = _shift_image(img_a, _SHIFT_DX, _SHIFT_DY)

    result_no_tolerance = diff_images(img_a, img_b, shift_tolerance=0)
    assert result_no_tolerance.has_diff is True
    assert result_no_tolerance.diff_ratio > 0.01, "位置ズレのみでも、許容なしでは有意な差分比率になるはず"

    result_with_tolerance = diff_images(img_a, img_b, shift_tolerance=5)
    assert result_with_tolerance.has_diff is False or (
        result_with_tolerance.diff_ratio < result_no_tolerance.diff_ratio / 10
    ), "位置ズレ許容ありでは、差分なし、または比率が桁違いに小さくなるはず"

    print("OK: test_shift_only_difference_is_suppressed_by_tolerance")


def test_genuine_content_change_is_still_detected_with_tolerance():
    """位置ズレとは無関係な本物の内容変化(新規の黒塗り矩形)は、shift_tolerance=5でも
    見逃されず検出されることを確認する(誤って差分を消し過ぎていないかのチェック)。
    """
    img_a = _make_base_image()
    img_b = _shift_image(img_a, _SHIFT_DX, _SHIFT_DY)
    # 位置ズレとは無関係な、明確に大きい内容変化を追加する
    ImageDraw.Draw(img_b).rectangle([150, 100, 250, 180], fill="black")

    result = diff_images(img_a, img_b, shift_tolerance=5)
    assert result.has_diff is True, "本物の内容変化はshift_tolerance>0でも検出されるはず"
    assert len(result.regions) >= 1

    print("OK: test_genuine_content_change_is_still_detected_with_tolerance")


def test_shift_tolerance_zero_is_identical_to_default_behavior():
    """shift_tolerance未指定(既定値0)が、明示的に0を渡した場合と同じ結果になることを確認する
    (デフォルト挙動が本機能追加によって変わっていないことの回帰チェック)。
    """
    img_a = _make_base_image()
    img_b = _shift_image(img_a, _SHIFT_DX, _SHIFT_DY)

    result_default = diff_images(img_a, img_b)
    result_explicit_zero = diff_images(img_a, img_b, shift_tolerance=0)

    assert result_default.has_diff == result_explicit_zero.has_diff
    assert result_default.diff_ratio == result_explicit_zero.diff_ratio
    assert result_default.regions == result_explicit_zero.regions

    print("OK: test_shift_tolerance_zero_is_identical_to_default_behavior")


if __name__ == "__main__":
    test_shift_only_difference_is_suppressed_by_tolerance()
    test_genuine_content_change_is_still_detected_with_tolerance()
    test_shift_tolerance_zero_is_identical_to_default_behavior()
