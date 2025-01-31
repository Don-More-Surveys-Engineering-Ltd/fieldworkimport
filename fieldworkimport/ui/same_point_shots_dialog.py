
from typing import TYPE_CHECKING, Optional, cast

from PyQt5.QtWidgets import QDialog, QTreeWidgetItem, QWidget
from qgis.core import Qgis, QgsFeature, QgsMessageLog, QgsVectorLayer
from qgis.PyQt import QtCore, QtGui

from fieldworkimport.fwimport.merge_helpers import calc_parent_child_residuals, get_average_point
from fieldworkimport.ui.generated.same_point_shots_ui import Ui_SamePointShotsDialog

if TYPE_CHECKING:
    from fieldworkimport.plugin import PluginInput

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
        residuals = calc_parent_child_residuals(parent_point=self.parent_point, child_point=self.point)
        cols = [
            self.point.attribute("name"),
            self.point.attribute("description"),
            f"{self.point.attribute('northing'):.3f}",
            f"{self.point.attribute('easting'):.3f}",
            f"{self.point.attribute('elevation'):.3f}",
            f"{residuals[0]:.3f}",
            f"{residuals[1]:.3f}",
            f"{residuals[2]:.3f}",
        ]
        for i, text in enumerate(cols):
            self.setText(i, text)

    def update_parent(self, parent_point: QgsFeature):
        self.parent_point = parent_point
        self.show_point()


class ParentPointTreeWidgetItem(QTreeWidgetItem):
    parent_point: QgsFeature
    child_points: list[QgsFeature]
    fieldworkshot_layer: QgsVectorLayer
    plugin_input: "PluginInput"

    def __init__(self, fieldworkshot_layer: QgsVectorLayer, child_points: list[QgsFeature], plugin_input: "PluginInput") -> None:
        super().__init__()
        self.fieldworkshot_layer = fieldworkshot_layer
        self.child_points = child_points
        self.plugin_input = plugin_input
        self.parent_point = get_average_point(self.fieldworkshot_layer, self.child_points, self.plugin_input)

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
            self.parent_point.attribute("description"),
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
        self.parent_point = get_average_point(self.fieldworkshot_layer, features, self.plugin_input)
        self.show_point()

        # update children with new point
        for i in range(self.childCount()):
            child = cast("ChildPointTreeWidgetItem", self.child(i))
            child.update_parent(self.parent_point)

    def get_checked_child_points(self) -> list[QgsFeature]:
        features = []
        for i in range(self.childCount()):
            child = cast("ChildPointTreeWidgetItem", self.child(i))
            if child.checkState(0) == QtCore.Qt.CheckState.Checked:
                features.append(child.point)
        return features

    def is_enabled(self) -> bool:
        return self.checkState(0) == QtCore.Qt.CheckState.Checked


class SamePointShotsDialog(QDialog, Ui_SamePointShotsDialog):
    final_groups: list[list[QgsFeature]]

    def __init__(
        self,
        fieldworkshot_layer: QgsVectorLayer,
        groups: list[list[QgsFeature]],
        plugin_input: "PluginInput",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.final_groups = []
        self.setupUi(self)

        # show actual tolerance in label
        self.tolerance_text.setText(self.tolerance_text.text().replace("{{same_point_tolerance}}", f"{plugin_input.same_point_tolerance:.2f}"))  # noqa: E501

        # setup rows
        items = []
        for group in groups:
            parent_tree_item = ParentPointTreeWidgetItem(fieldworkshot_layer, child_points=group, plugin_input=plugin_input)
            items.append(parent_tree_item)

        self.tree_widget.addTopLevelItems(items)
        # expand parent items
        self.tree_widget.expandAll()
        # resize columns to fit data
        for i in range(self.tree_widget.columnCount()):
            self.tree_widget.resizeColumnToContents(i)

        self.tree_widget.itemChanged.connect(self.on_tree_widget_item_changed)

    def on_tree_widget_item_changed(self, item: QTreeWidgetItem):
        if isinstance(item, ChildPointTreeWidgetItem):
            item = cast("ChildPointTreeWidgetItem", item)
            item.parent_point_widget_item.recalc_point()

    def get_final_groups(self) -> list[list[QgsFeature]]:
        """Get the list of groups of points."""  # noqa: DOC201
        groups = []
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            if not isinstance(item, ParentPointTreeWidgetItem):
                QgsMessageLog.logMessage("Expected only ParentPointTreeWidgetItems in top level items.", level=Qgis.MessageLevel.Critical)
                continue
            # skip unchecked parent points
            if item.checkState(0) != QtCore.Qt.CheckState.Checked:
                continue
            item = cast("ParentPointTreeWidgetItem", item)
            group = item.get_checked_child_points()
            # don't append empty groups
            if len(group) >= 2:  # noqa: PLR2004
                groups.append(group)
        return groups

    def accept(self) -> None:
        self.final_groups = self.get_final_groups()
        return super().accept()
