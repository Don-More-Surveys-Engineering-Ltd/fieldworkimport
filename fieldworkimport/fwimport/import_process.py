
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from qgis.core import QgsFeature, QgsVectorLayer
from qgis.gui import QgisInterface
from qgis.utils import iface as _iface

from fieldworkimport.exceptions import AbortError
from fieldworkimport.fwimport.stage_1_create_fieldwork import create_fieldwork
from fieldworkimport.fwimport.stage_2_validate_points import correct_codes, show_warnings, validate_points
from fieldworkimport.fwimport.stage_3_local_point_merge import local_point_merge
from fieldworkimport.fwimport.stage_4_match_fieldrun import FieldRunMatchStage
from fieldworkimport.fwimport.stage_5_coordinate_shift import CoordinateShiftStage
from fieldworkimport.helpers import get_layers_by_table_name

iface: QgisInterface = _iface  # type: ignore

try:
    import rw5_to_csv
except ImportError:
    import os
    import sys
    this_dir = Path(os.path.realpath(__file__)).parent.parent
    path = this_dir / "wheels" / "rw5_to_csv-0.1.0-py3-none-any.whl"
    sys.path.append(str(path))
    import rw5_to_csv


@dataclass
class FieldworkImportLayers:
    fieldwork_layer: QgsVectorLayer
    fieldworkshot_layer: QgsVectorLayer
    fieldrunshot_layer: QgsVectorLayer
    controlpointdata_layer: QgsVectorLayer
    controlpointcoordinate_layer: QgsVectorLayer
    controlpointelevation_layer: QgsVectorLayer
    coordsystem_layer: QgsVectorLayer
    elevationsystem_layer: QgsVectorLayer


class FieldworkImportProcess:
    geopackage_path: str
    group_name: str
    layers: FieldworkImportLayers
    fieldwork_feature: QgsFeature
    vrms_tolerance: float
    hrms_tolerance: float
    same_point_tolerance: float
    valid_codes: list[str]
    valid_special_chars: list[str]
    parameterized_special_chars: list[str]
    control_point_codes: list[str]
    crdb_path: str
    rw5_path: str
    sum_path: str | None
    ref_path: str | None
    loc_path: str | None
    fieldrun_feature: QgsFeature | None

    def __init__(  # noqa: PLR0913
        self,
        vrms_tolerance: float,
        hrms_tolerance: float,
        same_point_tolerance: float,
        valid_codes: list[str],
        valid_special_chars: list[str],
        parameterized_special_chars: list[str],
        control_point_codes: list[str],
        crdb_path: str,
        rw5_path: str,
        sum_path: str | None,
        ref_path: str | None,
        loc_path: str | None,
        fieldrun_feature: QgsFeature | None,
    ) -> None:
        self.vrms_tolerance = vrms_tolerance
        self.hrms_tolerance = hrms_tolerance
        self.same_point_tolerance = same_point_tolerance
        self.valid_codes = valid_codes
        self.valid_special_chars = valid_special_chars
        self.parameterized_special_chars = parameterized_special_chars
        self.control_point_codes = control_point_codes
        self.crdb_path = crdb_path
        self.rw5_path = rw5_path
        self.sum_path = sum_path
        self.ref_path = ref_path
        self.loc_path = loc_path
        self.fieldrun_feature = fieldrun_feature

        rw5_prelude = rw5_to_csv.prelude(rw5_path=Path(rw5_path))

        self.geopackage_path = str(Path(r"C:\Users\jlong\Documents\gpkg") / f"{rw5_prelude['JobName']}.gpkg")  # TODO
        self.group_name = f"{rw5_prelude['JobName']} Fieldwork Import"

        fieldwork_layer = self.create_working_layer("sites_fieldwork")
        fieldworkshot_layer = self.create_working_layer("sites_fieldworkshot")
        fieldrunshot_layer = self.create_working_layer("sites_fieldrunshot")
        controlpointdata_layer = self.create_working_layer("sites_controlpointdata")
        controlpointelevation_layer = self.create_working_layer("sites_controlpointelevation")
        controlpointcoordinate_layer = self.create_working_layer("sites_controlpointcoordinate")
        coordsystem_layer = self.create_working_layer("sites_coordsystem")
        eleavtionsystem_layer = self.create_working_layer("sites_elevationsystem")

        self.layers = FieldworkImportLayers(
            fieldwork_layer=fieldwork_layer,
            fieldworkshot_layer=fieldworkshot_layer,
            fieldrunshot_layer=fieldrunshot_layer,
            controlpointdata_layer=controlpointdata_layer,
            controlpointcoordinate_layer=controlpointcoordinate_layer,
            controlpointelevation_layer=controlpointelevation_layer,
            coordsystem_layer=coordsystem_layer,
            elevationsystem_layer=eleavtionsystem_layer,
        )

    def rollback(self):
        self.layers.controlpointcoordinate_layer.rollBack()
        self.layers.controlpointelevation_layer.rollBack()
        self.layers.controlpointdata_layer.rollBack()
        self.layers.fieldrunshot_layer.rollBack()
        self.layers.fieldworkshot_layer.rollBack()
        self.layers.fieldwork_layer.rollBack()

    def run(self):
        try:
            self.layers.fieldwork_layer.startEditing()
            self.layers.fieldworkshot_layer.startEditing()
            self.layers.fieldrunshot_layer.startEditing()

            self.fieldwork_feature = create_fieldwork(
                self.layers.fieldwork_layer,
                self.layers.fieldworkshot_layer,
                self.crdb_path,
                self.rw5_path,
                self.sum_path,
                self.ref_path,
                self.loc_path,
                self.fieldrun_feature,
            )

            fieldwork_id = self.fieldwork_feature.attribute("id")
            fieldrun_id = self.fieldrun_feature.attribute("id") if self.fieldrun_feature else None

            validate_points(
                self.layers.fieldworkshot_layer,
                fieldwork_id=fieldwork_id,
                hrms_tolerance=self.hrms_tolerance,
                vrms_tolerance=self.vrms_tolerance,
                valid_codes=self.valid_codes,
                valid_special_chars=self.valid_special_chars,
                parameterized_special_chars=self.parameterized_special_chars,
            )

            correct_codes(
                self.layers.fieldworkshot_layer,
                fieldwork_id=fieldwork_id,
                valid_codes=self.valid_codes,
                valid_special_chars=self.valid_special_chars,
                parameterized_special_chars=self.parameterized_special_chars,
            )

            show_warnings(
                self.layers.fieldworkshot_layer,
                fieldwork_id=fieldwork_id,
                hrms_tolerance=self.hrms_tolerance,
                vrms_tolerance=self.vrms_tolerance,
            )

            local_point_merge(
                self.layers.fieldworkshot_layer,
                fieldwork_id=fieldwork_id,
                same_point_tolerance=self.same_point_tolerance,
                control_point_codes=self.control_point_codes,
            )

            mm = FieldRunMatchStage(
                layers=self.layers,
                fieldwork_id=fieldwork_id,
                fieldrun_id=fieldrun_id,
                control_point_codes=self.control_point_codes,
            )
            mm.run()

            cs = CoordinateShiftStage(
                layers=self.layers,
                fieldwork=self.fieldwork_feature,
                fieldrun_id=fieldrun_id,
                control_point_codes=self.control_point_codes,
            )
            cs.run()

            self.mark_shots_as_processed()

        except AbortError:
            self.rollback()
            raise

    def mark_shots_as_processed(self):
        """Set is_processed to true on all points to show processing has completed."""
        fields = self.layers.fieldworkshot_layer.fields()
        is_processed_idx = fields.indexFromName("is_processed")
        points: list[QgsFeature] = [*self.layers.fieldworkshot_layer.getFeatures(
            f"fieldwork_id = '{self.fieldwork_feature.attribute('id')}'",
        )]  # type: ignore []
        for point in points:
            point[is_processed_idx] = True
            self.layers.fieldworkshot_layer.updateFeature(point)

    def create_working_layer(self, table_name: str):
        # get layer know will be present
        return get_layers_by_table_name("public", table_name, raise_exception=True, no_filter=True)[0]
