
from typing import Optional

from PyQt5.QtWidgets import QWidget
from qgis.core import QgsFeature

from fieldworkimport.ui.generated.point_warning_item_ui import Ui_PointWarning


class PointWarningItem(QWidget, Ui_PointWarning):
    def __init__(
        self,
        point: QgsFeature,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setupUi(self)

        name = point["name"]
        desc = point["description"]
        bad_hrms_flag = point["bad_hrms_flag"]
        bad_vrms_flag = point["bad_vrms_flag"]
        bad_fixed_status_flag = point["bad_fixed_status_flag"]

        warnings_html = "<ul>"
        if bad_hrms_flag in {"true", True}:
            hrms = point["hrms"]
            warnings_html += f"<li>HRMS over tolerance: <code>{hrms}</code></li>"
        if bad_vrms_flag in {"true", True}:
            vrms = point["vrms"]
            warnings_html += f"<li>VRMS over tolerance: <code>{vrms}</code></li>"
        if bad_fixed_status_flag in {"true", True}:
            fixed_status = point["status"]
            warnings_html += f"<li>Bad fixed status: <code>{fixed_status}</code></li>"
        warnings_html += "</ul>"

        self.PointNumber.setText(name)
        self.PointDescription.setText(desc)
        self.PointWarnings.setHtml(warnings_html)
