from typing import Optional

from PyQt5.QtWidgets import QDialog, QWidget

from fieldworkimport.ui.generated.import_finished_ui import Ui_ImportFinishedDialog


class ImportFinishedDialog(QDialog, Ui_ImportFinishedDialog):
    def __init__(self, parent: Optional[QWidget] = None):  # noqa: FA100
        super().__init__(parent)
        self.setupUi(self)
