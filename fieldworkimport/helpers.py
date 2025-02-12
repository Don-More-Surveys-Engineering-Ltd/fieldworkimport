from contextlib import contextmanager
from pathlib import Path
from time import gmtime, strftime
from timeit import default_timer as timer
from typing import Any

from qgis.core import (
    NULL,
    QgsApplication,
    QgsMessageLog,
    QgsProject,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QProgressBar, QProgressDialog

BASE_DIR = Path(__file__).parent


def nullish(val: Any) -> bool:  # noqa: ANN401, D103
    return (val is None or val == NULL)


def get_layers_by_table_name(
    schema: str,
    table_name: str,
    *,
    no_filter: bool = False,
    require_geom: bool = False,
    raise_exception: bool = False,
) -> list[QgsVectorLayer]:
    layers_dict: dict[str, QgsVectorLayer] = QgsProject.instance().mapLayers()  # type: ignore
    layers_list = layers_dict.values()

    matches = []

    src_table_snippet = f'table="{schema}"."{table_name}"'
    src_layername_snippet = f"layername={table_name}"

    for layer in layers_list:
        if no_filter and layer.subsetString():
            continue
        src_str = layer.source()
        if src_str.endswith(src_layername_snippet):
            # only matches for geopackage layers, helpful for testing
            matches.append(layer)
            continue
        if require_geom and "(geom)" not in src_str:
            continue
        if src_table_snippet in src_str:
            matches.append(layer)

    if not matches and raise_exception:
        msg = f"Could not find layer with table '{schema}'.'{table_name}'."
        raise ValueError(msg)
    return matches


@contextmanager
def timed(name: str):
    start = timer()
    yield
    end = timer()
    QgsMessageLog.logMessage(f"{name}: {(end - start):.2f}s")


@contextmanager
def progress_dialog(text: str):
    dialog = QProgressDialog()
    dialog.setWindowModality(Qt.WindowModal)
    dialog.setWindowTitle("Progress")
    dialog.setLabelText(text)
    dialog.setCancelButton(None)
    bar = QProgressBar(dialog)
    dialog.setBar(bar)

    start = timer()

    def set_progress(p: int) -> None:
        t = timer() - start
        hms = strftime("%H:%M:%S", gmtime(t))
        bar.setFormat(f"{hms} - %p%")
        bar.setValue(p)
        QgsApplication.processEvents()

    bar.setMinimum(0)
    bar.setMaximum(100)
    bar.setTextVisible(True)
    set_progress(0)

    dialog.show()
    QgsApplication.processEvents()

    yield set_progress

    dialog.done(0)


def assert_true(val: bool, fail_msg: str):
    if not val:
        raise ValueError(fail_msg)


def settings_key(short_name: str):
    return f"fieldwork/{short_name}"
