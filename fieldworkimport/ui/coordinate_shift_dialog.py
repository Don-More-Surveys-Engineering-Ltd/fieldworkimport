from __future__ import annotations

from typing import cast

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QCheckBox, QDialog, QGridLayout, QTableWidgetItem, QWidget
from qgis.core import QgsFeature

from fieldworkimport.ui.generated.coordinate_shift_ui import Ui_CoordinateShiftDialog


class CheckBox(QWidget):
    """Modified version of https://github.com/yjg30737/pyqt-checkbox-table-widget/blob/main/pyqt_checkbox_table_widget/checkBox.py#L5."""

    checkedSignal = pyqtSignal(int, Qt.CheckState)

    def __init__(self, r_idx, flag):
        super().__init__()
        self.__r_idx = r_idx
        self.__initUi(flag)

    def __initUi(self, flag):
        chkBox = QCheckBox()
        chkBox.setChecked(flag)
        chkBox.stateChanged.connect(self.__sendCheckedSignal)

        lay = QGridLayout()
        lay.addWidget(chkBox)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setAlignment(chkBox, Qt.AlignmentFlag.AlignCenter)

        self.setLayout(lay)

    def __sendCheckedSignal(self, flag):
        flag = Qt.CheckState(flag)
        self.checkedSignal.emit(self.__r_idx, flag)

    def isChecked(self):
        f = self.getCheckBox().isChecked()
        return Qt.Checked if f else Qt.Unchecked

    def setChecked(self, f):
        if isinstance(f, Qt.CheckState):
            self.getCheckBox().setCheckState(f)
        elif isinstance(f, bool):
            self.getCheckBox().setChecked(f)

    def getCheckBox(self) -> QCheckBox:
        return cast("QCheckBox", self.layout().itemAt(0).widget())


class CoordinateShiftDialog(QDialog, Ui_CoordinateShiftDialog):
    fieldwork_shot_by_index: dict[int, QgsFeature]
    fieldrun_shot_by_index: dict[int, QgsFeature]
    shift_by_index: dict[int, tuple[float, float, float | None]]

    def __init__(
        self,
        parent: QWidget | None = None,

    ):
        super().__init__(parent)
        self.setupUi(self)

        self.fieldwork_shot_by_index = {}
        self.fieldrun_shot_by_index = {}
        self.shift_by_index = {}

    def add_shift_row(
        self,
        fieldwork_shot: QgsFeature,
        fieldrun_shot: QgsFeature,
        shift: tuple[float, float, float | None],
    ):
        index = self.control_shift_table.rowCount()
        self.fieldwork_shot_by_index[index] = fieldwork_shot
        self.fieldrun_shot_by_index[index] = fieldrun_shot
        self.shift_by_index[index] = shift

        check_box = CheckBox(index, True)
        self.control_shift_table.insertRow(index)
        self.control_shift_table.setCellWidget(
            index,
            0,
            check_box,
        )
        self.control_shift_table.setItem(index, 1, QTableWidgetItem(fieldrun_shot.attribute("name")))
        self.control_shift_table.setItem(index, 2, QTableWidgetItem(fieldwork_shot.attribute("name")))
        self.control_shift_table.setItem(index, 3, QTableWidgetItem(f"{shift[0]:.3f}, {shift[1]:.3f}, {round(shift[2], 3) if shift[2] else 'N/A'}"))

        for i in range(self.control_shift_table.columnCount()):
            self.control_shift_table.resizeColumnToContents(i)
