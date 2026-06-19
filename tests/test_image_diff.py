import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageDraw

from ymb_pdf_diff.core.image_diff import diff_images


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


if __name__ == "__main__":
    test_identical_images_have_no_diff()
    test_localized_change_is_detected_as_single_region()
    test_two_separated_changes_are_detected_as_two_regions()
