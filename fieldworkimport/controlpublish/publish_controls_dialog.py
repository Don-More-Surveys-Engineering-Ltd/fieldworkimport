from __future__ import annotations

from typing import TYPE_CHECKING

from qgis.core import QgsFeature, QgsMessageLog, QgsVectorLayer
from qgis.PyQt.QtWidgets import QDialog, QMessageBox, QWidget

from fieldworkimport.helpers import get_layers_by_table_name, not_NULL
from fieldworkimport.ui.generated.publish_controls_ui import Ui_PublishControlsDialog
from fieldworkimport.ui.publish_control_item import PublishControlItem

if TYPE_CHECKING:
    from fieldworkimport.fwimport.import_process import FieldworkImportLayers


class PublishControlsDialog(QDialog, Ui_PublishControlsDialog):
    layers: FieldworkImportLayers
    selected_fieldwork: QgsFeature | None
    fieldwork_layer: QgsVectorLayer
    fieldworkshot_layer: QgsVectorLayer
    fieldrunshot_layer: QgsVectorLayer
    controlpointdata_layer: QgsVectorLayer
    controlpointcoordinate_layer: QgsVectorLayer
    controlpointelevation_layer: QgsVectorLayer

    def __init__(
        self,
        default_fieldwork: QgsFeature | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.selected_fieldwork = default_fieldwork

        self.fieldwork_layer = get_layers_by_table_name("public", "sites_fieldwork", no_filter=True, raise_exception=True)[0]
        self.fieldworkshot_layer = get_layers_by_table_name("public", "sites_fieldworkshot", no_filter=True, raise_exception=True)[0]
        self.fieldrunshot_layer = get_layers_by_table_name("public", "sites_fieldrunshot", no_filter=True, raise_exception=True)[0]
        self.controlpointdata_layer = get_layers_by_table_name("public", "sites_controlpointdata", no_filter=True, raise_exception=True)[0]
        self.controlpointcoordinate_layer = get_layers_by_table_name("public", "sites_controlpointcoordinate", no_filter=True, raise_exception=True)[0]
        self.controlpointelevation_layer = get_layers_by_table_name("public", "sites_controlpointelevation", no_filter=True, raise_exception=True)[0]

        self.fieldwork_input.setLayer(self.fieldwork_layer)
        self.fieldwork_input.featureChanged.connect(self.selected_fieldwork_changed)

        if not_NULL(self.selected_fieldwork):
            self.fieldwork_input.setFeature(self.selected_fieldwork)
            self.find_elligble_controls()

    def reset_controls_list(self):
        for item in list(self.scrollAreaWidgetContents.children()):
            if isinstance(item, PublishControlItem) and not item.is_valid():
                item.setParent(None)
                del item

    def selected_fieldwork_changed(self):
        self.selected_fieldwork = self.fieldwork_input.feature()
        if not_NULL(self.selected_fieldwork):
            self.find_elligble_controls()

    def add_control(self, control: QgsFeature):
        self.scrollAreaWidgetContents.layout().addWidget(
            PublishControlItem(control, self.fieldrunshot_layer),
        )

    def is_valid(self):
        for item in self.scrollAreaWidgetContents.children():
            if isinstance(item, PublishControlItem) and not item.is_valid():
                return False
        return True

    def find_elligble_controls(self):
        if not not_NULL(self.selected_fieldwork):
            return
        assert self.selected_fieldwork is not None  # noqa: S101
        QgsMessageLog.logMessage(f"{self.selected_fieldwork.attribute('name')=}")
        self.reset_controls_list()
        fieldwork_id = self.selected_fieldwork.attribute("id")

        fieldworkshots: list[QgsFeature] = [*self.fieldworkshot_layer.getFeatures(
            f"""
            fieldwork_id = '{fieldwork_id}' AND
            matching_fieldrun_shot_id is not null AND
            is_processed = true AND
            code in ('CP', 'MON') -- #TODO Don't hard code control point codes
            """,
        )]  # type: ignore []
        QgsMessageLog.logMessage(f"{len(fieldworkshots)=}")

        for shot in fieldworkshots:
            matching_fieldrun_shot = next(self.fieldrunshot_layer.getFeatures(
                f"""
                id = '{shot.attribute('matching_fieldrun_shot_id')}' AND
                type like 'Control'
                """,
            ), None)
            if not matching_fieldrun_shot:
                QgsMessageLog.logMessage(f"shot {shot.attribute('name')} no fieldrunshot")
                continue

            controlpointdata = next(self.controlpointdata_layer.getFeatures(
                f"""
                fieldrun_shot_id = '{matching_fieldrun_shot.attribute('id')}' AND
                primary_coord_id is null
                """,
            ), None)
            if not controlpointdata:
                QgsMessageLog.logMessage(f"shot {shot.attribute('name')} no controlpointdata")
                continue

            self.add_control(shot)

    def publish_controls(self):
        for item in self.scrollAreaWidgetContents.children():
            if not isinstance(item, PublishControlItem):
                continue
            if item.dont_publish_checkbox.isChecked():
                continue
            name = item.control_name_input.text()
            description = item.control_description_input.toPlainText()
            coord_system = item.coordinate_system_input.feature()
            elevation_system = item.elevation_system_input.feature()

            fieldrunshot = item.fieldrun_shot
            controlpointdata = next(self.controlpointdata_layer.getFeatures(f"fieldrun_shot_id = '{fieldrunshot.attribute("id")}'"), None)
            if not controlpointdata:
                msg = "No controlpoint data in publish_controls."
                raise ValueError(msg)
            controlpointdata

    def accept(self) -> None:
        if not self.is_valid():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText("Missing required information.")
            msg.setInformativeText("You forgot to enter one or more required fields.")
            msg.setWindowTitle("Not so fast...")
            msg.exec()
            return None

        self.publish_controls()
        return super().accept()
