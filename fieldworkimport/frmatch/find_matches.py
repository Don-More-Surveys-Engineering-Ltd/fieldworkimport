from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from qgis.core import (
    Qgis,
    QgsFeature,
    QgsFeatureRequest,
    QgsMessageLog,
    QgsVectorLayerUtils,
)
from qgis.PyQt.QtSql import QSqlQuery

from fieldworkimport.helpers import layer_database_connection
from fieldworkimport.ui.match_control_item import MatchControlItem
from fieldworkimport.ui.match_to_controls_dialog import MatchToControlsDialog

if TYPE_CHECKING:
    from fieldworkimport.process import FieldworkImportLayers


class FieldRunMatchStage:
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
        """Start finding matches."""
        QgsMessageLog.logMessage(
            "FieldRunMatchStage.run started.",
        )
        self.match_controls()
        if self.fieldrun_id:
            self.match_on_name()

    def create_fieldrun_control_shot(self, name: str, based_on_fieldwork_shot: QgsFeature) -> QgsFeature:
        new_control = QgsVectorLayerUtils.createFeature(self.layers.fieldrunshot_layer)
        fields = self.layers.fieldrunshot_layer.fields()
        new_control[fields.indexFromName("id")] = str(uuid4())
        new_control[fields.indexFromName("name")] = name
        new_control[fields.indexFromName("type")] = "Control"
        new_control[fields.indexFromName("field_run_id")] = self.fieldrun_id
        new_control[fields.indexFromName("description")] = f"[Genrated to match shot {based_on_fieldwork_shot.attribute('name')}]"
        new_control.setGeometry(based_on_fieldwork_shot.geometry())

        self.layers.fieldrunshot_layer.addFeature(new_control)
        return new_control

    def assign_fr_shot(self, fw_shot: QgsFeature, fr_shot_id: str) -> None:
        """Assign fieldrun show as match for fieldwork shot, and that shot's ancestors."""
        fw_shot[self.fw_matching_fieldrun_shot_id_index] = fr_shot_id
        self.layers.fieldworkshot_layer.updateFeature(fw_shot)

        # recurse up ancestor tree.
        parent_point_id = fw_shot.attribute("parent_point_id")
        if parent_point_id:
            parent_point = self.layers.fieldworkshot_layer.getFeature(parent_point_id)
            self.assign_fr_shot(parent_point, fr_shot_id)

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
                .setFilterExpression(f"\"fieldrun_id\" = '{self.fieldrun_id}'"),
            ),  # type: ignore []
        ]
        fr_name_feature_tuples = [(f.attribute("name"), f) for f in fr_points]
        fr_name_feature_map = {f[0].strip(): f[1] for f in fr_name_feature_tuples if f[0]}

        for fw_shot in fw_points:
            fw_shot_name = fw_shot.attribute("name")
            if fw_shot_name in fr_name_feature_map:
                fr_shot = fr_name_feature_map[fw_shot_name]
                fr_shot_id = fr_shot.attribute("id")

                self.assign_fr_shot(fw_shot, fr_shot_id)

    def match_controls(self) -> None:
        """List all controls that need matches, with neasby (5m) suggestions for each point.

        User can either choose a suggestion, choose an "other" point, or provide a name for a new point.
        """
        dialog = MatchToControlsDialog()

        allow_create_new = self.fieldrun_id is not None

        # find control-type fieldwork shots that need fieldrunshot matches.
        cp_code_clause = " OR ".join([f"\"code\" like '{code}'" for code in self.control_point_codes])
        # Points with a cp code (mon or cp), are parent points, and are of the current fieldwork.
        fw_controls_needing_matches: list[QgsFeature] = [*self.layers.fieldworkshot_layer.getFeatures(
            f'"fieldwork_id" = \'{self.fieldwork_id}\' and "parent_point_id" is null and ({cp_code_clause})',
        )]  # type: ignore []

        with layer_database_connection(self.layers.fieldrunshot_layer) as db:
            # add widget for each fieldworkshot control
            for fw_shot in fw_controls_needing_matches:
                # find nearby suggestions
                point = fw_shot.geometry().asPoint()
                distance_threshold = 5
                # Use direct SQL query to get ids rather than qgis expression because it is much faster
                # Construct the SQL expression using ST_DWithin
                query = QSqlQuery(db)
                sql = f"""
                SELECT id
                    FROM "public"."sites_fieldrunshot"
                    WHERE
                        -- within 5 meters of the fieldworkshot geometry
                        -- convert geometry to ::geography so that the ST_DWithin is in meters, not degrees
                        ST_DWithin(geom::geography, ST_GeomFromText('{point.asWkt()}', 4326)::geography, {distance_threshold})
                        -- fieldrunshot is a control
                        AND type like 'Control'
                """  # noqa: S608
                feature_ids = []
                if query.exec(sql):
                    # Fetch the results
                    while query.next():
                        feature_id = query.value(0)  # ID
                        feature_ids.append(feature_id)
                        QgsMessageLog.logMessage(f"query next {feature_id}", level=Qgis.MessageLevel.Critical)
                else:
                    QgsMessageLog.logMessage("No exec", level=Qgis.MessageLevel.Critical)
                    QgsMessageLog.logMessage(f"{db.lastError().text()}", level=Qgis.MessageLevel.Critical)

                # turn list of ids into list of qgis features
                ids_str = ", ".join([f"'{i}'" for i in feature_ids])
                expression = f'"id" in ({ids_str})'
                suggestions = [*self.layers.fieldrunshot_layer.getFeatures(expression)]  # type: ignore []

                # add widget for fieldworkshot matching
                match_control_item = MatchControlItem(self.layers, fw_shot, suggestions, allow_create_new=allow_create_new)
                dialog.scrollAreaContents.layout().addWidget(match_control_item)

        dialog.exec()

        for fieldwork_shot, control_match_result in dialog.results:
            if control_match_result.matched_fieldrunshot:
                self.assign_fr_shot(fieldwork_shot, control_match_result.matched_fieldrunshot.attribute("id"))
            elif control_match_result.new_fieldrunshot_name:
                # create new point to match shot first
                matched_fieldrunshot = self.create_fieldrun_control_shot(name=control_match_result.new_fieldrunshot_name, based_on_fieldwork_shot=fieldwork_shot)
                self.assign_fr_shot(fieldwork_shot, matched_fieldrunshot.attribute("id"))
