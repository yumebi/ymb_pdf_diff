import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

from ymb_pdf_diff.gui.diff_colors import DEFAULT_COLORS, DiffColors


def test_set_get_and_reset_round_trip():
    app = QApplication.instance() or QApplication(sys.argv)
    colors = DiffColors()
    original = colors.get("changed_bg")

    colors.set("changed_bg", "#123456")
    assert colors.get("changed_bg") == "#123456"

    # 別インスタンスでもQSettings経由で永続化されている
    colors2 = DiffColors()
    assert colors2.get("changed_bg") == "#123456"

    colors2.reset_defaults()
    assert colors2.get("changed_bg") == DEFAULT_COLORS["changed_bg"]

    colors.set("changed_bg", original)
    print("OK: test_set_get_and_reset_round_trip")


if __name__ == "__main__":
    test_set_get_and_reset_round_trip()
