from typing import Optional

from PyQt5.QtWidgets import QDialog, QWidget
from qgis.core import QgsSettings

from fieldworkimport.helpers import settings_key
from fieldworkimport.ui.generated.validation_settings_ui import Ui_ValidationSettingsDialog


class ValidationSettingsDialog(QDialog, Ui_ValidationSettingsDialog):
    def __init__(self, parent: Optional[QWidget] = None):  # noqa: FA100
        super().__init__(parent)
        self.setupUi(self)

        s = QgsSettings()

        self.hrms_tolerance_input.setValue(float(s.value(settings_key("hrms_tolerance"), 0)))
        self.vrms_tolerance_input.setValue(float(s.value(settings_key("vrms_tolerance"), 0)))
        self.same_point_tolerance_input.setValue(float(s.value(settings_key("same_point_tolerance"), 0)))
        self.valid_codes_input.setPlainText(s.value(settings_key("valid_codes"), ""))
        self.valid_special_chars_input.setText(s.value(settings_key("valid_special_chars"), ""))
        self.parameterized_special_chars_input.setText(s.value(settings_key("parameterized_special_chars"), ""))
        self.control_point_codes_input.setText(s.value(settings_key("control_point_codes"), ""))
        self.debug_mode_checkbox.setChecked(s.value(settings_key("debug_mode"), False, bool))  # noqa: FBT003

    def accept(self) -> None:
        s = QgsSettings()
        key = settings_key("hrms_tolerance")
        s.setValue(key, self.hrms_tolerance_input.value())
        key = settings_key("vrms_tolerance")
        s.setValue(key, self.vrms_tolerance_input.value())
        key = settings_key("same_point_tolerance")
        s.setValue(key, self.same_point_tolerance_input.value())
        key = settings_key("valid_codes")
        s.setValue(key, self.valid_codes_input.toPlainText())
        key = settings_key("valid_special_chars")
        s.setValue(key, self.valid_special_chars_input.text())
        key = settings_key("parameterized_special_chars")
        s.setValue(key, self.parameterized_special_chars_input.text())
        key = settings_key("control_point_codes")
        s.setValue(key, self.control_point_codes_input.text())
        key = settings_key("debug_mode")
        s.setValue(key, self.debug_mode_checkbox.isChecked())

        return super().accept()
