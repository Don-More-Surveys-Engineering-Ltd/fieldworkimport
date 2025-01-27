from __future__ import annotations

from pathlib import Path
from typing import Callable

from PyQt5.QtWidgets import QAction, QWidget
from qgis.core import Qgis, QgsFeature, QgsSettings, QgsVectorLayer
from qgis.gui import QgisInterface
from qgis.PyQt.QtGui import QIcon
from qgis.utils import iface as _iface

from fieldworkimport.controlpublish.publish_controls_dialog import PublishControlsDialog
from fieldworkimport.fwimport.import_process import FieldworkImportProcess
from fieldworkimport.ui.import_finished_dialog import ImportFinishedDialog

iface: QgisInterface = _iface  # type: ignore

from fieldworkimport.exceptions import AbortError
from fieldworkimport.ui.import_dialog import ImportFieldworkDialog


class Plugin:
    """QGIS Plugin Implementation."""

    name = "fieldworkimport"
    import_dialog: ImportFieldworkDialog | None
    active_fieldwork_feature = None

    geopackage_path: str
    geopackage_layers_group_name: str
    fieldwork_layer: QgsVectorLayer
    fieldworkshot_layer: QgsVectorLayer

    def __init__(self) -> None:
        self.actions: list[QAction] = []
        self.menu = Plugin.name
        self.import_dialog = None

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
        self.setup_settings()
        self.add_action(
            str(Path(__file__).parent / "resources" / "icons" / "noun-geodesy-7254004.svg"),
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

    def onClosePlugin(self) -> None:  # noqa: N802
        """Cleanup necessary items here when plugin dockwidget is closed."""

    def unload(self) -> None:
        """Remove the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            iface.removePluginMenu(Plugin.name, action)
            iface.removeToolBarIcon(action)

    def setup_settings(self):
        settings = QgsSettings()
        key = "dmse/importfieldwork/validation_settings_file"
        if not settings.contains(key) or not settings.value(key) or not Path(settings.value(key)).exists():
            settings.setValue(key, Path(__file__).parent / "resources" / "validation_settings.json")

    def _setup_import_dialog(self) -> ImportFieldworkDialog:
        dialog = ImportFieldworkDialog()

        return dialog

    def _on_accept_new_form(self):
        if not self.import_dialog:
            return

        crdb_path = self.import_dialog.crdb_file_input.filePath()
        rw5_path = self.import_dialog.rw5_file_input.filePath()
        sum_path = self.import_dialog.sum_file_input.filePath()
        ref_path = self.import_dialog.ref_file_input.filePath()
        loc_path = self.import_dialog.loc_file_input.filePath()
        fieldrun: QgsFeature = self.import_dialog.fieldrun_input.feature()

        vrms_tolerance = self.import_dialog.vrms_tolerance_input.value()
        hrms_tolerance = self.import_dialog.hrms_tolerance_input.value()
        same_point_tolerance = self.import_dialog.same_point_tolerance_input.value()
        valid_codes = self.import_dialog.valid_codes_input.toPlainText().split(",")
        valid_special_chars = self.import_dialog.valid_special_chars_input.text().split(",")
        parameterized_special_chars = self.import_dialog.parameterized_special_chars_input.text().split(",")
        control_point_codes = self.import_dialog.control_point_codes_input.text().split(",")

        fwimport = FieldworkImportProcess(
            vrms_tolerance,
            hrms_tolerance,
            same_point_tolerance,
            valid_codes,
            valid_special_chars,
            parameterized_special_chars,
            control_point_codes,
            crdb_path,
            rw5_path,
            sum_path,
            ref_path,
            loc_path,
            fieldrun,
        )

        try:
            fwimport.run()
        except AbortError as e:
            iface.messageBar().pushMessage("Import Aborted", e.args[0], level=Qgis.MessageLevel.Critical)  # type: ignore
            return

        import_finished_dialog = ImportFinishedDialog()
        return_code = import_finished_dialog.exec_()

        if return_code == ImportFinishedDialog.Rejected:
            fwimport.rollback()
        else:
            fwimport.layers.fieldwork_layer.commitChanges()
            fwimport.layers.fieldworkshot_layer.commitChanges()

        if import_finished_dialog.next_publish_controls_checkbox.isChecked():
            self.start_publish_controls(fwimport.fieldwork_feature)
        if import_finished_dialog.next_create_report_checkbox.isChecked():
            pass  # TODO: Create report

    def start_import(self) -> None:
        """Run method that performs all the real work."""
        self.import_dialog = self._setup_import_dialog()
        self.import_dialog.show()
        self.import_dialog.accepted.connect(self._on_accept_new_form)

    def start_publish_controls(self, *args, default_fieldwork: QgsFeature | None = None):
        dialog = PublishControlsDialog(default_fieldwork)
        dialog.exec_()
