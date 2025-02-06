from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import QDialog, QMessageBox, QWidget

from fieldworkimport.helpers import get_layers_by_table_name
from fieldworkimport.ui.generated.new_form_ui import Ui_ImportDialog


class ImportFieldworkDialog(QDialog, Ui_ImportDialog):
    def __init__(self, parent: Optional[QWidget] = None):  # noqa: FA100
        super().__init__(parent)
        self.setupUi(self)

        # setup feature picker with layer
        fieldrun_layer = get_layers_by_table_name("public", "sites_fieldrun", no_filter=True, raise_exception=True)[0]
        self.fieldrun_input.setLayer(fieldrun_layer)

        def auto_complete_files():
            path = self.crdb_file_input.filePath()
            if path:
                _p = Path(path)
                parent = _p.parent
                name = _p.stem

                rw5_path = parent / f"{name}.rw5"
                sum_path = parent / f"{name}.sum"
                ref_path = parent / f"{name}.ref"
                loc_path = parent / f"{name}.loc"

                if rw5_path.exists() and not self.rw5_file_input.filePath():
                    self.rw5_file_input.setFilePath(str(rw5_path))
                if sum_path.exists() and not self.sum_file_input.filePath():
                    self.sum_file_input.setFilePath(str(sum_path))
                if ref_path.exists() and not self.ref_file_input.filePath():
                    self.ref_file_input.setFilePath(str(ref_path))
                if loc_path.exists() and not self.loc_file_input.filePath():
                    self.loc_file_input.setFilePath(str(loc_path))

        self.crdb_file_input.fileChanged.connect(auto_complete_files)

    def accept(self) -> None:
        crdb_path = self.crdb_file_input.filePath()
        rw5_path = self.rw5_file_input.filePath()

        # validate requried fields.
        if not all([crdb_path, rw5_path]):
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText("Missing required information.")
            msg.setInformativeText("You forgot to enter one or more required fields (CRDB, RW5 file).")
            msg.setWindowTitle("Not so fast...")
            msg.exec()
            return None

        return super().accept()
