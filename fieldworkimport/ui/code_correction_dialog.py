from typing import Optional

from PyQt5.QtWidgets import QDialog, QMessageBox, QWidget

from fieldworkimport.ui.generated.code_correction_ui import Ui_CodeCorrectionDialog
from fieldworkimport.validate.validate_code import validate_code


class CodeCorrectionDialog(QDialog, Ui_CodeCorrectionDialog):
    def __init__(
        self,
        code: str,
        valid_codes: list[str],
        valid_special_chars: list[str],
        parameterized_special_chars: list[str],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setupUi(self)
        self.code = code
        self.valid_codes = valid_codes
        self.valid_special_chars = valid_special_chars
        self.parameterized_special_chars = parameterized_special_chars

        self.original_code_text.setText(code)
        self.correction_input.setText(code)

    def accept(self) -> None:
        code = self.correction_input.text()
        is_valid = validate_code(code, valid_codes=self.valid_codes, valid_special_characters=self.valid_special_chars, parameterized_special_characters=self.parameterized_special_chars)
        # validate requried fields.
        if not is_valid or not code:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText("Invalid code correction.")
            msg.setInformativeText(f"'{code}' is not valid. Please try again or click 'ignore' to ignore the exception.")
            msg.setWindowTitle("Not so fast...")
            msg.exec()
            return None

        return super().accept()
