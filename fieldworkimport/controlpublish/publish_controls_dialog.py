from __future__ import annotations

from typing import TYPE_CHECKING

from qgis.core import QgsFeature, QgsMessageLog, QgsSettings, QgsVectorLayer
from qgis.PyQt.QtWidgets import QDialog, QMessageBox, QWidget

from fieldworkimport.helpers import assert_true, get_layers_by_table_name, nullish, progress_dialog, settings_key, timed
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

        self.fieldwork_input.setLayer(self.fieldwork_layer)
        self.fieldwork_input.featureChanged.connect(self.selected_fieldwork_changed)
        if default_fieldwork:
            self.fieldwork_input.setFeature(default_fieldwork.id())
            self.find_elligble_controls()

    def reset_controls_list(self):
        for item in list(self.scrollAreaWidgetContents.children()):
            if isinstance(item, PublishControlItem):
                item.setParent(None)  # type: ignore
                del item

    def selected_fieldwork_changed(self):
        self.selected_fieldwork = self.fieldwork_input.feature()
        if not nullish(self.selected_fieldwork):
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
        s = QgsSettings()
        control_point_codes = s.value(settings_key("control_point_codes")).split(",")
        cp_code_clause = ", ".join([f"'{code}'" for code in control_point_codes])
        if nullish(self.selected_fieldwork):
            return
        assert self.selected_fieldwork is not None  # noqa: S101
        self.reset_controls_list()
        fieldwork_id = self.selected_fieldwork["id"]
        with timed("findfind_elligble_controls __internal"):
            fieldworkshots: list[QgsFeature] = [*self.fieldworkshot_layer.getFeatures(
                f"""
                fieldwork_id = '{fieldwork_id}' AND
                matching_fieldrun_shot_id is not null AND
                is_processed = true AND
                code in ({cp_code_clause})
                """,
            )]  # type: ignore []

            QgsMessageLog.logMessage(f"Fieldwork shots found: {len(fieldworkshots)}")

            for shot in fieldworkshots:
                matching_fieldrun_shot = next(self.fieldrunshot_layer.getFeatures(
                    f"""
                    id = '{shot['matching_fieldrun_shot_id']}' AND
                    type like 'Control'
                    """,
                ), None)
                if not matching_fieldrun_shot:
                    QgsMessageLog.logMessage(f"shot {shot['name']} no fieldrunshot")
                    continue

                controlpointdata = next(self.controlpointdata_layer.getFeatures(
                    f"""
                    fieldrun_shot_id = '{matching_fieldrun_shot['id']}' AND
                    (easting is null or northing is null)
                    """,
                ), None)
                if not controlpointdata:
                    QgsMessageLog.logMessage(f"shot {shot['name']} no controlpointdata")
                    continue

                self.add_control(shot)

    def publish_controls(self):
        self.fieldworkshot_layer.startEditing()
        self.fieldrunshot_layer.startEditing()
        self.controlpointdata_layer.startEditing()

        frs_fields = self.fieldrunshot_layer.fields()
        cpd_fields = self.controlpointdata_layer.fields()

        for item in self.scrollAreaWidgetContents.children():
            if not isinstance(item, PublishControlItem):
                continue
            if item.dont_publish_checkbox.isChecked():
                continue
            name = item.control_name_input.text()
            description = item.control_description_input.toPlainText()
            coord_system = item.coordinate_system_input.feature()
            elevation_system = item.elevation_system_input.feature()

            fieldworkshot = item.fieldwork_shot
            fieldrunshot = item.fieldrun_shot
            fieldrunshot[frs_fields.indexFromName("name")] = name
            fieldrunshot[frs_fields.indexFromName("description")] = description
            assert_true(self.fieldrunshot_layer.updateFeature(fieldrunshot), "Failed to update fieldrun shot.")

            controlpointdata = next(self.controlpointdata_layer.getFeatures(f"fieldrun_shot_id = '{fieldrunshot["id"]}'"), None)  # noqa: E501
            if not controlpointdata:
                msg = "No controlpoint data in publish_controls."
                raise ValueError(msg)
            # update control point data to set published_by_fieldwork_id
            # lets us know that the control point coords were published by this fieldwork.
            if self.selected_fieldwork:
                controlpointdata[cpd_fields.indexFromName("published_by_fieldwork_id")] = self.selected_fieldwork["id"]

            controlpointdata[cpd_fields.indexFromName("coordinate_system_id")] = coord_system["id"]
            controlpointdata[cpd_fields.indexFromName("easting")] = fieldworkshot["easting"]
            controlpointdata[cpd_fields.indexFromName("northing")] = fieldworkshot["northing"]
            controlpointdata[cpd_fields.indexFromName("elevation_system_id")] = elevation_system["id"]
            controlpointdata[cpd_fields.indexFromName("elevation")] = fieldworkshot["elevation"]
            assert_true(self.controlpointdata_layer.updateFeature(controlpointdata), "Failed to update controlpoint data.")

        fail_msg = "Failed to commit %s."
        assert_true(self.fieldworkshot_layer.commitChanges(), fail_msg % "fieldworkshot")
        assert_true(self.fieldrunshot_layer.commitChanges(), fail_msg % "fieldrunshot")
        assert_true(self.controlpointdata_layer.commitChanges(stopEditing=False), fail_msg % "controlpointdata")

        try:
            assert_true(self.controlpointdata_layer.commitChanges(), fail_msg % "controlpointdata (second commit)")
        except:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Commit error...")
            msg.setInformativeText("Part 2 of the coordinate publishing routine failed, and you may be left with invalid data.")  # noqa: E501
            msg.setWindowTitle("Failed")
            msg.exec()
            raise

    def accept(self) -> None:
        if not self.is_valid():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText("Missing required information.")
            msg.setInformativeText("You forgot to enter one or more required fields.")
            msg.setWindowTitle("Not so fast...")
            msg.exec()
            return None

        with progress_dialog("Publishing Controls...", indeterminate=True):
            try:
                self.publish_controls()
            except:
                # try to rollback if possible.
                self.fieldworkshot_layer.rollBack()
                self.controlpointdata_layer.rollBack()
                self.fieldrunshot_layer.rollBack()
                raise

        return super().accept()
