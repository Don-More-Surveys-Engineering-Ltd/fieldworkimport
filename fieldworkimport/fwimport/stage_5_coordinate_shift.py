from __future__ import annotations

from typing import TYPE_CHECKING

from qgis.core import QgsFeature, QgsMessageLog, QgsSettings

from fieldworkimport.helpers import assert_true, nullish, settings_key
from fieldworkimport.ui.coordinate_shift_dialog import CoordinateShiftDialog, CoordinateShiftDialogResult

if TYPE_CHECKING:
    from fieldworkimport.fwimport.import_process import FieldworkImportLayers
    from fieldworkimport.plugin import PluginInput


class CoordinateShiftStage:
    layers: FieldworkImportLayers
    fw_matching_fieldrun_shot_id_index: int
    fieldwork: QgsFeature
    fieldrun_id: int | None
    plugin_input: PluginInput

    def __init__(  # noqa: D107
        self,
        layers: FieldworkImportLayers,
        fieldwork: QgsFeature,
        fieldrun_id: int | None,
        plugin_input: PluginInput,
    ) -> None:
        self.layers = layers
        self.fieldwork = fieldwork
        self.fieldrun_id = fieldrun_id
        self.plugin_input = plugin_input

        fw_fields = self.layers.fieldworkshot_layer.fields()
        self.fw_matching_fieldrun_shot_id_index = fw_fields.indexFromName("matching_fieldrun_shot_id")

    def run(self):
        QgsMessageLog.logMessage(
            "CoordinateShiftStage.run started.",
        )
        s = QgsSettings()
        control_point_codes = s.value(settings_key("control_point_codes")).split(",")
        cp_code_clause = ", ".join([f"'{code}'" for code in control_point_codes])

        hpn_shift = self.calculate_hpn_shift()
        dialog = CoordinateShiftDialog(hpn_shift=hpn_shift)

        points: list[QgsFeature] = [*self.layers.fieldworkshot_layer.getFeatures(
            f"""
            fieldwork_id = '{self.fieldwork['id']}' AND
            code in ({cp_code_clause}) AND
            matching_fieldrun_shot_id is not null
            """,
        )]  # type: ignore []

        for fieldworkshot in points:
            fieldrunshot = next(self.layers.fieldrunshot_layer.getFeatures(f"id = '{fieldworkshot['matching_fieldrun_shot_id']}'"))  # noqa: E501
            controlpointdata = next(self.layers.controlpointdata_layer.getFeatures(f"fieldrun_shot_id = '{fieldrunshot['id']}'"), None)  # noqa: E501
            if not controlpointdata:
                QgsMessageLog.logMessage(f"Matched fieldrunshot has no controlpoint data. ({fieldrunshot['id']=})")
                continue

            published_easting = controlpointdata["easting"]
            published_northing = controlpointdata["northing"]
            published_elevation = controlpointdata["elevation"]

            # check if easting an northing is set, and if not, it's new and we can't use it for a shift
            if nullish(published_easting) or nullish(published_northing):
                continue

            measured_easting = fieldworkshot["easting"]
            measured_northing = fieldworkshot["northing"]
            measured_elevation = fieldworkshot["elevation"]
            shift = (
                published_easting - measured_easting,
                published_northing - measured_northing,
                (published_elevation - measured_elevation) if not nullish(published_elevation) else None,
            )

            dialog.add_shift_row(
                fieldworkshot,
                fieldrunshot,
                shift,
            )

        # done adding matches / shifts, tell dialog to add the average shift row
        dialog.add_avg_row()
        # show and wait for dialog
        dialog.exec_()

        # apply shift
        result = dialog.get_result()

        self.apply_shift(result)

    def _apply_shift_to_fieldwork(self, result: CoordinateShiftDialogResult, fieldwork: QgsFeature) -> None:
        """Apply shift from dialog to fieldwork."""
        shift_type, shift, selected_fieldrunshots = result
        ids = [shot["id"] for shot in (selected_fieldrunshots or [])]
        ids_str = ",".join(ids)

        fieldwork = next(self.layers.fieldwork_layer.getFeatures(f"\"id\"='{fieldwork["id"]}'"))
        fieldwork.setAttribute("shift_type", shift_type)
        fieldwork.setAttribute("shift_control_ids", ids_str)
        if shift:
            fieldwork.setAttribute("easting_shift", shift[0])
            fieldwork.setAttribute("northing_shift", shift[1])
            fieldwork.setAttribute("elevation_shift", shift[2])

        assert_true(self.layers.fieldwork_layer.updateFeature(fieldwork), "Failed to update fieldwork with shift.")

    def _apply_shift_to_fieldworkshot(self, result: CoordinateShiftDialogResult, fieldworkshot: QgsFeature) -> None:
        """Apply shift from dialog to fieldwork point."""
        fields = self.layers.fieldworkshot_layer.fields()
        easting_idx = fields.indexFromName("easting")
        northing_idx = fields.indexFromName("northing")
        elevation_idx = fields.indexFromName("elevation")

        _, shift, _ = result

        if shift:
            if fieldworkshot[easting_idx]:
                fieldworkshot[easting_idx] += shift[0]
            if fieldworkshot[northing_idx]:
                fieldworkshot[northing_idx] += shift[1]
            if fieldworkshot[elevation_idx]:
                fieldworkshot[elevation_idx] += shift[2]
            assert_true(self.layers.fieldworkshot_layer.updateFeature(fieldworkshot), "Failed to update fieldwork shot with shift.")

    def apply_shift(self, result: CoordinateShiftDialogResult) -> None:
        """Apply shift from dialog."""
        # apply to fieldwork
        self._apply_shift_to_fieldwork(result, self.fieldwork)

        _, shift, _ = result
        if shift:
            points: list[QgsFeature] = [
                *self.layers.fieldworkshot_layer.getFeatures(
                    f"""
                    "fieldwork_id" = '{self.fieldwork['id']}'
                    """,
                ),  # type: ignore []
            ]
            # apply to each point in fieldwork
            for point in points:
                self._apply_shift_to_fieldworkshot(result, point)

    def calculate_hpn_shift(self) -> tuple[float, float, float] | None:  # noqa: D102
        SUM_easting = self.fieldwork["SUM_easting"]  # noqa: N806
        SUM_northing = self.fieldwork["SUM_northing"]  # noqa: N806
        SUM_elevation = self.fieldwork["SUM_elevation"]  # noqa: N806
        SUM_geoid_seperation = self.fieldwork["SUM_geoid_seperation"]  # noqa: N806
        REF_easting = self.fieldwork["REF_easting"]  # noqa: N806
        REF_northing = self.fieldwork["REF_northing"]  # noqa: N806
        REF_elevation = self.fieldwork["REF_elevation"]  # noqa: N806
        LOC_grid_easting = self.fieldwork["LOC_grid_easting"]  # noqa: N806
        LOC_grid_northing = self.fieldwork["LOC_grid_northing"]  # noqa: N806
        LOC_grid_elevation = self.fieldwork["LOC_grid_elevation"]  # noqa: N806
        LOC_measured_easting = self.fieldwork["LOC_measured_easting"]  # noqa: N806
        LOC_measured_northing = self.fieldwork["LOC_measured_northing"]  # noqa: N806
        LOC_measured_elevation = self.fieldwork["LOC_measured_elevation"]  # noqa: N806

        if not all(
            var for var in [
                SUM_easting,
                SUM_northing,
                SUM_elevation,
                SUM_geoid_seperation,
                REF_easting,
                REF_northing,
                REF_elevation,
            ]
        ):
            return None

        east = SUM_easting - REF_easting
        north = SUM_northing - REF_northing
        elv = SUM_elevation - REF_elevation + SUM_geoid_seperation

        if all(
            var for var in [
                LOC_grid_easting,
                LOC_grid_northing,
                LOC_grid_elevation,
                LOC_measured_easting,
                LOC_measured_northing,
                LOC_measured_elevation,
            ]
        ):
            east -= LOC_grid_easting - LOC_measured_easting
            north -= LOC_grid_northing - LOC_measured_northing
            elv -= LOC_grid_elevation - LOC_measured_elevation

        return (
            east,
            north,
            elv,
        )
