from __future__ import annotations

import json
import pprint
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PyQt5.QtWidgets import QAction, QWidget
from qgis.core import Qgis, QgsFeature, QgsSettings, QgsVectorLayer
from qgis.gui import QgisInterface
from qgis.PyQt.QtGui import QIcon
from qgis.utils import iface as _iface

from fieldworkimport.controlpublish.publish_controls_dialog import PublishControlsDialog
from fieldworkimport.fwimport.import_process import FieldworkImportProcess
from fieldworkimport.helpers import BASE_DIR, assert_true, progress_dialog, settings_key, timed
from fieldworkimport.reportgen.report_process import create_report, get_report_variables
from fieldworkimport.samepointshots.findsamepointshots_process import FindSamePointShots
from fieldworkimport.ui.generate_report_dialog import GenerateReportDialog
from fieldworkimport.ui.import_finished_dialog import ImportFinishedDialog
from fieldworkimport.ui.validation_settings_dialog import ValidationSettingsDialog

iface: QgisInterface = _iface  # type: ignore

from fieldworkimport.exceptions import AbortError
from fieldworkimport.ui.import_dialog import ImportFieldworkDialog


@dataclass
class PluginInput:
    """Holds validation settings and import input."""

    crdb_path: str
    rw5_path: str
    sum_path: str | None
    ref_path: str | None
    loc_path: str | None
    fieldrun_feature: QgsFeature | None


class Plugin:
    """QGIS Plugin Implementation."""

    name = "fieldworkimport"
    import_dialog: ImportFieldworkDialog | None
    fieldwork_layer: QgsVectorLayer
    fieldworkshot_layer: QgsVectorLayer
    plugin_input: PluginInput | None

    def __init__(self) -> None:
        self.actions: list[QAction] = []
        self.menu = Plugin.name
        self.plugin_input = None

    def add_action(
        self,
        icon_path: str,
        text: str,
        callback: Callable,
        *,
        enabled_flag: bool = True,
        add_to_menu: bool = True,
        add_to_toolbar: bool = True,
        status_tip: str | None = None,
        whats_this: str | None = None,
        parent: QWidget | None = None,
    ) -> QAction:
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.

        :param text: Text that should be shown in menu items for this action.

        :param callback: Function to be called when the action is triggered.

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.

        :param parent: Parent widget for the new action. Defaults None.

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action .

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """  # noqa: DOC201
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        # noinspection PyUnresolvedReferences
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            iface.addToolBarIcon(action)

        if add_to_menu:
            iface.addPluginToMenu(self.menu, action)

        self.actions.append(action)

        return action

    def initGui(self) -> None:  # noqa: N802
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        self.setup_settings()
        self.add_action(
            "",
            text="Change Settings",
            callback=self.start_validation_settings,
            parent=iface.mainWindow(),
            add_to_toolbar=False,
        )
        self.add_action(
            str(BASE_DIR / "resources" / "icons" / "noun-geodesy-7254004.svg"),
            text="Import Fieldwork",
            callback=self.start_import,
            parent=iface.mainWindow(),
            add_to_toolbar=True,
        )
        self.add_action(
            "",
            text="Find and Publish Controls",
            callback=self.start_publish_controls,
            parent=iface.mainWindow(),
            add_to_toolbar=False,
        )
        self.add_action(
            "",
            text="Generate a Processing Report",
            callback=self.start_generate_report,
            parent=iface.mainWindow(),
            add_to_toolbar=False,
        )
        self.add_action(
            "",
            text="Find Same-point Shots",
            callback=self.start_find_same_point_shots,
            parent=iface.mainWindow(),
            add_to_toolbar=False,
        )

    def onClosePlugin(self) -> None:  # noqa: N802
        """Cleanup necessary items here when plugin dockwidget is closed."""

    def unload(self) -> None:
        """Remove the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            iface.removePluginMenu(Plugin.name, action)
            iface.removeToolBarIcon(action)

    def setup_settings(self):
        s = QgsSettings()

        validation_file_path = BASE_DIR / "resources" / "validation_settings.json"
        if not validation_file_path:
            msg = "QGIS settings is missing validation settings file path."
            raise ValueError(msg)

        validation_settings: dict = json.loads(Path(validation_file_path).read_text(encoding="utf-8"))
        key = settings_key("hrms_tolerance")
        if not s.contains(key) or not s.value(key):
            s.setValue(key, validation_settings.get("hrms_tolerance", 0))
        key = settings_key("vrms_tolerance")
        if not s.contains(key) or not s.value(key):
            s.setValue(key, validation_settings.get("vrms_tolerance", 0))
        key = settings_key("same_point_tolerance")
        if not s.contains(key) or not s.value(key):
            s.setValue(key, validation_settings.get("same_point_tolerance", 0))
        key = settings_key("valid_codes")
        if not s.contains(key) or not s.value(key):
            s.setValue(key, validation_settings.get("valid_codes", 0))
        key = settings_key("valid_special_chars")
        if not s.contains(key) or not s.value(key):
            s.setValue(key, validation_settings.get("valid_special_chars", 0))
        key = settings_key("parameterized_special_chars")
        if not s.contains(key) or not s.value(key):
            s.setValue(key, validation_settings.get("parameterized_special_chars", 0))
        key = settings_key("control_point_codes")
        if not s.contains(key) or not s.value(key):
            s.setValue(key, validation_settings.get("control_point_codes", 0))
        key = settings_key("debug_mode")
        if not s.contains(key):
            s.setValue(key, False)  # noqa: FBT003

    def _setup_import_dialog(self) -> ImportFieldworkDialog:
        dialog = ImportFieldworkDialog()

        return dialog

    def _on_accept_new_form(self):
        if not self.import_dialog:
            return

        self.plugin_input = PluginInput(
            crdb_path=self.import_dialog.crdb_file_input.filePath(),
            rw5_path=self.import_dialog.rw5_file_input.filePath(),
            sum_path=self.import_dialog.sum_file_input.filePath(),
            ref_path=self.import_dialog.ref_file_input.filePath(),
            loc_path=self.import_dialog.loc_file_input.filePath(),
            fieldrun_feature=self.import_dialog.fieldrun_input.feature(),
        )

        fwimport = FieldworkImportProcess(
            self.plugin_input,
        )

        # run fieldwork import process
        try:
            fwimport.run()
        except AbortError as e:
            iface.messageBar().pushMessage("Import Aborted", e.args[0], level=Qgis.MessageLevel.Critical)  # type: ignore
            return

        # show import finished dialog
        import_finished_dialog = ImportFinishedDialog()
        return_code = import_finished_dialog.exec_()

        # rollback if requested
        if return_code == ImportFinishedDialog.Rejected:
            fwimport.rollback()
            return

        # commit changes
        with progress_dialog("Saving Changes...", indeterminate=True):
            fail_msg = "Failed to commit {}."
            assert_true(fwimport.layers.fieldwork_layer.commitChanges(), fail_msg.format("fieldwork_layer"))
            assert_true(fwimport.layers.fieldworkshot_layer.commitChanges(), fail_msg.format("fieldworkshot_layer"))
            assert_true(fwimport.layers.fieldrunshot_layer.commitChanges(), fail_msg.format("fieldrunshot_layer"))
            assert_true(fwimport.layers.controlpointdata_layer.commitChanges(), fail_msg.format("controlpointdata_layer"))

        # # integrate with other fieldwork by finding same point shots
        # start by selecting all fieldwork shots
        fwimport.layers.fieldworkshot_layer.selectByExpression(f'"fieldwork_id" = \'{fwimport.fieldwork_feature['id']}\'')
        # then select all points in bbox of fieldwork shots to get shots from other fieldwork
        bbox = fwimport.layers.fieldworkshot_layer.boundingBoxOfSelected()
        fwimport.layers.fieldworkshot_layer.selectByRect(bbox)
        # then run find_same_point_shots
        self.start_find_same_point_shots()

        # refresh fieldwork feature to get populated one with a fid
        refreshed_fieldwork = next(fwimport.layers.fieldwork_layer.getFeatures(f"id = '{fwimport.fieldwork_feature['id']}'"))
        # publish controls if requested
        if import_finished_dialog.next_publish_controls_checkbox.isChecked():
            with timed("start_publish_controls"):
                self.start_publish_controls(default_fieldwork=refreshed_fieldwork)
        # create report if requested
        if import_finished_dialog.next_create_report_checkbox.isChecked():
            self.start_generate_report(default_fieldwork=refreshed_fieldwork)

    def start_import(self) -> None:
        """Run method that performs all the real work."""
        self.import_dialog = self._setup_import_dialog()
        self.import_dialog.show()
        self.import_dialog.accepted.connect(self._on_accept_new_form)

    def start_publish_controls(self, *args, default_fieldwork: QgsFeature | None = None):
        with progress_dialog("Searching for new controls...", indeterminate=True):
            dialog = PublishControlsDialog(default_fieldwork)
        dialog.exec_()

    def start_generate_report(self, *args, default_fieldwork: QgsFeature | None = None):
        default_save_path = None
        if self.plugin_input and self.plugin_input.crdb_path:
            default_save_path = str(Path(self.plugin_input.crdb_path).parent)
        dialog = GenerateReportDialog(default_fieldwork, default_save_path)
        return_code = dialog.exec_()
        if return_code == dialog.Rejected:
            return
        fieldwork_feature = dialog.fieldwork_input.feature()
        job_number = dialog.job_number_input.text()
        client_name = dialog.client_name_input.text()
        output_folder_path = Path(dialog.output_folder_input.filePath())

        s = QgsSettings()
        debug_mode: bool = s.value(settings_key("debug_mode"), False, bool)

        with progress_dialog("Generating Report...", indeterminate=True):
            report_vars = get_report_variables(fieldwork_feature, self.plugin_input, job_number, client_name)
            if debug_mode:
                with (output_folder_path / "report_vars.txt").open("w") as fptr:
                    fptr.write(pprint.pformat(report_vars))

        with (output_folder_path / "Fieldwork Report.html").open("w") as fptr:
            html = create_report(report_vars)
            fptr.write(html)

    def start_find_same_point_shots(self):
        with timed("class setup"):
            shot_merge = FindSamePointShots()
        shot_merge.run()

    def start_validation_settings(self):
        dialog = ValidationSettingsDialog()
        dialog.exec()
