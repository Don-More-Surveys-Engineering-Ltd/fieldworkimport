
import string
from typing import Optional, cast
from uuid import uuid4

from PyQt5.QtWidgets import QDialog, QTreeWidgetItem, QWidget
from qgis.core import QgsFeature
from qgis.PyQt import QtCore, QtGui

from fieldworkimport.fieldwork.helpers import get_layers_by_table_name
from fieldworkimport.ui.generated.same_point_shots_ui import Ui_SamePointShotsDialog


def parent_name(name: str):
    if name[-1] not in string.ascii_letters:
        return name + "A"
    if name[-1] == "Z":
        return name + "A"
    return name[:-1] + chr(ord(name[-1]) + 1)


def get_merged_point(points: list[QgsFeature]) -> QgsFeature:  # noqa: D103, PLR0914
    n = len(points)

    layer = get_layers_by_table_name("public", "sites_fieldworkshot", no_filter=True, raise_exception=True)[0]
    f = QgsFeature(points[0])
    fields = layer.fields()
    id_index = fields.indexFromName("id")
    name_index = fields.indexFromName("name")
    northing_index = fields.indexFromName("northing")
    easting_index = fields.indexFromName("easting")
    elevation_index = fields.indexFromName("elevation")
    HRMS_index = fields.indexFromName("HRMS")  # noqa: N806
    VRMS_index = fields.indexFromName("VRMS")  # noqa: N806
    PDOP_index = fields.indexFromName("PDOP")  # noqa: N806
    HDOP_index = fields.indexFromName("HDOP")  # noqa: N806
    VDOP_index = fields.indexFromName("VDOP")  # noqa: N806
    TDOP_index = fields.indexFromName("TDOP")  # noqa: N806
    GDOP_index = fields.indexFromName("GDOP")  # noqa: N806

    n_with_HRMS = len([p for p in points if p[HRMS_index]])  # noqa: N806
    n_with_VRMS = len([p for p in points if p[VRMS_index]])  # noqa: N806
    n_with_PDOP = len([p for p in points if p[PDOP_index]])  # noqa: N806
    n_with_HDOP = len([p for p in points if p[HDOP_index]])  # noqa: N806
    n_with_VDOP = len([p for p in points if p[VDOP_index]])  # noqa: N806
    n_with_TDOP = len([p for p in points if p[TDOP_index]])  # noqa: N806
    n_with_GDOP = len([p for p in points if p[GDOP_index]])  # noqa: N806

    f[id_index] = str(uuid4())
    f[name_index] = parent_name(f[name_index])
    f[northing_index] = sum(p[northing_index] for p in points) / n
    f[easting_index] = sum(p[easting_index] for p in points) / n
    f[elevation_index] = sum(p[elevation_index] for p in points) / n
    f[HRMS_index] = sum(p[HRMS_index] for p in points if p[HRMS_index]) / max(n_with_HRMS, 1)
    f[VRMS_index] = sum(p[VRMS_index] for p in points if p[VRMS_index]) / max(n_with_VRMS, 1)
    f[PDOP_index] = sum(p[PDOP_index] for p in points if p[PDOP_index]) / max(n_with_PDOP, 1)
    f[HDOP_index] = sum(p[HDOP_index] for p in points if p[HDOP_index]) / max(n_with_HDOP, 1)
    f[VDOP_index] = sum(p[VDOP_index] for p in points if p[VDOP_index]) / max(n_with_VDOP, 1)
    f[TDOP_index] = sum(p[TDOP_index] for p in points if p[TDOP_index]) / max(n_with_TDOP, 1)
    f[GDOP_index] = sum(p[GDOP_index] for p in points if p[GDOP_index]) / max(n_with_GDOP, 1)

    return f


def calc_residuals(parent_point: QgsFeature, child_point: QgsFeature):
    parent_point_northing = parent_point.attribute("northing")
    parent_point_easting = parent_point.attribute("easting")
    parent_point_elevation = parent_point.attribute("elevation")
    child_point_northing = child_point.attribute("northing")
    child_point_easting = child_point.attribute("easting")
    child_point_elevation = child_point.attribute("elevation")

    return (
        parent_point_northing - child_point_northing,
        parent_point_easting - child_point_easting,
        parent_point_elevation - child_point_elevation,
    )


PARENT_POINT_TREE_WIDGET_FONT = QtGui.QFont()
PARENT_POINT_TREE_WIDGET_FONT.setPointSize(11)
PARENT_POINT_TREE_WIDGET_FONT.setBold(True)
PARENT_POINT_TREE_WIDGET_FONT.setWeight(75)


class ChildPointTreeWidgetItem(QTreeWidgetItem):
    point: QgsFeature
    parent_point: QgsFeature
    parent_point_widget_item: "ParentPointTreeWidgetItem"

    last_checked_state = None

    def __init__(self, point: QgsFeature, parent_point: QgsFeature, parent_point_widget_item: "ParentPointTreeWidgetItem") -> None:
        super().__init__()
        self.point = point
        self.parent_point = parent_point
        self.parent_point_widget_item = parent_point_widget_item
        self.show_point()

        self.setCheckState(0, QtCore.Qt.Checked)
        self.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
        self.setCheckState(0, QtCore.Qt.Checked)

        self.last_checked_state = True

    def show_point(self):
        residuals = calc_residuals(parent_point=self.parent_point, child_point=self.point)
        cols = [
            self.point.attribute("name"),
            f"{self.point.attribute('northing'):.3f}",
            f"{self.point.attribute('easting'):.3f}",
            f"{self.point.attribute('elevation'):.3f}",
            f"{residuals[0]:.3f}",
            f"{residuals[1]:.3f}",
            f"{residuals[2]:.3f}",
        ]
        for i, text in enumerate(cols):
            self.setText(i, text)

    def setData(self, column: int, role: int, value) -> None:
        checked = self.checkState(0) == QtCore.Qt.CheckState.Checked
        # prevents infinite loop
        if checked != self.last_checked_state:
            self.parent_point_widget_item.recalc_point()
        self.last_checked_state = checked
        return super().setData(column, role, value)

    def update_parent(self, parent_point: QgsFeature):
        self.parent_point = parent_point
        self.show_point()


class ParentPointTreeWidgetItem(QTreeWidgetItem):
    parent_point: QgsFeature
    child_points: list[QgsFeature]

    def __init__(self, child_points: list[QgsFeature]) -> None:
        super().__init__()
        self.child_points = child_points
        self.parent_point = get_merged_point(self.child_points)

        # set special font for parent
        for i in range(self.columnCount()):
            self.setFont(i, PARENT_POINT_TREE_WIDGET_FONT)

        # set special flags
        self.setCheckState(0, QtCore.Qt.Checked)
        self.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
        self.setCheckState(0, QtCore.Qt.Checked)

        self.show_point()

        # generate rows for children
        for point in self.child_points:
            child_tree_item = ChildPointTreeWidgetItem(point, parent_point=self.parent_point, parent_point_widget_item=self)

            self.addChild(child_tree_item)

    def show_point(self):
        cols = [
            f"{self.parent_point.attribute('name')}/{self.parent_point.attribute('code')}",
            f"{self.parent_point.attribute('northing'):.3f}",
            f"{self.parent_point.attribute('easting'):.3f}",
            f"{self.parent_point.attribute('elevation'):.3f}",
            "",
            "",
            "",
        ]
        for i, text in enumerate(cols):
            self.setText(i, text)

    def recalc_point(self):
        features = []
        for i in range(self.childCount()):
            child = cast("ChildPointTreeWidgetItem", self.child(i))
            if child.checkState(0) == QtCore.Qt.CheckState.Checked:
                features.append(child.point)
        if not features:
            return
        self.parent_point = get_merged_point(features)
        self.show_point()

        # update children with new point
        for i in range(self.childCount()):
            child = cast("ChildPointTreeWidgetItem", self.child(i))
            child.update_parent(self.parent_point)


class SamePointShotsDialog(QDialog, Ui_SamePointShotsDialog):
    def __init__(
        self,
        same_point_tolerance: float,
        groups: list[list[QgsFeature]],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setupUi(self)

        # show actual tolerance in label
        self.tolerance_text.setText(self.tolerance_text.text().replace("{{same_point_tolerance}}", f"{same_point_tolerance:.2f}"))  # noqa: E501

        # setup rows
        items = []
        for group in groups:
            parent_tree_item = ParentPointTreeWidgetItem(child_points=group)
            items.append(parent_tree_item)

        self.tree_widget.addTopLevelItems(items)
        # expand parent items
        self.tree_widget.expandAll()
        # resize columns to fit data
        for i in range(self.tree_widget.columnCount()):
            self.tree_widget.resizeColumnToContents(i)
