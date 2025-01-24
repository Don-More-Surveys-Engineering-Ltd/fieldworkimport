from __future__ import annotations

from typing import TYPE_CHECKING

from qgis.core import QgsFeature, QgsMessageLog
from qgis.PyQt.QtSql import QSqlQuery

from fieldworkimport.helpers import layer_database_connection
from fieldworkimport.ui.coordinate_shift_dialog import CoordinateShiftDialog, CoordinateShiftDialogResult

if TYPE_CHECKING:
    from fieldworkimport.process import FieldworkImportLayers


class CoordinateShiftStage:
    layers: FieldworkImportLayers
    fw_matching_fieldrun_shot_id_index: int
    fieldwork: QgsFeature
    fieldrun_id: int | None
    control_point_codes: list[str]

    def __init__(  # noqa: D107
        self,
        layers: FieldworkImportLayers,
        fieldwork: QgsFeature,
        fieldrun_id: int | None,
        control_point_codes: list[str],
    ) -> None:
        self.layers = layers
        self.fieldwork = fieldwork
        self.fieldrun_id = fieldrun_id
        self.control_point_codes = control_point_codes

        fw_fields = self.layers.fieldworkshot_layer.fields()
        self.fw_matching_fieldrun_shot_id_index = fw_fields.indexFromName("matching_fieldrun_shot_id")

    def run(self):
        QgsMessageLog.logMessage(
            "CoordinateShiftStage.run started.",
        )
        cp_code_clause = ", ".join([f"'{code}'" for code in self.control_point_codes])

        hpn_shift = self.calculate_hpn_shift()
        dialog = CoordinateShiftDialog(hpn_shift=hpn_shift)

        # get suitable controls for shift, and add them w/ their shifts to the dialog
        with layer_database_connection(self.layers.fieldrunshot_layer) as db:
            query = QSqlQuery(db)
            # get the fieldwork shots that have fieldrun shots, are controls, and the matching fieldrun shots
            # have primary coords. Do this with a QUADRUPLE join, that:
            # - starts with fieldworkshots table
            # - joins matching fieldrun shots
            # - joins the fieldrun shot's controlpointdata
            # - joins the controlpointdata's primary coord
            # - joins the controlpointdata's primary elevation IF it exists (LEFT join)
            # WHERE the fieldworkshots are from the current fieldwork, and the code is a control point code CP or MON.
            sql = f"""
            SELECT fws.id, frs.id, (cpc.east - fws.easting) as diff_east, (cpc.north - fws.northing) as diff_north, (cpe.elev - fws.elevation) as diff_elev
                FROM "public"."sites_fieldworkshot" as fws
                INNER JOIN "public"."sites_fieldrunshot" as frs
                    ON fws.matching_fieldrun_shot_id = frs.id
                INNER JOIN "public"."sites_controlpointdata" as cpd
                    ON frs.id = cpd.fieldrun_shot_id
                INNER JOIN "public"."sites_controlpointcoordinate" as cpc
                    ON cpd.primary_coord_id = cpc.id
                LEFT JOIN "public"."sites_controlpointelevation" as cpe
                    ON cpd.primary_elevation_id = cpe.id
                WHERE
                    -- from this fieldwork set
                    fws.fieldwork_id = '{self.fieldwork.attribute('id')}' AND
                    -- fieldworkshot is a control
                    fws.code in ({cp_code_clause})
            """  # noqa: S608

            if query.exec(sql):
                # Fetch the results
                while query.next():
                    fieldworkshot_id = query.value(0)
                    fieldrunshot_id = query.value(1)
                    fieldworkshot = next(self.layers.fieldworkshot_layer.getFeatures(f"\"id\"='{fieldworkshot_id}'"))
                    fieldrunshot = next(self.layers.fieldrunshot_layer.getFeatures(f"\"id\"='{fieldrunshot_id}'"))
                    diff_east: float = query.value(2)
                    diff_north: float = query.value(3)
                    diff_elev: float | None = query.value(4)
                    QgsMessageLog.logMessage(
                        f"{fieldworkshot_id}/{fieldrunshot_id}/{diff_east=}/{diff_north=}/{diff_elev=}",
                    )

                    # add match / shift to dialog
                    dialog.add_shift_row(
                        fieldworkshot,
                        fieldrunshot,
                        (diff_east, diff_north, diff_elev),
                    )
            else:
                QgsMessageLog.logMessage(
                    f"Failed: {db.lastError().text()}",
                )
        # done adding matches / shifts, tell dialog to add the average shift row
        dialog.add_avg_row()
        # show and wait for dialog
        dialog.exec_()

        # apply shift
        result = dialog.get_result()

        QgsMessageLog.logMessage(
            f"{result=}.",
        )
        self.apply_shift(result)

    def _apply_shift_to_fieldwork(self, result: CoordinateShiftDialogResult, fieldwork: QgsFeature) -> None:
        """Apply shift from dialog to fieldwork."""
        fields = self.layers.fieldwork_layer.fields()

        shift_type, shift = result

        QgsMessageLog.logMessage(
            f"{fieldwork[fields.indexFromName('shift_type')]=}",
        )
        fieldwork = next(self.layers.fieldwork_layer.getFeatures(f"\"id\"='{fieldwork.attribute("id")}'"))
        fieldwork.setAttribute("shift_type", shift_type)
        if shift:
            fieldwork.setAttribute("easting_shift", shift[0])
            fieldwork.setAttribute("northing_shift", shift[1])
            fieldwork.setAttribute("elevation_shift", shift[2])

        QgsMessageLog.logMessage(
            f"{fieldwork[fields.indexFromName('shift_type')]=}",
        )

        self.layers.fieldwork_layer.updateFeature(fieldwork)
        self.layers.fieldwork_layer.commitChanges()

    def _apply_shift_to_fieldworkshot(self, result: CoordinateShiftDialogResult, fieldworkshot: QgsFeature) -> None:
        """Apply shift from dialog to fieldwork point."""
        fields = self.layers.fieldworkshot_layer.fields()
        easting_idx = fields.indexFromName("easting")
        northing_idx = fields.indexFromName("northing")
        elevation_idx = fields.indexFromName("elevation")

        _, shift = result

        if shift:
            if fieldworkshot[easting_idx]:
                fieldworkshot[easting_idx] += shift[0]
            if fieldworkshot[northing_idx]:
                fieldworkshot[northing_idx] += shift[1]
            if fieldworkshot[elevation_idx]:
                fieldworkshot[elevation_idx] += shift[2]
            self.layers.fieldworkshot_layer.updateFeature(fieldworkshot)

    def apply_shift(self, result: CoordinateShiftDialogResult) -> None:
        """Apply shift from dialog."""
        # apply to fieldwork
        self._apply_shift_to_fieldwork(result, self.fieldwork)

        _, shift = result
        if shift:
            points: list[QgsFeature] = [
                *self.layers.fieldworkshot_layer.getFeatures(
                    f"""
                    "fieldwork_id" = '{self.fieldwork.attribute('id')}'
                    """,
                ),  # type: ignore []
            ]
            # apply to each point in fieldwork
            for point in points:
                self._apply_shift_to_fieldworkshot(result, point)

    def calculate_hpn_shift(self) -> tuple[float, float, float] | None:  # noqa: D102
        SUM_easting = self.fieldwork.attribute("SUM_easting")  # noqa: N806
        SUM_northing = self.fieldwork.attribute("SUM_northing")  # noqa: N806
        SUM_elevation = self.fieldwork.attribute("SUM_elevation")  # noqa: N806
        SUM_geoid_seperation = self.fieldwork.attribute("SUM_geoid_seperation")  # noqa: N806
        REF_easting = self.fieldwork.attribute("REF_easting")  # noqa: N806
        REF_northing = self.fieldwork.attribute("REF_northing")  # noqa: N806
        REF_elevation = self.fieldwork.attribute("REF_elevation")  # noqa: N806
        LOC_grid_easting = self.fieldwork.attribute("LOC_grid_easting")  # noqa: N806
        LOC_grid_northing = self.fieldwork.attribute("LOC_grid_northing")  # noqa: N806
        LOC_grid_elevation = self.fieldwork.attribute("LOC_grid_elevation")  # noqa: N806
        LOC_measured_easting = self.fieldwork.attribute("LOC_measured_easting")  # noqa: N806
        LOC_measured_northing = self.fieldwork.attribute("LOC_measured_northing")  # noqa: N806
        LOC_measured_elevation = self.fieldwork.attribute("LOC_measured_elevation")  # noqa: N806
        QgsMessageLog.logMessage(
            f"{[
                SUM_easting,
                SUM_northing,
                SUM_elevation,
                SUM_geoid_seperation,
                REF_easting,
                REF_northing,
                REF_elevation,
                LOC_grid_easting,
                LOC_grid_northing,
                LOC_grid_elevation,
                LOC_measured_easting,
                LOC_measured_northing,
                LOC_measured_elevation,
            ]=}",
        )
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
