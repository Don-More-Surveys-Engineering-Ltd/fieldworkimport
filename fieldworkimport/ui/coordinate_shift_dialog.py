from __future__ import annotations

from typing import Literal, cast

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QCheckBox, QDialog, QGridLayout, QTableWidgetItem, QWidget
from qgis.core import QgsFeature
from qgis.PyQt import QtWidgets

from fieldworkimport.helpers import not_NULL
from fieldworkimport.ui.generated.coordinate_shift_ui import Ui_CoordinateShiftDialog

CoordinateShiftDialogResult = tuple[Literal["NONE", "HPN", "CONTROL"], tuple[float, float, float] | None]


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
    checkbox_by_index: dict[int, CheckBox]
    avg_control_shift: tuple[float, float, float]
    avg_row_index: int | None
    hpn_shift: tuple[float, float, float] | None

    def __init__(
        self,
        hpn_shift: tuple[float, float, float] | None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setupUi(self)
        self.hpn_shift = hpn_shift

        self.fieldwork_shot_by_index = {}
        self.fieldrun_shot_by_index = {}
        self.shift_by_index = {}
        self.checkbox_by_index = {}
        self.avg_control_shift = (0, 0, 0)
        self.avg_row_index = None

        self.control_shift_table.verticalHeader().hide()
        self.control_shift_table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.control_shift_table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)

        self.control_point_shift_radio.toggled.connect(self.on_control_point_shift_toggled)
        self.on_control_point_shift_toggled()

        # set hpn labels
        if self.hpn_shift is not None:
            self.hpn_shift_available_label.setText(
                self.hpn_shift_available_label.text()
                .replace("{{shift_x}}", f"{self.hpn_shift[0]:.3f}")
                .replace("{{shift_y}}", f"{self.hpn_shift[1]:.3f}")
                .replace("{{shift_z}}", f"{self.hpn_shift[2]:.3f}"),
            )
            self.hpn_shift_not_available_label.hide()
        else:
            self.hpn_shift_available_label.hide()

    def on_control_point_shift_toggled(self):
        """Disable table if not checked."""
        checked = self.control_point_shift_radio.isChecked()
        self.control_shift_table.setDisabled(not checked)

    def add_shift_row(
        self,
        fieldwork_shot: QgsFeature,
        fieldrun_shot: QgsFeature,
        shift: tuple[float, float, float | None],
    ):
        """Add a row for a fieldwork shot and fieldrun shot control match."""
        index = self.control_shift_table.rowCount()
        self.fieldwork_shot_by_index[index] = fieldwork_shot
        self.fieldrun_shot_by_index[index] = fieldrun_shot
        self.shift_by_index[index] = shift

        check_box = CheckBox(index, True)
        self.checkbox_by_index[index] = check_box
        check_box.checkedSignal.connect(self.update_avg_shift)
        self.control_shift_table.insertRow(index)
        self.control_shift_table.setCellWidget(
            index,
            0,
            check_box,
        )
        self.control_shift_table.setItem(index, 1, QTableWidgetItem(fieldrun_shot.attribute("name")))
        self.control_shift_table.setItem(index, 2, QTableWidgetItem(fieldwork_shot.attribute("name")))
        self.control_shift_table.setItem(index, 3, QTableWidgetItem(f"{shift[0]:.3f}, {shift[1]:.3f}, {round(shift[2], 3) if not_NULL(shift[2]) else 'N/A'}"))

        for i in range(self.control_shift_table.columnCount()):
            self.control_shift_table.resizeColumnToContents(i)

        self.update_avg_shift()

    def update_avg_shift(self):
        """Calculate avg shift from checked rows and set it on the dialog instance."""
        e_shifts = [
            shift[0] for index, shift in self.shift_by_index.items()
                if (shift[0] and
                self.checkbox_by_index[index].getCheckBox().isChecked())
        ]
        n_shifts = [
            shift[1] for index, shift in self.shift_by_index.items()
                if (shift[1] and
                self.checkbox_by_index[index].getCheckBox().isChecked())
        ]
        z_shifts = [
            shift[2] for index, shift in self.shift_by_index.items()
                if (shift[2] and
                self.checkbox_by_index[index].getCheckBox().isChecked())
        ]
        avg_shift_e = sum(e_shifts, start=0) / max(len(e_shifts), 1)
        avg_shift_n = sum(n_shifts, start=0) / max(len(n_shifts), 1)
        avg_shift_z = sum(z_shifts, start=0) / max(len(z_shifts), 1)
        self.avg_control_shift = (avg_shift_e, avg_shift_n, avg_shift_z)

        # update ui
        if self.avg_row_index:
            self.update_avg_row_shift_value()
            self.update_residuals_column()

    def add_avg_row(self):
        """Add avergae row, after all controls have been added."""
        self.avg_row_index = self.control_shift_table.rowCount()
        self.control_shift_table.insertRow(self.avg_row_index)

        self.update_avg_row_shift_value()
        self.update_residuals_column()

        self.control_shift_table.resizeRowsToContents()
        self.control_shift_table.resizeColumnsToContents()

    def update_avg_row_shift_value(self):
        """Update value of average shift row."""  # noqa: DOC501
        if self.avg_row_index is None:
            msg = "add_avg_row must be called first."
            raise ValueError(msg)
        self.control_shift_table.setItem(
            self.avg_row_index,
            3,
            QTableWidgetItem(f"{self.avg_control_shift[0]:.3f}, {self.avg_control_shift[1]:.3f}, {self.avg_control_shift[2]:.3f}"),
        )
        self.update_residuals_column()

    def update_residuals_column(self):
        """Update residuals column for points, subtracting the point shift from the avg shift."""
        for index, shift in self.shift_by_index.items():
            residual = (
                self.avg_control_shift[0] - shift[0],
                self.avg_control_shift[1] - shift[1],
                (self.avg_control_shift[2] - shift[2]) if shift[2] else None,
            )
            self.control_shift_table.setItem(
                index,
                4,
                QTableWidgetItem(f"{residual[0]:.3f}, {residual[1]:.3f}, {round(residual[2], 3) if not_NULL(residual[2]) else 'N/A'}"),
            )

    def get_result(self) -> CoordinateShiftDialogResult:
        """Return chosen shift type/value."""  # noqa: DOC201, DOC501
        if self.no_shift_radio.isChecked():
            return ("NONE", None)
        if self.hpn_shift_radio.isChecked():
            return ("HPN", self.hpn_shift)
        if self.control_point_shift_radio.isChecked():
            return ("CONTROL", self.avg_control_shift)
        msg = "No shift option selected."
        raise ValueError(msg)
