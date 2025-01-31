from collections.abc import Iterator
from typing import TYPE_CHECKING, Optional

from qgis.core import Qgis, QgsFeature, QgsFeatureRequest, QgsMessageLog, QgsVectorLayer
from qgis.PyQt import QtWidgets

from fieldworkimport.exceptions import AbortError
from fieldworkimport.fwimport.validate_code import validate_code
from fieldworkimport.ui.code_correction_dialog import CodeCorrectionDialog
from fieldworkimport.ui.point_warning_item import PointWarningItem
from fieldworkimport.ui.point_warnings_dialog import PointWarningsDialog

if TYPE_CHECKING:
    from fieldworkimport.plugin import PluginInput


def validate_point(point: QgsFeature, plugin_input: "PluginInput") -> bool:
    hrms: float = point.attribute("HRMS")
    vrms: float = point.attribute("VRMS")
    code: str = point.attribute("code")
    status: Optional[str] = point.attribute("status")  # noqa: FA100
    invalid = False

    if hrms > plugin_input.hrms_tolerance:
        point.setAttribute("bad_hrms_flag", True)
        invalid = True
    if vrms > plugin_input.vrms_tolerance:
        point.setAttribute("bad_vrms_flag", True)
        invalid = True
    if status and "fixed" not in status.lower():
        point.setAttribute("bad_fixed_status_flag", True)
        invalid = True

    code_valid = validate_code(
        code,
        valid_codes=plugin_input.valid_codes,
        valid_special_characters=plugin_input.valid_special_chars,
        parameterized_special_characters=plugin_input.parameterized_special_chars,
    )
    if not code_valid:
        point.setAttribute("bad_code_flag", True)
        invalid = True
    return not invalid


def validate_points(
    fieldworkshot_layer: QgsVectorLayer,
    fieldwork_id: int,
    plugin_input: "PluginInput",
):
    QgsMessageLog.logMessage(
        "Validate points started.",
    )
    points: list[QgsFeature] = [
        *fieldworkshot_layer.getFeatures(
            QgsFeatureRequest()
            .setFilterExpression(f"\"fieldwork_id\" = '{fieldwork_id}'")
            .setFlags(Qgis.FeatureRequestFlag.NoGeometry),
        ),  # type: ignore []
    ]

    fieldworkshot_layer.startEditing()
    for point in points:
        valid = validate_point(point, plugin_input)
        if not valid:
            # update invalid flags
            fieldworkshot_layer.updateFeature(point)


def correct_codes(
    fieldworkshot_layer: QgsVectorLayer,
    fieldwork_id: int,
    plugin_input: "PluginInput",
):
    QgsMessageLog.logMessage(
        "Correct points started.",
    )
    fields = fieldworkshot_layer.fields()
    code_index = fields.indexFromName("code")
    description_index = fields.indexFromName("description")
    points: list[QgsFeature] = [
        *fieldworkshot_layer.getFeatures(
            QgsFeatureRequest().setFilterExpression(f"\"fieldwork_id\" = '{fieldwork_id}'"),
        ),  # type: ignore
    ]

    corrections = {
        "__bad_code__": "__good_code__",
    }

    fieldworkshot_layer.startEditing()
    for point in points:
        code = point.attribute("code")
        description: str = point.attribute("description")
        code_valid = validate_code(
            code,
            valid_codes=plugin_input.valid_codes,
            valid_special_characters=plugin_input.valid_special_chars,
            parameterized_special_characters=plugin_input.parameterized_special_chars,
        )

        if not code_valid:
            if code not in corrections:
                # populate corrections
                dialog = CodeCorrectionDialog(
                    code,
                    valid_codes=plugin_input.valid_codes,
                    valid_special_chars=plugin_input.valid_special_chars,
                    parameterized_special_chars=plugin_input.parameterized_special_chars,
                )
                dialog.exec_()
                # either the exception was ignored or corrected, use the correction value
                correction = dialog.correction_input.text()
                if correction:
                    corrections[code] = correction
                else:
                    corrections[code] = code
            point[code_index] = corrections[code]
            delim_index = description.find("/")
            point[description_index] = corrections[code] + (description[delim_index:] if delim_index else "")
            fieldworkshot_layer.updateFeature(point)


def show_warnings(
    fieldworkshot_layer: QgsVectorLayer,
    fieldwork_id: int,
    plugin_input: "PluginInput",
):
    QgsMessageLog.logMessage(
        "Show warnings started.",
    )
    points: Iterator[QgsFeature] = fieldworkshot_layer.getFeatures(
        QgsFeatureRequest().setFilterExpression(f"\"fieldwork_id\" = '{fieldwork_id}'"),
    )  # type: ignore

    warning_widgets: list[QtWidgets.QWidget] = []
    for point in points:
        bad_hrms_flag = point.attribute("bad_hrms_flag")
        bad_vrms_flag = point.attribute("bad_vrms_flag")
        bad_fixed_status_flag = point.attribute("bad_fixed_status_flag")
        if bad_fixed_status_flag in {"true", True} or bad_hrms_flag in {"true", True} or bad_vrms_flag in {"true", True}:
            warning_widgets.append(
                PointWarningItem(point),
            )

    if len(warning_widgets) > 0:
        dialog = PointWarningsDialog(
            hrms_tolerance=plugin_input.hrms_tolerance,
            vrms_tolerance=plugin_input.vrms_tolerance,
        )
        for w in warning_widgets:
            dialog.scrollAreaWidgetContents.layout().addWidget(w)
        return_code = dialog.exec_()
        if return_code == dialog.Rejected:
            # abort process
            msg = "Aborted due to point warnings."
            raise AbortError(msg)
