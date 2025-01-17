
from typing import Optional

from PyQt5.QtWidgets import QDialog, QWidget

from fieldworkimport.ui.generated.point_warnings_ui import Ui_PointWarningsDialog


class PointWarningsDialog(QDialog, Ui_PointWarningsDialog):
    def __init__(
        self,
        hrms_tolerance: float,
        vrms_tolerance: float,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setupUi(self)
        self.tolerances_text.setText(
            self.tolerances_text.text()
            .replace("{{hrms_tolerance}}", f"{hrms_tolerance:.2f}")
            .replace("{{vrms_tolerance}}", f"{vrms_tolerance:.2f}"),
        )
