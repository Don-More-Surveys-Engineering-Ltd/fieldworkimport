from enum import Enum
from typing import Any

from qgis.core import QgsProject, QgsVectorLayer


def get_layers_by_table_name(schema: str, table_name: str, *, no_filter: bool = False, raise_exception: bool = False) -> list[QgsVectorLayer]:
    layers_dict: dict[str, QgsVectorLayer] = QgsProject.instance().mapLayers()
    layers_list = layers_dict.values()

    matches = []

    src_snippet = f'table="{schema}"."{table_name}"'

    for layer in layers_list:
        if no_filter and layer.subsetString():
            continue
        src_str = layer.source()
        if src_snippet in src_str:
            matches.append(layer)

    if not matches and raise_exception:
        msg = f"Could not find layer with table '{schema}'.'{table_name}'."
        raise ValueError(msg)
    return matches


class ReturnCode(Enum):  # noqa: D101
    CONTINUE = 0
    ABORT = 1


ImportStageReturn = tuple[ReturnCode, dict[str, Any]]
