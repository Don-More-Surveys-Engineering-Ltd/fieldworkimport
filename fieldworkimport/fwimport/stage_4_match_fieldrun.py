from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureRequest,
    QgsGeometry,
    QgsMessageLog,
    QgsProject,
    QgsSettings,
    QgsVectorLayerUtils,
)

from fieldworkimport.helpers import assert_true, nullish, progress_dialog, settings_key, timed
from fieldworkimport.ui.match_control_item import MatchControlItem
from fieldworkimport.ui.match_to_controls_dialog import MatchToControlsDialog

if TYPE_CHECKING:
    from fieldworkimport.fwimport.import_process import FieldworkImportLayers
    from fieldworkimport.plugin import PluginInput


class FieldRunMatchStage:
    layers: "FieldworkImportLayers"
    fieldwork_id: str
    fieldrun_id: Optional[int]  # noqa: FA100
    plugin_input: "PluginInput"

    def __init__(  # noqa: D107
        self,
        layers: "FieldworkImportLayers",
        fieldwork_id: str,
        fieldrun_id: Optional[int],  # noqa: FA100
        plugin_input: "PluginInput",
    ) -> None:
        self.layers = layers
        self.fieldwork_id = fieldwork_id
        self.fieldrun_id = fieldrun_id
        self.plugin_input = plugin_input

        fw_fields = self.layers.fieldworkshot_layer.fields()

    def run(self):
        """Start finding matches."""
        QgsMessageLog.logMessage(
            "FieldRunMatchStage.run started.",
        )
        if self.fieldrun_id:
            with timed("match_on_name"):
                self.match_on_name()
        with timed("match_controls"):
            self.match_controls()

    def create_fieldrun_control_shot(self, name: str, based_on_fieldwork_shot: QgsFeature) -> QgsFeature:
        new_fieldrunshot = QgsVectorLayerUtils.createFeature(self.layers.fieldrunshot_layer)
        fields = self.layers.fieldrunshot_layer.fields()
        new_fieldrunshot[fields.indexFromName("id")] = str(uuid4())
        new_fieldrunshot[fields.indexFromName("name")] = name
        new_fieldrunshot[fields.indexFromName("type")] = "Control"
        new_fieldrunshot[fields.indexFromName("field_run_id")] = self.fieldrun_id
        new_fieldrunshot[fields.indexFromName("description")] = f"{based_on_fieldwork_shot["description"]}\n[Generated to match shot {based_on_fieldwork_shot['name']}]"  # noqa: E501
        geom = QgsGeometry(based_on_fieldwork_shot.geometry())
        new_fieldrunshot.setGeometry(geom)

        assert_true(self.layers.fieldrunshot_layer.addFeature(new_fieldrunshot), "Failed to add new fieldrun shot.")

        return new_fieldrunshot

    def assign_fr_shot(self, fw_shot: QgsFeature, fr_shot: QgsFeature) -> None:
        """Assign fieldrun show as match for fieldwork shot or its ancestor."""
        parent_point_id = fw_shot["parent_point_id"]
        if not nullish(parent_point_id):
            parent_point = next(self.layers.fieldworkshot_layer.getFeatures(f"id = '{parent_point_id}'"))
            # recurse up ancestor tree.
            self.assign_fr_shot(parent_point, fr_shot)
        else:
            fr_shot["matched_fieldwork_shot_id"] = fw_shot["id"]
            assert_true(self.layers.fieldrunshot_layer.updateFeature(fr_shot), "Failed to assign fieldwork shot match to fieldrun shot.")

    def match_on_name(self) -> None:
        """Iterate through fieldwork points, look for match in fieldrun points.

        Cascase matches through fieldwork point's parents and grandparents and ...
        """  # noqa: DOC501
        if not self.fieldrun_id:
            msg = "Fieldrun wasn't passed so a match on name is impossible."
            raise ValueError(msg)

        fw_points: list[QgsFeature] = [
            *self.layers.fieldworkshot_layer.getFeatures(
                QgsFeatureRequest()
                .setFilterExpression(f"\"fieldwork_id\" = '{self.fieldwork_id}'"),
            ),  # type: ignore []
        ]

        fr_points: list[QgsFeature] = [
            *self.layers.fieldrunshot_layer.getFeatures(
                QgsFeatureRequest()
                .setFilterExpression(f'"field_run_id" = {self.fieldrun_id}'),
            ),  # type: ignore []
        ]
        fr_name_feature_tuples = [(f["name"], f) for f in fr_points]
        fr_name_feature_map = {f[0].strip(): f[1] for f in fr_name_feature_tuples if f[0]}

        for fw_shot in fw_points:
            fw_shot_name = fw_shot["name"]
            if fw_shot_name in fr_name_feature_map:
                fr_shot = fr_name_feature_map[fw_shot_name]
                QgsMessageLog.logMessage(f"Matched {fw_shot['name']} to field run shot {fr_shot['name']} based on name.")

                self.assign_fr_shot(fw_shot, fr_shot)

    def match_controls(self) -> None:
        """List all controls that need matches, with neasby (5m) suggestions for each point.

        User can either choose a suggestion, choose an "other" point, or provide a name for a new point.
        """
        s = QgsSettings()
        control_point_codes = s.value(settings_key("control_point_codes")).split(",")
        qgsproj = QgsProject.instance()
        assert qgsproj
        dialog = MatchToControlsDialog()

        allow_create_new = self.fieldrun_id is not None

        # find control-type fieldwork shots that need fieldrunshot matches.
        cp_code_clause = " OR ".join([f"\"code\" like '{code}'" for code in control_point_codes])
        # Points with a cp code (mon or cp), are parent points, and are of the current fieldwork.
        fw_controls_needing_matches: list[QgsFeature] = [*self.layers.fieldworkshot_layer.getFeatures(
            f'"fieldwork_id" = \'{self.fieldwork_id}\' and "parent_point_id" is null and ({cp_code_clause})',
        )]  # type: ignore []

        with progress_dialog("Finding control point matches...") as set_progress:
            n_controls = len(fw_controls_needing_matches)

            src_crs = self.layers.fieldrunshot_layer.crs()
            # add widget for each fieldworkshot control
            for index, fw_shot in enumerate(fw_controls_needing_matches):
                set_progress(index * 100 // n_controls)
                projected_crs = QgsCoordinateReferenceSystem("EPSG:3857")  # Web Mercator so we can use meters
                point = fw_shot.geometry()
                transform_to_m = QgsCoordinateTransform(src_crs, projected_crs, qgsproj.transformContext())
                point.transform(transform_to_m)

                buffer_geom = point.buffer(10, 10)  # 5 meters
                transform_back_to_crs = QgsCoordinateTransform(projected_crs, src_crs, qgsproj.transformContext())
                buffer_geom.transform(transform_back_to_crs)

                suggestions = []

                # find nearby suggestions
                with timed("find suggestions"):
                    suggestions = [*self.layers.fieldrunshot_layer.getFeatures(
                        QgsFeatureRequest().setFilterExpression("type like 'Control'").setFilterRect(buffer_geom.boundingBox()),
                    )]  # type: ignore

                # add widget for fieldworkshot matching
                match_control_item = MatchControlItem(self.layers, fw_shot, suggestions, allow_create_new=allow_create_new)
                dialog.scrollAreaContents.layout().addWidget(match_control_item)

        dialog.exec_()

        for fieldwork_shot, control_match_result in dialog.results:
            if control_match_result.matched_fieldrunshot:
                # match to selected fieldrun shot
                self.assign_fr_shot(fieldwork_shot, control_match_result.matched_fieldrunshot)
            elif control_match_result.new_fieldrunshot_name:
                # create new fieldrun shot control point, and then match to it
                matched_fieldrunshot = self.create_fieldrun_control_shot(name=control_match_result.new_fieldrunshot_name, based_on_fieldwork_shot=fieldwork_shot)
                self.assign_fr_shot(fieldwork_shot, matched_fieldrunshot)
