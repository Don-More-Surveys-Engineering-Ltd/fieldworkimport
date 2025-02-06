
from typing import Optional, cast

from PyQt5.QtWidgets import QDialog, QTreeWidgetItem, QWidget
from qgis.core import QgsFeature, QgsVectorLayer
from qgis.PyQt import QtCore

from fieldworkimport.common import calc_parent_child_residuals, get_average_point
from fieldworkimport.ui.generated.recalculate_shot_ui import Ui_RecalculateShotDialog


class SameShotTreeWidgetItem(QTreeWidgetItem):
    """Individual shot row."""

    shot: QgsFeature

    def __init__(self, shot: QgsFeature) -> None:
        super().__init__()
        self.shot = shot

        # set special flags
        self.setCheckState(0, QtCore.Qt.Checked)
        self.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
        self.setCheckState(0, QtCore.Qt.Checked)

        cols = [
            f"{self.shot['name']}/{self.shot['code']}",
            self.shot["description"],
            f"{self.shot['easting']:.3f}",
            f"{self.shot['northing']:.3f}",
            f"{self.shot['elevation']:.3f}",
            "",
            "",
            "",
        ]
        for i, text in enumerate(cols):
            self.setText(i, text)

    def is_enabled(self) -> bool:
        return self.checkState(0) == QtCore.Qt.CheckState.Checked

    def shot_residual_from_avg(self, avg: QgsFeature):
        r = calc_parent_child_residuals(avg, self.shot)
        self.setText(5, f"{r[0]:.3f}")
        self.setText(6, f"{r[1]:.3f}")
        self.setText(7, f"{r[2]:.3f}")


class RecalculateShotDialog(QDialog, Ui_RecalculateShotDialog):
    shots: list[QgsFeature]
    layer: QgsVectorLayer

    def __init__(
        self,
        shots: list[QgsFeature],
        layer: QgsVectorLayer,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.shots = shots
        self.layer = layer
        self.setupUi(self)

        # setup rows
        items = []
        for shot in shots:
            parent_tree_item = SameShotTreeWidgetItem(shot)
            items.append(parent_tree_item)

        self.treeWidget.addTopLevelItems(items)
        # expand parent items
        self.treeWidget.expandAll()
        # resize columns to fit data
        for i in range(self.treeWidget.columnCount()):
            self.treeWidget.resizeColumnToContents(i)

        self.treeWidget.itemChanged.connect(self.__on_tree_widget_item_changed)
        self.__recalculate_avg()

    def __on_tree_widget_item_changed(self, _: QTreeWidgetItem) -> None:
        """If a shot is checked/unchecked, recalculate the average."""
        self.__recalculate_avg()

    def __recalculate_avg(self) -> None:
        """Calculate the average shot and display it, and the individual shot residuals."""
        included_shots: list[QgsFeature] = self.get_checked_shots()
        avg_shot = get_average_point(self.layer, included_shots)

        for i in range(self.treeWidget.topLevelItemCount()):
            item = self.treeWidget.topLevelItem(i)
            if isinstance(item, SameShotTreeWidgetItem):
                item = cast("SameShotTreeWidgetItem", item)
                item.shot_residual_from_avg(avg_shot)

        self.avg_coord_text.setText(
            self.avg_coord_text.text()
            .replace("{{easting}}", f"{avg_shot['easting']:.3f}")
            .replace("{{northing}}", f"{avg_shot['northing']:.3f}")
            .replace("{{elevation}}", f"{avg_shot['elevation']:.3f}"),
        )

    def get_checked_shots(self) -> list[QgsFeature]:
        """Return the checked shots."""  # noqa: DOC201
        included_shots: list[QgsFeature] = []
        for i in range(self.treeWidget.topLevelItemCount()):
            item = self.treeWidget.topLevelItem(i)
            if isinstance(item, SameShotTreeWidgetItem):
                item = cast("SameShotTreeWidgetItem", item)
                if item.checkState(0) == QtCore.Qt.CheckState.Checked:
                    included_shots.append(item.shot)
        return included_shots

    def get_unchecked_shots(self) -> list[QgsFeature]:
        """Return the unchecked shots."""  # noqa: DOC201
        included_shots: list[QgsFeature] = []
        for i in range(self.treeWidget.topLevelItemCount()):
            item = self.treeWidget.topLevelItem(i)
            if isinstance(item, SameShotTreeWidgetItem):
                item = cast("SameShotTreeWidgetItem", item)
                if item.checkState(0) == QtCore.Qt.CheckState.Unchecked:
                    included_shots.append(item.shot)
        return included_shots
