
import sqlite3
from pathlib import Path
from typing import Optional
from uuid import uuid4

import pytz
from PyQt5.QtCore import QDateTime
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsPoint,
    QgsProject,
    QgsVectorLayerUtils,
)
from qgis.gui import QgisInterface
from qgis.utils import iface as _iface

from fieldworkimport.fieldwork.helpers import ReturnCode, get_layers_by_table_name
from fieldworkimport.fieldwork.parse_loc_file import parse_loc_file
from fieldworkimport.fieldwork.parse_ref_file import parse_ref_file
from fieldworkimport.fieldwork.parse_sum_file import parse_sum_file

try:
    import rw5_to_csv
except ImportError:
    import os
    import sys
    this_dir = Path(os.path.realpath(__file__)).parent.parent
    path = this_dir / "wheels" / "rw5_to_csv-0.1.0-py3-none-any.whl"
    sys.path.append(str(path))
    import rw5_to_csv

iface: QgisInterface = _iface


def create_fieldwork(
    crdb_path: str,
    rw5_path: str,
    sum_path: Optional[str],
    ref_path: Optional[str],
    loc_path: Optional[str],  # noqa: FA100
    fieldrun_feature: Optional[QgsFeature],
) -> tuple[ReturnCode, QgsFeature]:
    timezone = pytz.timezone("America/Halifax")
    fieldwork_layer = get_layers_by_table_name("public", "sites_fieldwork", no_filter=True, raise_exception=True)[0]
    fieldwork_shot_layer = get_layers_by_table_name("public", "sites_fieldworkshot", no_filter=True, raise_exception=True)[0]

    loc_data = None
    sum_data = None
    ref_data = None
    field_run_id = None
    if sum_path:
        sum_data = parse_sum_file(Path(sum_path))
    if loc_path:
        loc_data = parse_loc_file(Path(loc_path), geoid_seperation=sum_data["geoid_seperation"] if sum_data else None)
    if ref_path:
        ref_data = parse_ref_file(Path(ref_path))
    if fieldrun_feature:
        field_run_id = fieldrun_feature.attribute("id")

    rw5_rows = rw5_to_csv.convert(rw5_path=Path(rw5_path), output_path=None, tzinfo=timezone)
    rw5_prelude = rw5_to_csv.prelude(rw5_path=Path(rw5_path))

    crdb_connection = sqlite3.connect(crdb_path)
    crdb_connection.row_factory = sqlite3.Row
    cursor = crdb_connection.cursor()

    fieldwork_layer_fields = fieldwork_layer.fields()
    fieldwork_layer_id_index = fieldwork_layer_fields.indexFromName("id")
    fieldwork_layer_field_run_id_index = fieldwork_layer_fields.indexFromName("field_run_id")
    fieldwork_layer_name_index = fieldwork_layer_fields.indexFromName("name")
    fieldwork_layer_note_index = fieldwork_layer_fields.indexFromName("note")
    LOC_measured_easting_index = fieldwork_layer_fields.indexFromName("LOC_measured_easting")  # noqa: N806
    LOC_measured_northing_index = fieldwork_layer_fields.indexFromName("LOC_measured_northing")  # noqa: N806
    LOC_measured_elevation_index = fieldwork_layer_fields.indexFromName("LOC_measured_elevation")  # noqa: N806
    LOC_grid_easting_index = fieldwork_layer_fields.indexFromName("LOC_grid_easting")  # noqa: N806
    LOC_grid_northing_index = fieldwork_layer_fields.indexFromName("LOC_grid_northing")  # noqa: N806
    LOC_grid_elevation_index = fieldwork_layer_fields.indexFromName("LOC_grid_elevation")  # noqa: N806
    LOC_description_index = fieldwork_layer_fields.indexFromName("LOC_description")  # noqa: N806
    REF_easting_index = fieldwork_layer_fields.indexFromName("REF_easting")  # noqa: N806
    REF_northing_index = fieldwork_layer_fields.indexFromName("REF_northing")  # noqa: N806
    REF_elevation_index = fieldwork_layer_fields.indexFromName("REF_elevation")  # noqa: N806
    SUM_easting_index = fieldwork_layer_fields.indexFromName("SUM_easting")  # noqa: N806
    SUM_northing_index = fieldwork_layer_fields.indexFromName("SUM_northing")  # noqa: N806
    SUM_elevation_index = fieldwork_layer_fields.indexFromName("SUM_elevation")  # noqa: N806
    SUM_orthometric_system_index = fieldwork_layer_fields.indexFromName("SUM_orthometric_system")  # noqa: N806
    SUM_orthometric_model_index = fieldwork_layer_fields.indexFromName("SUM_orthometric_model")  # noqa: N806
    SUM_geoid_seperation_index = fieldwork_layer_fields.indexFromName("SUM_geoid_seperation")  # noqa: N806
    equipment_string_index = fieldwork_layer_fields.indexFromName("equipment_string")
    fieldwork_id = str(uuid4())

    fieldwork_layer.startEditing()
    new_fieldwork = QgsVectorLayerUtils.createFeature(fieldwork_layer)
    new_fieldwork[fieldwork_layer_field_run_id_index] = field_run_id
    new_fieldwork[fieldwork_layer_id_index] = fieldwork_id
    new_fieldwork[fieldwork_layer_name_index] = rw5_prelude["JobName"]
    new_fieldwork[fieldwork_layer_note_index] = ""
    new_fieldwork[LOC_measured_easting_index] = loc_data["measured_point"][0] if loc_data else None
    new_fieldwork[LOC_measured_northing_index] = loc_data["measured_point"][1] if loc_data else None
    new_fieldwork[LOC_measured_elevation_index] = loc_data["measured_point"][2] if loc_data else None
    new_fieldwork[LOC_grid_easting_index] = loc_data["grid_point"][0] if loc_data and loc_data["grid_point"] is not None else None  # noqa: E501
    new_fieldwork[LOC_grid_northing_index] = loc_data["grid_point"][1] if loc_data and loc_data["grid_point"] is not None else None  # noqa: E501
    new_fieldwork[LOC_grid_elevation_index] = loc_data["grid_point"][2] if loc_data and loc_data["grid_point"] is not None else None  # noqa: E501
    new_fieldwork[LOC_description_index] = loc_data["description"] if loc_data else None
    new_fieldwork[REF_easting_index] = ref_data[0] if ref_data else None
    new_fieldwork[REF_northing_index] = ref_data[1] if ref_data else None
    new_fieldwork[REF_elevation_index] = ref_data[2] if ref_data else None
    new_fieldwork[SUM_easting_index] = sum_data["point"][0] if sum_data else None
    new_fieldwork[SUM_northing_index] = sum_data["point"][1] if sum_data else None
    new_fieldwork[SUM_elevation_index] = sum_data["point"][2] if sum_data else None
    new_fieldwork[SUM_geoid_seperation_index] = sum_data["geoid_seperation"] if sum_data else None
    new_fieldwork[SUM_orthometric_model_index] = sum_data["orthometric_model"] if sum_data else None
    new_fieldwork[SUM_orthometric_system_index] = sum_data["orthometric_system"] if sum_data else None
    new_fieldwork[equipment_string_index] = rw5_prelude["Equipment"]

    fieldwork_layer.addFeature(new_fieldwork)

    fieldworkshot_layer_fields = fieldwork_shot_layer.fields()
    fieldworkshot_layer_id_index = fieldworkshot_layer_fields.indexFromName("id")
    fieldworkshot_layer_fieldwork_id_index = fieldworkshot_layer_fields.indexFromName("fieldwork_id")
    fieldworkshot_layer_name_index = fieldworkshot_layer_fields.indexFromName("name")
    fieldworkshot_layer_datetime_index = fieldworkshot_layer_fields.indexFromName("datetime")
    fieldworkshot_layer_description_index = fieldworkshot_layer_fields.indexFromName("description")
    fieldworkshot_layer_code_index = fieldworkshot_layer_fields.indexFromName("code")
    fieldworkshot_layer_original_code_index = fieldworkshot_layer_fields.indexFromName("original_code")
    northing_index = fieldworkshot_layer_fields.indexFromName("northing")
    easting_index = fieldworkshot_layer_fields.indexFromName("easting")
    elevation_index = fieldworkshot_layer_fields.indexFromName("elevation")
    number_of_satellites_index = fieldworkshot_layer_fields.indexFromName("number_of_satellites")
    age_of_corrections_index = fieldworkshot_layer_fields.indexFromName("age_of_corrections")
    status_index = fieldworkshot_layer_fields.indexFromName("status")
    HRMS_index = fieldworkshot_layer_fields.indexFromName("HRMS")  # noqa: N806
    VRMS_index = fieldworkshot_layer_fields.indexFromName("VRMS")  # noqa: N806
    PDOP_index = fieldworkshot_layer_fields.indexFromName("PDOP")  # noqa: N806
    HDOP_index = fieldworkshot_layer_fields.indexFromName("HDOP")  # noqa: N806
    VDOP_index = fieldworkshot_layer_fields.indexFromName("VDOP")  # noqa: N806
    TDOP_index = fieldworkshot_layer_fields.indexFromName("TDOP")  # noqa: N806
    GDOP_index = fieldworkshot_layer_fields.indexFromName("GDOP")  # noqa: N806
    rod_height_index = fieldworkshot_layer_fields.indexFromName("rod_height")
    instrument_height_index = fieldworkshot_layer_fields.indexFromName("instrument_height")
    instrument_type_index = fieldworkshot_layer_fields.indexFromName("instrument_type")

    fieldwork_shot_layer.startEditing()

    for rw5_row in rw5_rows:
        crdb_query = cursor.execute("SELECT * FROM Coordinates WHERE P like ?", (rw5_row["PointID"].strip(),))
        crdb_row: sqlite3.Row = crdb_query.fetchone()

        # skip if no crdbrow
        if not crdb_row:
            continue

        # code is everything before the / in the description
        code = crdb_row["D"].split("/")[0]

        srcCrs = QgsCoordinateReferenceSystem(2953)
        dstCrs = QgsCoordinateReferenceSystem(4617)
        transform = QgsCoordinateTransform(srcCrs, dstCrs, QgsProject.instance())

        geom = QgsPoint(x=crdb_row["E"], y=crdb_row["N"])
        geom.transform(transform)

        new_fieldwork_shot = QgsVectorLayerUtils.createFeature(fieldwork_shot_layer)
        new_fieldwork_shot[fieldworkshot_layer_id_index] = str(uuid4())
        new_fieldwork_shot[fieldworkshot_layer_fieldwork_id_index] = fieldwork_id
        if rw5_row["DateTime"]:
            new_fieldwork_shot[fieldworkshot_layer_datetime_index] = QDateTime(rw5_row["DateTime"])
        new_fieldwork_shot[fieldworkshot_layer_name_index] = crdb_row["P"]
        new_fieldwork_shot[fieldworkshot_layer_description_index] = crdb_row["D"]
        new_fieldwork_shot[fieldworkshot_layer_code_index] = code
        new_fieldwork_shot[fieldworkshot_layer_original_code_index] = code
        new_fieldwork_shot[northing_index] = crdb_row["N"]
        new_fieldwork_shot[easting_index] = crdb_row["E"]
        new_fieldwork_shot[elevation_index] = crdb_row["Z"]
        new_fieldwork_shot[number_of_satellites_index] = rw5_row["NumSatellites"]
        new_fieldwork_shot[age_of_corrections_index] = rw5_row["Age"]
        new_fieldwork_shot[status_index] = rw5_row["Status"]
        new_fieldwork_shot[HRMS_index] = rw5_row["HRMS"]
        new_fieldwork_shot[VRMS_index] = rw5_row["VRMS"]
        new_fieldwork_shot[PDOP_index] = rw5_row["PDOP"]
        new_fieldwork_shot[HDOP_index] = rw5_row["HDOP"]
        new_fieldwork_shot[VDOP_index] = rw5_row["VDOP"]
        new_fieldwork_shot[TDOP_index] = rw5_row["TDOP"]
        new_fieldwork_shot[GDOP_index] = rw5_row["GDOP"]
        new_fieldwork_shot[rod_height_index] = rw5_row["RodHeight"]
        new_fieldwork_shot[instrument_height_index] = rw5_row["InstrumentHeight"]
        new_fieldwork_shot[instrument_type_index] = rw5_row["InstrumentType"]
        new_fieldwork_shot.setGeometry(geom)
        fieldwork_shot_layer.addFeature(new_fieldwork_shot)

    # zoom layer to new fieldwork points
    iface.setActiveLayer(fieldwork_shot_layer)
    fieldwork_shot_layer.selectByExpression(f'"fieldwork_id" = \'{fieldwork_id}\'')
    bbox = fieldwork_shot_layer.boundingBoxOfSelected()
    map_canvas = iface.mapCanvas()
    # map_canvas.setExtent(bbox)
    # map_canvas.refresh()
    map_canvas.zoomToSelected(fieldwork_shot_layer)

    return (ReturnCode.CONTINUE, new_fieldwork)
