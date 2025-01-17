from __future__ import annotations

from pathlib import Path
from typing import Callable

from PyQt5.QtWidgets import QMessageBox, QWidget
from qgis.core import QgsSettings
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.utils import iface

from fieldworkimport.fieldwork.helpers import ReturnCode, get_layers_by_table_name
from fieldworkimport.fieldwork.import_fieldwork import create_fieldwork
from fieldworkimport.fieldwork.local_point_merge import local_point_merge
from fieldworkimport.fieldwork.validate_points import correct_codes, show_warnings, validate_points
from fieldworkimport.ui.new_form_dialog import ImportFieldworkDialog


class Plugin:
    """QGIS Plugin Implementation."""

    name = "fieldworkimport"
    import_dialog: ImportFieldworkDialog | None
    active_fieldwork_feature = None

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
            "",
            text=Plugin.name,
            callback=self.run,
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

        fieldrun_layer = get_layers_by_table_name("public", "sites_fieldrun", no_filter=True, raise_exception=True)[0]

        dialog.fieldrun_input.setLayer(fieldrun_layer)

        return dialog

    def rollback(self):
        # rollback changes.
        get_layers_by_table_name("public", "sites_fieldrun", no_filter=True, raise_exception=True)[0].rollBack()
        get_layers_by_table_name("public", "sites_fieldrunshotimage", no_filter=True, raise_exception=True)[0].rollBack()
        get_layers_by_table_name("public", "sites_fieldrunshot", no_filter=True, raise_exception=True)[0].rollBack()
        get_layers_by_table_name("public", "sites_fieldworkshot", no_filter=True, raise_exception=True)[0].rollBack()
        get_layers_by_table_name("public", "sites_fieldwork", no_filter=True, raise_exception=True)[0].rollBack()
        get_layers_by_table_name("public", "sites_pipe", no_filter=True, raise_exception=True)[0].rollBack()
        get_layers_by_table_name("public", "sites_measurement", no_filter=True, raise_exception=True)[0].rollBack()

    def _on_accept_new_form(self):
        if not self.import_dialog:
            return
        crdb_path = self.import_dialog.crdb_file_input.filePath()
        rw5_path = self.import_dialog.rw5_file_input.filePath()
        sum_path = self.import_dialog.sum_file_input.filePath()
        ref_path = self.import_dialog.ref_file_input.filePath()
        loc_path = self.import_dialog.loc_file_input.filePath()
        fieldrun = self.import_dialog.fieldrun_input.feature()

        vrms_tolerance = self.import_dialog.vrms_tolerance_input.value()
        hrms_tolerance = self.import_dialog.hrms_tolerance_input.value()
        same_point_tolerance = self.import_dialog.same_point_tolerance_input.value()
        valid_codes = self.import_dialog.valid_codes_input.toPlainText().split(",")
        valid_special_chars = self.import_dialog.valid_special_chars_input.text().split(",")
        parameterized_special_chars = self.import_dialog.parameterized_special_chars_input.text().split(",")
        control_point_codes = self.import_dialog.control_point_codes_input.text().split(",")

        fieldwork = create_fieldwork(
            crdb_path=crdb_path,
            rw5_path=rw5_path,
            sum_path=sum_path,
            ref_path=ref_path,
            loc_path=loc_path,
            fieldrun_feature=fieldrun,
        )[1]

        return_code = validate_points(
            fieldwork_id=fieldwork.attribute("id"),
            hrms_tolerance=hrms_tolerance,
            vrms_tolerance=vrms_tolerance,
            valid_codes=valid_codes,
            valid_special_chars=valid_special_chars,
            parameterized_special_chars=parameterized_special_chars,
        )[0]
        if return_code == ReturnCode.ABORT:
            self.rollback()
            return

        return_code = correct_codes(
            fieldwork_id=fieldwork.attribute("id"),
            valid_codes=valid_codes,
            valid_special_chars=valid_special_chars,
            parameterized_special_chars=parameterized_special_chars,
        )[0]
        if return_code == ReturnCode.ABORT:
            self.rollback()
            return

        return_code = show_warnings(
            fieldwork_id=fieldwork.attribute("id"),
            hrms_tolerance=hrms_tolerance,
            vrms_tolerance=vrms_tolerance,
        )[0]
        if return_code == ReturnCode.ABORT:
            self.rollback()
            return

        return_code = local_point_merge(
            fieldwork_id=fieldwork.attribute("id"),
            same_point_tolerance=same_point_tolerance,
            control_point_codes=control_point_codes,
        )[0]
        if return_code == ReturnCode.ABORT:
            self.rollback()
            return

        if fieldwork:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText("Success")
            msg.setInformativeText(
                f"Fieldwork {fieldwork.attribute('name')} done.\nNow look over your work and save changes if you like what you see, or rollback if you don't.",
            )
            msg.setWindowTitle("Import Complete")
            msg.exec()

    def run(self) -> None:
        """Run method that performs all the real work."""
        self.import_dialog = self._setup_import_dialog()
        self.import_dialog.show()
        self.import_dialog.accepted.connect(self._on_accept_new_form)
