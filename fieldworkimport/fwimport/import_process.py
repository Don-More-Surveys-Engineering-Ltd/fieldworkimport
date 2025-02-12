
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from qgis.core import QgsFeature, QgsVectorLayer
from qgis.gui import QgisInterface
from qgis.utils import iface as _iface

from fieldworkimport.exceptions import AbortError
from fieldworkimport.fwimport.stage_1_create_fieldwork import create_fieldwork
from fieldworkimport.fwimport.stage_2_validate_points import correct_codes, show_warnings, validate_points
from fieldworkimport.fwimport.stage_3_local_point_merge import local_point_merge
from fieldworkimport.fwimport.stage_4_match_fieldrun import FieldRunMatchStage
from fieldworkimport.fwimport.stage_5_coordinate_shift import CoordinateShiftStage
from fieldworkimport.helpers import assert_true, get_layers_by_table_name, timed

iface: QgisInterface = _iface  # type: ignore

if TYPE_CHECKING:
    from fieldworkimport.plugin import PluginInput

try:
    import rw5_to_csv
except ImportError:
    import os
    import sys
    this_dir = Path(os.path.realpath(__file__)).parent.parent
    path = this_dir / "wheels" / "rw5_to_csv-0.1.0-py3-none-any.whl"
    sys.path.append(str(path))


@dataclass
class FieldworkImportLayers:
    fieldwork_layer: QgsVectorLayer
    fieldworkshot_layer: QgsVectorLayer
    fieldrunshot_layer: QgsVectorLayer
    coordsystem_layer: QgsVectorLayer
    elevationsystem_layer: QgsVectorLayer


class FieldworkImportProcess:
    layers: FieldworkImportLayers
    plugin_input: PluginInput

    def __init__(
        self,
        plugin_input: PluginInput,
    ) -> None:
        self.plugin_input = plugin_input

        fieldwork_layer = get_layers_by_table_name("public", "sites_fieldwork", raise_exception=True, no_filter=True)[0]
        fieldworkshot_layer = get_layers_by_table_name("public", "sites_fieldworkshot", raise_exception=True, no_filter=True, require_geom=True)[0]
        fieldrunshot_layer = get_layers_by_table_name("public", "sites_fieldrunshot", raise_exception=True, no_filter=True, require_geom=True)[0]
        coordsystem_layer = get_layers_by_table_name("public", "sites_coordsystem", raise_exception=True, no_filter=True)[0]
        eleavtionsystem_layer = get_layers_by_table_name("public", "sites_elevationsystem", raise_exception=True, no_filter=True)[0]

        self.layers = FieldworkImportLayers(
            fieldwork_layer=fieldwork_layer,
            fieldworkshot_layer=fieldworkshot_layer,
            fieldrunshot_layer=fieldrunshot_layer,
            coordsystem_layer=coordsystem_layer,
            elevationsystem_layer=eleavtionsystem_layer,
        )

    def rollback(self):
        self.layers.fieldrunshot_layer.rollBack()
        self.layers.fieldworkshot_layer.rollBack()
        self.layers.fieldwork_layer.rollBack()

    def run(self):
        try:
            self.layers.fieldwork_layer.startEditing()
            self.layers.fieldworkshot_layer.startEditing()
            self.layers.fieldrunshot_layer.startEditing()

            with timed("create_fieldwork"):
                self.fieldwork_feature = create_fieldwork(
                    self.layers,
                    self.plugin_input,
                )

            fieldwork_id = self.fieldwork_feature["id"]
            fieldrun_id = self.plugin_input.fieldrun_feature["id"] if self.plugin_input.fieldrun_feature else None

            with timed("validate_points"):
                validate_points(
                    self.layers.fieldworkshot_layer,
                    fieldwork_id=fieldwork_id,
                )

            with timed("correct_codes"):
                correct_codes(
                    self.layers.fieldworkshot_layer,
                    fieldwork_id=fieldwork_id,
                )

            with timed("show_warnings"):
                show_warnings(
                    self.layers.fieldworkshot_layer,
                    fieldwork_id=fieldwork_id,
                )

            with timed("local_point_merge"):
                local_point_merge(
                    self.layers.fieldworkshot_layer,
                    fieldwork_id=fieldwork_id,
                )

            with timed("FieldRunMatchStage"):
                mm = FieldRunMatchStage(
                    layers=self.layers,
                    fieldwork_id=fieldwork_id,
                    fieldrun_id=fieldrun_id,
                    plugin_input=self.plugin_input,
                )
                mm.run()

            with timed("CoordinateShiftStage"):
                cs = CoordinateShiftStage(
                    layers=self.layers,
                    fieldwork=self.fieldwork_feature,
                    fieldrun_id=fieldrun_id,
                    plugin_input=self.plugin_input,
                )
                cs.run()

            with timed("mark_shots_as_processed"):
                self.mark_shots_as_processed()

        except AbortError:
            self.rollback()
            raise

    def mark_shots_as_processed(self):
        """Set is_processed to true on all points to show processing has completed."""
        fields = self.layers.fieldworkshot_layer.fields()
        is_processed_idx = fields.indexFromName("is_processed")
        points: list[QgsFeature] = [*self.layers.fieldworkshot_layer.getFeatures(
            f"fieldwork_id = '{self.fieldwork_feature['id']}'",
        )]  # type: ignore []
        for point in points:
            point[is_processed_idx] = True
            assert_true(self.layers.fieldworkshot_layer.updateFeature(point), "Failed to mark fieldwork shot as processed.")
