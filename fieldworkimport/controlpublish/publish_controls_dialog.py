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
        assert not nullish(self.selected_fieldwork) and isinstance(self.selected_fieldwork, QgsFeature)  # noqa: S101
        self.reset_controls_list()
        fieldwork_id = self.selected_fieldwork["id"]
        with timed("findfind_elligble_controls __internal"):
            fieldworkshots: list[QgsFeature] = [*self.fieldworkshot_layer.getFeatures(
                f"""
                fieldwork_id = '{fieldwork_id}' AND
                is_processed = true AND
                code in ({cp_code_clause})
                """,
            )]  # type: ignore []

            QgsMessageLog.logMessage(f"Fieldwork shots found: {len(fieldworkshots)}")

            for shot in fieldworkshots:
                matched_fieldrun_shot = next(self.fieldrunshot_layer.getFeatures(
                    f"""
                    matched_fieldwork_shot_id = '{shot['id']}' AND
                    type like 'Control' AND
                    (control_easting is null or control_northing is null)
                    """,
                ), None)
                if not matched_fieldrun_shot:
                    QgsMessageLog.logMessage(f"shot {shot['name']} no fieldrunshot")
                    continue

                self.add_control(shot)

    def publish_controls(self):
        self.fieldworkshot_layer.startEditing()
        self.fieldrunshot_layer.startEditing()

        frs_fields = self.fieldrunshot_layer.fields()

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
            # update control point data to set published_by_fieldwork_id
            # lets us know that the control point coords were published by this fieldwork.
            if self.selected_fieldwork:
                fieldrunshot[frs_fields.indexFromName("control_published_by_fieldwork_id")] = self.selected_fieldwork["id"]

            fieldrunshot[frs_fields.indexFromName("control_coordinate_system_id")] = coord_system["id"]
            fieldrunshot[frs_fields.indexFromName("control_easting")] = fieldworkshot["easting"]
            fieldrunshot[frs_fields.indexFromName("control_northing")] = fieldworkshot["northing"]
            fieldrunshot[frs_fields.indexFromName("control_elevation_system_id")] = elevation_system["id"]
            fieldrunshot[frs_fields.indexFromName("control_elevation")] = fieldworkshot["elevation"]
            assert_true(self.fieldrunshot_layer.updateFeature(fieldrunshot), "Failed to update fieldrun shot.")

        fail_msg = "Failed to commit %s."
        assert_true(self.fieldworkshot_layer.commitChanges(), fail_msg % "fieldworkshot")
        assert_true(self.fieldrunshot_layer.commitChanges(), fail_msg % "fieldrunshot")

    def accept(self) -> None:
        if not self.is_valid():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText("Missing required information.")
            msg.setInformativeText("You forgot to enter one or more required fields.")
            msg.setWindowTitle("Not so fast...")
            msg.exec()
            return None

        with progress_dialog("Publishing Controls...") as sp:
            sp(50)
            try:
                self.publish_controls()
            except:
                # try to rollback if possible.
                self.fieldworkshot_layer.rollBack()
                self.fieldrunshot_layer.rollBack()
                raise

        return super().accept()
