from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PyQt5.QtWidgets import QRadioButton, QWidget
from qgis.core import QgsFeature, QgsMessageLog

from fieldworkimport.exceptions import AbortError
from fieldworkimport.helpers import nullish
from fieldworkimport.ui.generated.match_control_item import Ui_match_control_item

if TYPE_CHECKING:
    from fieldworkimport.fwimport.import_process import FieldworkImportLayers


@dataclass
class ControlMatchResult:
    matched_fieldrunshot: QgsFeature | None
    # if not None, use feature as match.
    new_fieldrunshot_name: str | None
    # if matched_fieldrunshot is None, create a new fieldrunshot using this name.


def calc_redisuals(fw_shot: QgsFeature, fr_shot: QgsFeature) -> tuple[float, float, float | None] | None:  # noqa: D103
    fr_easting: float = fr_shot["control_easting"]
    fr_northing: float = fr_shot["control_northing"]
    fr_elevation: float = fr_shot["control_elevation"]

    if nullish(fr_easting) or nullish(fr_northing):
        return None

    fw_easting: float = fw_shot["easting"]
    fw_northing: float = fw_shot["northing"]
    fw_elevation: float = fw_shot["elevation"]

    return (
        fr_easting - fw_easting,
        fr_northing - fw_northing,
        (fr_elevation - fw_elevation) if not nullish(fr_elevation) else None,
    )


class MatchControlItem(QWidget, Ui_match_control_item):
    fieldwork_shot: QgsFeature
    suggested_fieldrun_shots: list[QgsFeature]

    def __init__(
        self,
        layers: FieldworkImportLayers,
        fieldwork_shot: QgsFeature,
        suggested_fieldrun_shots: list[QgsFeature],
        allow_create_new: bool,  # noqa: FBT001
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setupUi(self)

        # setup feature picker with layer
        self.layers = layers
        self.other_control_input.setLayer(layers.fieldrunshot_layer)
        self.other_control_input.setFilterExpression("\"type\" = 'Control'")

        self.fieldwork_shot = fieldwork_shot
        self.suggested_fieldrun_shots = suggested_fieldrun_shots
        self.allow_create_new = allow_create_new

        # set groupBox title
        fieldwork_shot_name = self.fieldwork_shot["name"]
        fieldwork_shot_description = self.fieldwork_shot["description"]
        self.groupbox.setTitle(f"{fieldwork_shot_name} - {fieldwork_shot_description}")

        # hide inputs by default until checked
        self.other_control_input.hide()
        self.create_new_input.hide()
        # setup checked listeners
        self.other_control_radio.toggled.connect(self.on_other_control_radio_checked)
        self.create_new_radio.toggled.connect(self.on_create_new_control_checked)

        if not self.allow_create_new:
            self.create_new_radio.hide()

        # add suggested shot radios
        for shot in self.suggested_fieldrun_shots:
            self.add_suggestion_radio(shot)

    def on_other_control_radio_checked(self):
        checked = self.other_control_radio.isChecked()
        if checked:
            self.other_control_input.show()
        else:
            self.other_control_input.hide()

    def on_create_new_control_checked(self):
        checked = self.create_new_radio.isChecked()
        if checked:
            self.create_new_input.show()
        else:
            self.create_new_input.hide()

    def add_suggestion_radio(self, suggestion_fieldrun_shot: QgsFeature):
        radio = QRadioButton()
        suggestion_name = suggestion_fieldrun_shot["name"]
        try:
            residuals = calc_redisuals(self.fieldwork_shot, suggestion_fieldrun_shot)
        except ValueError as e:
            QgsMessageLog.logMessage(str(e))
            return
        if residuals:
            radio.setText(f"{suggestion_name} - ({residuals[0]:.3f}, {residuals[1]:.3f}, {round(residuals[2], 3) if residuals[2] else 'N/A'})")  # noqa: E501
        else:
            radio.setText(f"{suggestion_name} - New Control (UNPUBLISHED)")
        radio.feature = suggestion_fieldrun_shot  # type: ignore [] []
        self.verticalLayout_8.insertWidget(0, radio)

    def get_result(self) -> ControlMatchResult | None:
        if self.create_new_radio.isChecked():
            name = self.create_new_input.text()
            if not name:
                msg = "Cannot create new control with a blank name."
                raise AbortError(msg)
            return ControlMatchResult(
                None,
                new_fieldrunshot_name=name,
            )
        if self.other_control_radio.isChecked():
            feature = self.other_control_input.feature()
            if not feature:
                msg = "Other was checked, but no feature was selected."
                raise AbortError(msg)
            return ControlMatchResult(
                feature,
                None,
            )
        for i in range(self.verticalLayout_8.count()):
            child = self.verticalLayout_8.itemAt(i).widget()

            if isinstance(child, QRadioButton) and child.isChecked() and hasattr(child, "feature"):
                feature = getattr(child, "feature")  # noqa: B009
                return ControlMatchResult(
                    feature,
                    None,
                )
        return None
