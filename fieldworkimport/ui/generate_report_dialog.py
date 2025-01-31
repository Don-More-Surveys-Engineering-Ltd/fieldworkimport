from typing import Optional

from PyQt5.QtWidgets import QDialog, QMessageBox, QWidget

from fieldworkimport.helpers import get_layers_by_table_name, not_NULL
from fieldworkimport.ui.generated.generate_report_ui import Ui_GenerateReportDialog


class GenerateReportDialog(QDialog, Ui_GenerateReportDialog):
    def __init__(self, parent: Optional[QWidget] = None):  # noqa: FA100
        super().__init__(parent)
        self.setupUi(self)
        fieldwork_layer = get_layers_by_table_name("public", "sites_fieldwork", raise_exception=True, no_filter=True)[0]
        self.fieldwork_input.setLayer(fieldwork_layer)

    def accept(self) -> None:
        fieldwork = self.fieldwork_input.feature()
        if not not_NULL(fieldwork):
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText("Invalid code correction.")
            msg.setInformativeText("Choose a fieldwork.")
            msg.setWindowTitle("Not so fast...")
            msg.exec()
            return None

        return super().accept()
