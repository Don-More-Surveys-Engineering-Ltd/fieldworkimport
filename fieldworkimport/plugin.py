from __future__ import annotations

import json
import pprint
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PyQt5.QtWidgets import QAction, QMessageBox, QWidget
from qgis.core import Qgis, QgsFeature, QgsProject, QgsSettings, QgsVectorLayer
from qgis.gui import QgisInterface
from qgis.PyQt.QtGui import QIcon
from qgis.utils import iface as _iface

from fieldworkimport.controlpublish.publish_controls_dialog import PublishControlsDialog
from fieldworkimport.fwimport.import_process import FieldworkImportProcess
from fieldworkimport.helpers import (
    BASE_DIR,
    assert_true,
    get_layers_by_table_name,
    progress_dialog,
    settings_key,
    timed,
)
from fieldworkimport.reportgen.report_process import create_report, gather_report_variables
from fieldworkimport.samepointshots.findsamepointshots_process import FindGlobalSamePointShots
from fieldworkimport.ui.delete_dialog import DeleteFieldworkDialog
from fieldworkimport.ui.generate_report_dialog import GenerateReportDialog
from fieldworkimport.ui.import_finished_dialog import ImportFinishedDialog
from fieldworkimport.ui.validation_settings_dialog import ValidationSettingsDialog

iface: QgisInterface = _iface  # type: ignore

from fieldworkimport.exceptions import AbortError
from fieldworkimport.ui.import_dialog import ImportFieldworkDialog


@dataclass
class PluginInput:
    """Holds import input to be passwd around."""

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
            mouse pointer hovers over the action.

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
        self._setup_settings()

        # add different toolbar/dropdown buttons
        self.add_action(
            "",
            text="Change Settings",
            callback=self.start_validation_settings,
            parent=iface.mainWindow(),
            add_to_toolbar=False,
        )
        self.add_action(
            str(BASE_DIR / "resources" / "icons" / "new_import.png"),
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
            callback=self.start_find_same_point_shots_global,
            parent=iface.mainWindow(),
            add_to_toolbar=False,
        )
        self.add_action(
            "",
            text="Delete a fieldwork",
            callback=self.start_delete_fieldwork,
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

    def _setup_settings(self) -> None:  # noqa: PLR6301
        """Setup the plugin settings for the first time."""  # noqa: D401, DOC501
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

    def start_import(self) -> None:
        """Start the import process by showing import dialog."""
        project = QgsProject.instance()
        fieldwork_layer_present = len(get_layers_by_table_name("public", "sites_fieldwork", no_filter=True)) > 0
        if project is None or not fieldwork_layer_present:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText("No project found.")
            msg.setInformativeText("Please open a DMSE fieldwork project first.")
            msg.setWindowTitle("No Project Found")
            msg.exec()
            return

        new_import_dialog = ImportFieldworkDialog()
        return_code = new_import_dialog.exec_()

        if return_code == new_import_dialog.Rejected:
            return

        # create a dataclass to pass around the input variables to the different steps.
        self.plugin_input = PluginInput(
            crdb_path=new_import_dialog.crdb_file_input.filePath(),
            rw5_path=new_import_dialog.rw5_file_input.filePath(),
            sum_path=new_import_dialog.sum_file_input.filePath(),
            ref_path=new_import_dialog.ref_file_input.filePath(),
            loc_path=new_import_dialog.loc_file_input.filePath(),
            fieldrun_feature=new_import_dialog.fieldrun_input.feature(),
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

        # rollback if aborted
        if return_code == ImportFinishedDialog.Rejected:
            fwimport.rollback()
            return

        # commit changes
        with progress_dialog("Saving Changes...") as sp:
            fail_msg = "Failed to commit {}."
            assert_true(fwimport.layers.fieldwork_layer.commitChanges(), fail_msg.format("fieldwork_layer"))
            sp(25)
            assert_true(fwimport.layers.fieldworkshot_layer.commitChanges(), fail_msg.format("fieldworkshot_layer"))
            sp(75)
            assert_true(fwimport.layers.fieldrunshot_layer.commitChanges(), fail_msg.format("fieldrunshot_layer"))

        # refresh all layers to show new points
        canvas = iface.mapCanvas()
        if canvas:
            canvas.refreshAllLayers()

        # # integrate with other fieldwork by finding same point shots
        # start by selecting all fieldwork shots
        fwimport.layers.fieldworkshot_layer.selectByExpression(f'"fieldwork_id" = \'{fwimport.fieldwork_feature['id']}\'')
        # then select all points in bbox of fieldwork shots to get shots from other fieldwork
        bbox = fwimport.layers.fieldworkshot_layer.boundingBoxOfSelected()
        fwimport.layers.fieldworkshot_layer.selectByRect(bbox)

        # refresh fieldwork feature to get populated one with a fid
        refreshed_fieldwork = next(fwimport.layers.fieldwork_layer.getFeatures(f"id = '{fwimport.fieldwork_feature['id']}'"))

        # --- OPTIONAL STEPS ---

        # then check for same-point shots collisions in other exisitng fieldwork if requested
        if import_finished_dialog.next_check_same_point_shots_checkbox.isChecked():
            self.start_find_same_point_shots_global()
        # then check for unpublished controls in this fieldwork to publish if requested
        if import_finished_dialog.next_publish_controls_checkbox.isChecked():
            self.start_publish_controls(default_fieldwork=refreshed_fieldwork)
        # then create report for this fieldwork if requested
        if import_finished_dialog.next_create_report_checkbox.isChecked():
            self.start_generate_report(default_fieldwork=refreshed_fieldwork)

    def start_publish_controls(self, *args, default_fieldwork: QgsFeature | None = None):
        """Open a dialog with unplublished controls that match with the selected fieldwork.

        Allow user to edit information on those controls, and autopopulate easting northing elevation from matched
        fieldwork shot.
        """
        with progress_dialog("Searching for new controls...") as sp:
            sp(25)
            dialog = PublishControlsDialog(default_fieldwork)
            sp(75)
        dialog.exec_()

    def start_generate_report(self, *args, default_fieldwork: QgsFeature | None = None):
        """Open a dialog with the fieldwork and some fields for information to display in the report.

        Then generate report for fieldwork.

        The report can be run as the finishing part of the import wizard, or on its own from the plugin drop down menu.
        If it is run as part of the wizard, the raw data from the files given to the wizard are passed to the report,
            and the report will feature a raw data section.
        """
        # if the report is generated as part of the import wizard, we have access to the plugin input/raw data.
        # we use the path to the raw data files to figure out where to save the report to on the file system.
        default_save_path = None
        if self.plugin_input and self.plugin_input.crdb_path:
            default_save_path = str(Path(self.plugin_input.crdb_path).parent)

        # show dialog
        dialog = GenerateReportDialog(default_fieldwork, default_save_path)
        return_code = dialog.exec_()
        if return_code == dialog.Rejected:
            return

        # get field values from dialog
        fieldwork_feature = dialog.fieldwork_input.feature()
        job_number = dialog.job_number_input.text()
        client_name = dialog.client_name_input.text()
        output_folder_path = Path(dialog.output_folder_input.filePath())

        s = QgsSettings()
        debug_mode: bool = s.value(settings_key("debug_mode"), False, bool)  # noqa: FBT003

        with progress_dialog("Generating Report...") as sp:
            # gather fieldwork data needed for the report
            report_vars = gather_report_variables(fieldwork_feature, self.plugin_input, job_number, client_name)
            sp(25)
            if debug_mode:
                with (output_folder_path / "report_vars.txt").open("w") as fptr:
                    fptr.write(pprint.pformat(report_vars))
            sp(75)
            # render report out to html with report vars
            with (output_folder_path / "Fieldwork Report.html").open("w") as fptr:
                html = create_report(report_vars)
                fptr.write(html)

    def start_find_same_point_shots_global(self):
        """Search for pairs of shots with the same code within 0.075 meters of eachother with in the QGIS selected features.

        Then prompt the user with a choice on which point to keep/parent, and a choice to
            create a completely new point with the root points that make up the two shots in question (this has it's
            own dialog for selecting which shots to calculate from).

        This serves to integrate the new fieldwork into the history of existing fieldwork,
            finding which shots represent the same point.
        """  # noqa: E501
        with timed("class setup"):
            shot_merge = FindGlobalSamePointShots()
        shot_merge.run()

    def start_validation_settings(self):
        """Prompt user with settings on how this plugin runs.

        Includes tolerances, which codes are valid, etc.
        """
        dialog = ValidationSettingsDialog()
        dialog.exec()

    def start_delete_fieldwork(self):
        """Allow user to select a fieldwork to delete in a dialog.

        Then delete it.
        """
        dialog = DeleteFieldworkDialog()
        return_code = dialog.exec_()
        if return_code == dialog.Rejected:
            return

        with progress_dialog("Deleting fieldwork...") as sp:
            # setup
            fieldwork = dialog.fieldwork_input.feature()
            fieldwork_layer = get_layers_by_table_name("public", "sites_fieldwork", no_filter=True, raise_exception=True)[0]
            fieldworkshot_layer = get_layers_by_table_name("public", "sites_fieldworkshot", no_filter=True, raise_exception=True)[0]
            fieldrunshot_layer = get_layers_by_table_name("public", "sites_fieldrunshot", no_filter=True, raise_exception=True)[0]
            fieldwork_layer.startEditing()
            fieldworkshot_layer.startEditing()
            fieldrunshot_layer.startEditing()
            sp(25)

            # remove matches from fieldrun shots
            shots: list[QgsFeature] = [*fieldworkshot_layer.getFeatures(f"\"fieldwork_id\" = '{fieldwork.attribute('id')}'")]  # type: ignore
            for shot in shots:
                matched_fieldrun_shot = next(fieldrunshot_layer.getFeatures(f"matched_fieldwork_shot_id = '{shot['id']}'"), None)
                if matched_fieldrun_shot:
                    matched_fieldrun_shot["matched_fieldwork_shot_id"] = None
                    fieldrunshot_layer.updateFeature(matched_fieldrun_shot)
            sp(50)
            # delete features
            assert_true(fieldworkshot_layer.deleteFeatures([shot.id() for shot in shots]), "Failed to delete fieldworkshots.")
            assert_true(fieldwork_layer.deleteFeature(fieldwork.id()), "Failed to delete fieldwork.")
            sp(75)
            # commit changes
            assert_true(fieldrunshot_layer.commitChanges(), "Failed to commit fieldworkshot layer.")
            sp(85)
            assert_true(fieldworkshot_layer.commitChanges(), "Failed to commit fieldworkshot layer.")
            sp(95)
            assert_true(fieldwork_layer.commitChanges(), "Failed to commit fieldwork layer.")

        # refresh all layers to show new points
        canvas = iface.mapCanvas()
        if canvas:
            canvas.refreshAllLayers()

        msg_bar = iface.messageBar()
        assert msg_bar
        msg_bar.pushMessage("Success", "Deleted fieldwork.", level=Qgis.MessageLevel.Success)
