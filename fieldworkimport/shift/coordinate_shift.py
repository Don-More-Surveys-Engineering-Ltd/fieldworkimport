from typing import TYPE_CHECKING, Optional

from qgis.core import QgsMessageLog
from qgis.PyQt.QtSql import QSqlQuery

from fieldworkimport.helpers import layer_database_connection
from fieldworkimport.ui.coordinate_shift_dialog import CoordinateShiftDialog

if TYPE_CHECKING:
    from fieldworkimport.process import FieldworkImportLayers


class CoordinateShiftStage:
    layers: "FieldworkImportLayers"
    fw_matching_fieldrun_shot_id_index: int
    fieldwork_id: str
    fieldrun_id: Optional[int]  # noqa: FA100
    control_point_codes: list[str]

    def __init__(  # noqa: D107
        self,
        layers: "FieldworkImportLayers",
        fieldwork_id: str,
        fieldrun_id: Optional[int],  # noqa: FA100
        control_point_codes: list[str],
    ) -> None:
        self.layers = layers
        self.fieldwork_id = fieldwork_id
        self.fieldrun_id = fieldrun_id
        self.control_point_codes = control_point_codes

        fw_fields = self.layers.fieldworkshot_layer.fields()
        self.fw_matching_fieldrun_shot_id_index = fw_fields.indexFromName("matching_fieldrun_shot_id")

    def run(self):
        QgsMessageLog.logMessage(
            "CoordinateShiftStage.run started.",
        )
        cp_code_clause = ", ".join([f"'{code}'" for code in self.control_point_codes])

        dialog = CoordinateShiftDialog()

        with layer_database_connection(self.layers.fieldrunshot_layer) as db:
            query = QSqlQuery(db)
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
                    fws.fieldwork_id = '{self.fieldwork_id}' AND
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
                    diff_elev: Optional[float] = query.value(4)
                    QgsMessageLog.logMessage(
                        f"{fieldworkshot_id}/{fieldrunshot_id}/{diff_east=}/{diff_north=}/{diff_elev=}",
                    )
                    dialog.add_shift_row(
                        fieldworkshot,
                        fieldrunshot,
                        (diff_east, diff_north, diff_elev),
                    )
            else:
                QgsMessageLog.logMessage(
                    f"Failed: {db.lastError().text()}",
                )

        dialog.exec_()
