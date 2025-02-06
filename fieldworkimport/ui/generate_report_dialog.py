from typing import Optional

from PyQt5.QtWidgets import QDialog, QMessageBox, QWidget
from qgis.core import QgsFeature

from fieldworkimport.helpers import get_layers_by_table_name, nullish
from fieldworkimport.ui.generated.generate_report_ui import Ui_GenerateReportDialog


class GenerateReportDialog(QDialog, Ui_GenerateReportDialog):
    def __init__(self, default_fieldwork: QgsFeature | None, default_output_folder: str | None, parent: Optional[QWidget] = None):  # noqa: FA100
        super().__init__(parent)
        self.setupUi(self)
        fieldwork_layer = get_layers_by_table_name("public", "sites_fieldwork", raise_exception=True, no_filter=True)[0]
        self.fieldwork_input.setLayer(fieldwork_layer)
        if default_fieldwork:
            self.fieldwork_input.setFeature(default_fieldwork.id())
        if default_output_folder:
            self.output_folder_input.setFilePath(default_output_folder)

    def accept(self) -> None:
        fieldwork = self.fieldwork_input.feature()
        output_folder_path = self.output_folder_input.filePath()
        if nullish(fieldwork) or not output_folder_path:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText("Invalid code correction.")
            msg.setInformativeText("Choose a fieldwork.")
            msg.setWindowTitle("Not so fast...")
            msg.exec()
            return None

        return super().accept()
