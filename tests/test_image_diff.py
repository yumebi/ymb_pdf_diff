import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from PIL import Image, ImageDraw

from ymb_pdf_diff.core.image_diff import diff_images, overlay_images


def test_identical_images_have_no_diff():
    img = Image.new("RGB", (200, 300), "white")
    result = diff_images(img, img.copy())
    assert result.has_diff is False
    assert result.regions == []
    assert result.diff_ratio == 0.0
    print("OK: test_identical_images_have_no_diff")


def test_localized_change_is_detected_as_single_region():
    img_a = Image.new("RGB", (200, 300), "white")
    img_b = img_a.copy()
    ImageDraw.Draw(img_b).rectangle([50, 100, 120, 140], fill="black")

    result = diff_images(img_a, img_b)
    assert result.has_diff is True
    assert len(result.regions) == 1
    x0, y0, x1, y1 = result.regions[0]
    assert 48 <= x0 <= 50 and 98 <= y0 <= 100
    assert 120 <= x1 <= 122 and 140 <= y1 <= 142
    print("OK: test_localized_change_is_detected_as_single_region")


def test_two_separated_changes_are_detected_as_two_regions():
    img_a = Image.new("RGB", (200, 300), "white")
    img_b = img_a.copy()
    draw = ImageDraw.Draw(img_b)
    draw.rectangle([10, 10, 30, 20], fill="black")
    draw.rectangle([10, 250, 30, 260], fill="black")

    result = diff_images(img_a, img_b)
    assert len(result.regions) == 2
    print("OK: test_two_separated_changes_are_detected_as_two_regions")


def test_overlay_white_plus_white_stays_white():
    img_a = Image.new("RGB", (50, 50), "white")
    img_b = Image.new("RGB", (50, 50), "white")
    composite = overlay_images(img_a, img_b)
    pixels = np.array(composite)
    assert (pixels == 255).all()
    print("OK: test_overlay_white_plus_white_stays_white")


def test_overlay_ink_only_in_a_gives_red():
    img_a = Image.new("RGB", (50, 50), "white")
    ImageDraw.Draw(img_a).rectangle([10, 10, 20, 20], fill="black")
    img_b = Image.new("RGB", (50, 50), "white")
    composite = overlay_images(img_a, img_b)
    pixel = composite.getpixel((15, 15))
    # Aのみにインクがある箇所は赤(R=255,G=0,B=0)になる
    assert pixel == (255, 0, 0)
    print("OK: test_overlay_ink_only_in_a_gives_red")


def test_overlay_ink_only_in_b_gives_blue():
    img_a = Image.new("RGB", (50, 50), "white")
    img_b = Image.new("RGB", (50, 50), "white")
    ImageDraw.Draw(img_b).rectangle([10, 10, 20, 20], fill="black")
    composite = overlay_images(img_a, img_b)
    pixel = composite.getpixel((15, 15))
    # Bのみにインクがある箇所は青(R=0,G=0,B=255)になる
    assert pixel == (0, 0, 255)
    print("OK: test_overlay_ink_only_in_b_gives_blue")


def test_overlay_ink_in_both_gives_dark():
    img_a = Image.new("RGB", (50, 50), "white")
    img_b = Image.new("RGB", (50, 50), "white")
    ImageDraw.Draw(img_a).rectangle([10, 10, 20, 20], fill="black")
    ImageDraw.Draw(img_b).rectangle([10, 10, 20, 20], fill="black")
    composite = overlay_images(img_a, img_b)
    pixel = composite.getpixel((15, 15))
    assert pixel == (0, 0, 0)
    print("OK: test_overlay_ink_in_both_gives_dark")


if __name__ == "__main__":
    test_identical_images_have_no_diff()
    test_localized_change_is_detected_as_single_region()
    test_two_separated_changes_are_detected_as_two_regions()
    test_overlay_white_plus_white_stays_white()
    test_overlay_ink_only_in_a_gives_red()
    test_overlay_ink_only_in_b_gives_blue()
    test_overlay_ink_in_both_gives_dark()
