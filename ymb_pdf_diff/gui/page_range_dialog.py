from typing import Optional, Tuple

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit


class PageRangeDialog(QDialog):
    """比較対象を特定のページ範囲だけに絞り込むダイアログ(#新機能8)。

    A範囲・B範囲を「1-5,8」のような書式で指定する。空欄のままOKを押すと、
    該当するファイル側は全ページが比較対象になる。実際の書式検証(総ページ数超過等)は
    比較実行時(parse_page_range)に行い、不正な場合はそこでエラー表示する。
    """

    def __init__(self, range_a: Optional[str], range_b: Optional[str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("ページ範囲を指定")

        layout = QFormLayout(self)

        self._edit_a = QLineEdit(range_a or "")
        self._edit_a.setPlaceholderText("例: 1-5,8(空欄=全ページ)")
        layout.addRow("A範囲", self._edit_a)

        self._edit_b = QLineEdit(range_b or "")
        self._edit_b.setPlaceholderText("例: 1-5,8(空欄=全ページ)")
        layout.addRow("B範囲", self._edit_b)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)

    def result_ranges(self) -> Tuple[Optional[str], Optional[str]]:
        a = self._edit_a.text().strip()
        b = self._edit_b.text().strip()
        return (a or None, b or None)
