
from typing import Optional

from PyQt5.QtWidgets import QDialog, QWidget
from qgis.core import Qgis, QgsFeature, QgsMessageLog

from fieldworkimport.ui.generated.match_to_controls_ui import Ui_MatchControlPoints
from fieldworkimport.ui.match_control_item import ControlMatchResult, MatchControlItem


class MatchToControlsDialog(QDialog, Ui_MatchControlPoints):
    results: list[tuple[QgsFeature, ControlMatchResult]]
    """tuples of [FieldworkShot, ControlMatchResult]"""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setupUi(self)
        self.scrollAreaContents.layout().setSpacing(0)
        self.results = []

    def store_result(self):
        for child in self.scrollAreaContents.children():
            QgsMessageLog.logMessage("child", level=Qgis.MessageLevel.Info)
            if isinstance(child, MatchControlItem):
                QgsMessageLog.logMessage("match child", level=Qgis.MessageLevel.Info)
                result = child.get_result()
                if result:
                    self.results.append((child.fieldwork_shot, result))

    def accept(self) -> None:
        # store result before tearing down ui
        self.store_result()
        return super().accept()
