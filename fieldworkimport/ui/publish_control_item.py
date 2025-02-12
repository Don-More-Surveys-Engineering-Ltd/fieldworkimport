
from typing import Optional

from PyQt5.QtWidgets import QWidget
from qgis.core import NULL, QgsExpression, QgsFeature, QgsFeatureRequest, QgsVectorLayer

from fieldworkimport.helpers import get_layers_by_table_name
from fieldworkimport.ui.generated.publish_control_item_ui import Ui_PublishControlItem


class PublishControlItem(QWidget, Ui_PublishControlItem):
    fieldwork_shot: QgsFeature
    fieldrun_shot: QgsFeature
    suggested_fieldrun_shots: list[QgsFeature]

    def __init__(
        self,
        fieldwork_shot: QgsFeature,
        fieldrunshot_layer: QgsVectorLayer,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setupUi(self)

        # setup feature picker with layer
        self.fieldrunshot_layer = fieldrunshot_layer
        self.coordsystem_layer = get_layers_by_table_name("public", "sites_coordsystem", no_filter=True, raise_exception=True)[0]
        self.elevationsystem_layer = get_layers_by_table_name("public", "sites_elevationsystem", no_filter=True, raise_exception=True)[0]

        self.fieldwork_shot = fieldwork_shot
        self.fieldrun_shot = next(self.fieldrunshot_layer.getFeatures(
            QgsFeatureRequest(QgsExpression(f"matched_fieldwork_shot_id = '{self.fieldwork_shot['id']}'"))
            .setLimit(1),
        ))  # type: ignore

        self.coordinate_system_input.setLayer(self.coordsystem_layer)
        self.coordinate_system_input.setFilterExpression('"active" = true')
        self.elevation_system_input.setLayer(self.elevationsystem_layer)
        self.elevation_system_input.setFilterExpression('"active" = true')

        # set groupBox title
        fieldrun_shot_name = self.fieldrun_shot["name"]
        fieldrun_shot_description = self.fieldrun_shot["description"]
        self.groupBox.setTitle(fieldrun_shot_name)
        self.control_name_input.setText(fieldrun_shot_name)
        self.control_description_input.setPlainText(fieldrun_shot_description)

    def is_valid(self):
        if self.dont_publish_checkbox.isChecked():
            return True

        name = self.control_name_input.text()
        description = self.control_description_input.toPlainText()
        coord_system = self.coordinate_system_input.feature()
        elevation_system = self.coordinate_system_input.feature()

        return not (not name or
                    not description or
                    not coord_system or
                    not elevation_system or
                    NULL in {coord_system, elevation_system}
        )
