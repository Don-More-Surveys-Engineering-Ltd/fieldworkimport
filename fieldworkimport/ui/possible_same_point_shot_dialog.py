
from typing import Optional

from PyQt5.QtWidgets import QDialog, QWidget
from qgis.core import QgsFeature

from fieldworkimport.ui.generated.possible_same_point_shot_ui import Ui_PossibleSamePointShotDialog


class PossibleSamePointShotDialog(QDialog, Ui_PossibleSamePointShotDialog):
    point_1: QgsFeature
    point_2: QgsFeature

    def __init__(
        self,
        point_1: QgsFeature,
        point_2: QgsFeature,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setupUi(self)

        self.point_1 = point_1
        self.point_2 = point_2

        residual_east = self.point_1["easting"] - self.point_2["easting"]
        residual_north = self.point_1["northing"] - self.point_2["northing"]
        residual_elevation = self.point_1["elevation"] - self.point_2["elevation"]

        p1_name = self.point_1["name"]
        p2_name = self.point_2["name"]
        p1_description = f"{self.point_1['description']}"
        p2_description = f"{self.point_2['description']}"

        self.residuals_text.setText(
            self.residuals_text.text()
            .replace("{{residual_east}}", f"{residual_east:.3f}")
            .replace("{{residual_north}}", f"{residual_north:.3f}")
            .replace("{{residual_elevation}}", f"{residual_elevation:.3f}"),
        )

        self.p1_desc_text.setText(
            self.p1_desc_text.text()
            .replace("{{p1_name}}", p1_name)
            .replace("{{p1_description}}", p1_description),
        )
        self.p2_desc_text.setText(
            self.p2_desc_text.text()
            .replace("{{p2_name}}", p2_name)
            .replace("{{p2_description}}", p2_description),
        )

        self.keep_p1_radio.setText(self.keep_p1_radio.text().replace("{{p1_name}}", p1_name))
        self.keep_p2_help_text.setText(
            self.keep_p2_help_text.text()
            .replace("{{p1_name}}", p1_name)
            .replace("{{p2_name}}", p2_name),
        )
        self.keep_p2_radio.setText(self.keep_p2_radio.text().replace("{{p2_name}}", p2_name))
        self.keep_p1_help_text.setText(
            self.keep_p1_help_text.text()
            .replace("{{p1_name}}", p1_name)
            .replace("{{p2_name}}", p2_name),
        )
        self.recalculate_help_text.setText(
            self.recalculate_help_text.text()
            .replace("{{p1_name}}", p1_name)
            .replace("{{p2_name}}", p2_name),
        )
