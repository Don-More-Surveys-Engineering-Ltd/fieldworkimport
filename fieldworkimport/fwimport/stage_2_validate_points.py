from collections.abc import Iterator

from qgis.core import Qgis, QgsFeature, QgsFeatureRequest, QgsMessageLog, QgsSettings, QgsVectorLayer
from qgis.PyQt import QtWidgets

from fieldworkimport.common import validate_code, validate_point
from fieldworkimport.exceptions import AbortError
from fieldworkimport.helpers import assert_true, settings_key
from fieldworkimport.ui.code_correction_dialog import CodeCorrectionDialog
from fieldworkimport.ui.point_warning_item import PointWarningItem
from fieldworkimport.ui.point_warnings_dialog import PointWarningsDialog


def validate_points(
    fieldworkshot_layer: QgsVectorLayer,
    fieldwork_id: int,
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
    s = QgsSettings()
    for point in points:
        valid = validate_point(
            point,
            float(s.value(settings_key("hrms_tolerance"), 0)),
            float(s.value(settings_key("vrms_tolerance"), 0)),
            s.value(settings_key("valid_codes"), "").split(","),
            s.value(settings_key("valid_special_chars"), "").split(","),
            s.value(settings_key("parameterized_special_chars"), "").split(","),
        )
        if not valid:
            # update invalid flags
            assert_true(fieldworkshot_layer.updateFeature(point), "Failed to update validation flags on fieldwork shot.")


def correct_codes(
    fieldworkshot_layer: QgsVectorLayer,
    fieldwork_id: int,
):
    QgsMessageLog.logMessage(
        "Correct points started.",
    )
    fields = fieldworkshot_layer.fields()
    code_index = fields.indexFromName("code")
    full_code_index = fields.indexFromName("full_code")
    description_index = fields.indexFromName("description")
    points: list[QgsFeature] = [
        *fieldworkshot_layer.getFeatures(
            QgsFeatureRequest().setFilterExpression(f"\"fieldwork_id\" = '{fieldwork_id}'"),
        ),  # type: ignore
    ]

    corrections = {
        "__bad_description__": "__good_description__",
    }

    s = QgsSettings()
    fieldworkshot_layer.startEditing()
    for point in points:
        full_code = point["full_code"]
        description: str = point["description"]
        full_code_valid = validate_code(
            full_code,
            s.value(settings_key("valid_codes"), "").split(","),
            s.value(settings_key("valid_special_chars"), "").split(","),
            s.value(settings_key("parameterized_special_chars"), "").split(","),
        )

        if not full_code_valid:
            if description not in corrections:
                # populate corrections
                dialog = CodeCorrectionDialog(
                    description,
                    s.value(settings_key("valid_codes"), "").split(","),
                    s.value(settings_key("valid_special_chars"), "").split(","),
                    s.value(settings_key("parameterized_special_chars"), "").split(","),
                )
                dialog.exec_()
                # either the exception was ignored or corrected, use the correction value
                description_correction = dialog.description
                if description_correction:
                    corrections[description] = description_correction
                else:
                    corrections[description] = description
            point[description_index] = corrections[description]
            point[full_code_index] = corrections[description].split("/")[0]
            point[code_index] = corrections[description].split("/")[0].split(" ")[0]
            assert_true(fieldworkshot_layer.updateFeature(point), "Failed to update code on fieldwork shot.")


def show_warnings(
    fieldworkshot_layer: QgsVectorLayer,
    fieldwork_id: int,
):
    QgsMessageLog.logMessage(
        "Show warnings started.",
    )
    points: Iterator[QgsFeature] = fieldworkshot_layer.getFeatures(
        QgsFeatureRequest().setFilterExpression(f"\"fieldwork_id\" = '{fieldwork_id}'"),
    )  # type: ignore

    warning_widgets: list[QtWidgets.QWidget] = []
    for point in points:
        bad_hrms_flag = point["bad_hrms_flag"]
        bad_vrms_flag = point["bad_vrms_flag"]
        bad_fixed_status_flag = point["bad_fixed_status_flag"]
        if bad_fixed_status_flag in {"true", True} or bad_hrms_flag in {"true", True} or bad_vrms_flag in {"true", True}:
            warning_widgets.append(
                PointWarningItem(point),
            )

    if len(warning_widgets) > 0:
        s = QgsSettings()
        dialog = PointWarningsDialog(
            float(s.value(settings_key("hrms_tolerance"), "")),
            float(s.value(settings_key("vrms_tolerance"), "")),
        )
        for w in warning_widgets:
            dialog.scrollAreaWidgetContents.layout().addWidget(w)
        return_code = dialog.exec_()
        if return_code == dialog.Rejected:
            # abort process
            msg = "Aborted due to point warnings."
            raise AbortError(msg)
