from typing import Optional

from PyQt5.QtWidgets import QDialog, QMessageBox, QWidget
from qgis.core import NULL

from fieldworkimport.helpers import get_layers_by_table_name
from fieldworkimport.ui.generated.deletedialog_ui import Ui_DeleteDialog


class DeleteFieldworkDialog(QDialog, Ui_DeleteDialog):
    def __init__(self, parent: Optional[QWidget] = None):  # noqa: FA100
        super().__init__(parent)
        self.setupUi(self)

        self.fieldwork_layer = get_layers_by_table_name("public", "sites_fieldwork", raise_exception=True, no_filter=True)[0]
        self.fieldwork_input.setLayer(self.fieldwork_layer)

    def accept(self) -> None:
        fieldwork = self.fieldwork_input.feature()

        # validate requried fields.
        if not fieldwork or fieldwork == NULL:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText("Missing required information.")
            msg.setInformativeText("You forgot to enter one or more required fields (fieldwork).")
            msg.setWindowTitle("Not so fast...")
            msg.exec()
            return None

        return super().accept()
