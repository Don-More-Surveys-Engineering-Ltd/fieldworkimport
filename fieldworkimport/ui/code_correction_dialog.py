from typing import Optional

from PyQt5.QtWidgets import QDialog, QMessageBox, QWidget

from fieldworkimport.common import validate_code
from fieldworkimport.ui.generated.code_correction_ui import Ui_CodeCorrectionDialog


class CodeCorrectionDialog(QDialog, Ui_CodeCorrectionDialog):
    def __init__(
        self,
        description: str,
        valid_codes: list[str],
        valid_special_chars: list[str],
        parameterized_special_chars: list[str],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setupUi(self)
        self.description = description
        self.code = self.description_to_code(description)
        self.valid_codes = valid_codes
        self.valid_special_chars = valid_special_chars
        self.parameterized_special_chars = parameterized_special_chars

        self.original_code_label.setText(description)
        self.correction_input.setText(description)

    @staticmethod
    def description_to_code(description: str):
        return description.split("/")[0]

    def accept(self) -> None:
        self.description = self.correction_input.text()
        self.code = self.description_to_code(self.description)
        is_valid = validate_code(self.code, valid_codes=self.valid_codes, valid_special_characters=self.valid_special_chars, parameterized_special_characters=self.parameterized_special_chars)
        # validate requried fields.
        if not is_valid or not self.code:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText("Invalid code correction.")
            msg.setInformativeText(f"'{self.code}' is not valid. Please try again or click 'ignore' to ignore the exception.")
            msg.setWindowTitle("Not so fast...")
            msg.exec()
            return None

        return super().accept()
