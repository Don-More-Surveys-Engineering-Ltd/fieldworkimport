"""Functions for performing a local point merge on fieldwork data."""

import math
from collections.abc import Generator, Iterable, Sequence
from typing import TYPE_CHECKING, Any, Callable, Optional, TypeVar

from qgis.core import QgsFeature, QgsFeatureRequest, QgsMessageLog, QgsVectorLayer

from fieldworkimport.exceptions import AbortError
from fieldworkimport.fwimport.merge_helpers import get_average_point
from fieldworkimport.ui.same_point_shots_dialog import SamePointShotsDialog

if TYPE_CHECKING:
    from fieldworkimport.plugin import PluginInput


_GC_T = TypeVar("_GC_T")


def should_be_averaged_together(
    p1: QgsFeature,
    p2: QgsFeature,
    plugin_input: "PluginInput",
) -> bool:
    """Return True if the two coords belong in an averaging group together."""  # noqa: DOC201
    # QgsMessageLog.logMessage(f"CMP: {p1.attribute('name')} -> {p2.attribute('name')}")

    p1_code = p1.attribute("code")
    p2_code = p2.attribute("code")
    p1_parent_point_id = p1.attribute("parent_point_id")
    p2_parent_point_id = p2.attribute("parent_point_id")
    p1_easting = p1.attribute("easting")
    p2_easting = p2.attribute("easting")
    p1_northing = p1.attribute("northing")
    p2_northing = p2.attribute("northing")

    # If already averaged (the user went back?) skip
    if p1_parent_point_id or p2_parent_point_id:

        return False

    # Same code
    if p1_code != p2_code:
        return False

    # Within tolerance
    if p1_code in plugin_input.control_point_codes:
        p1_elevation = p1.attribute("elevation")
        p2_elevation = p2.attribute("elevation")
        # factor elevation into distance calc if control point for 3d calculations
        distance = math.sqrt(
            (p2_easting - p1_easting) ** 2
            + (p2_northing - p1_northing) ** 2
            + (p2_elevation - p1_elevation) ** 2,
        )
    else:
        # if not control point, just use 2d calculations
        distance = math.sqrt((p2_easting - p1_easting) ** 2 + (p2_northing - p1_northing) ** 2)

    return not distance > plugin_input.same_point_tolerance


def _group_consecutively(iterable: Iterable[_GC_T], comparator: Callable[[_GC_T, _GC_T], bool]) -> Generator[list[_GC_T], Any, None]:  # noqa: E501
    pval: Optional[_GC_T] = None  # noqa: FA100
    group: list[_GC_T] = []
    for val in iterable:
        is_same_group = pval is None or comparator(val, pval)

        if pval is not None and not is_same_group and len(group) > 0:
            yield group
            group = [val]
        else:
            group.append(val)

        pval = val

    yield group


def find_groups_of_same_shots(
    points: Sequence[QgsFeature],
    plugin_input: "PluginInput",
) -> list[list[QgsFeature]]:
    def is_same_group(p1: QgsFeature, p2: QgsFeature) -> bool:
        return should_be_averaged_together(
            p1,
            p2,
            plugin_input,
        )

    # Consecutive
    return [group for group in _group_consecutively(points, is_same_group) if len(group) > 1]


def create_averaged_point(
    fieldworkshot_layer: QgsVectorLayer,
    group: list[QgsFeature],
    plugin_input: "PluginInput",
):
    fields = fieldworkshot_layer.fields()
    parent_point_id_index = fields.indexFromName("parent_point_id")

    # get avg point of group
    avg_point = get_average_point(fieldworkshot_layer, group, plugin_input)
    avg_point_id = avg_point.attribute("id")

    # add avg point to layer
    fieldworkshot_layer.addFeature(avg_point)

    # parent each child point with avg point
    for point in group:
        point[parent_point_id_index] = avg_point_id
        # update feature on layer
        fieldworkshot_layer.updateFeature(point)


def local_point_merge(
    fieldworkshot_layer: QgsVectorLayer,
    fieldwork_id: int,
    plugin_input: "PluginInput",
):
    QgsMessageLog.logMessage(
        "Local point merge started.",
    )
    points: list[QgsFeature] = [
        *fieldworkshot_layer.getFeatures(
            QgsFeatureRequest()
            .setFilterExpression(f"\"fieldwork_id\" = '{fieldwork_id}'")
            .addOrderBy("name", ascending=True),
        ),  # type: ignore
    ]

    groups = find_groups_of_same_shots(
        points,
        plugin_input,
    )

    dialog = SamePointShotsDialog(fieldworkshot_layer, groups=groups, plugin_input=plugin_input)
    return_code = dialog.exec_()
    if return_code == dialog.Rejected:
        msg = "Aborted during local point merge stage."
        raise AbortError(msg)

    final_groups = dialog.final_groups
    for group in final_groups:
        create_averaged_point(fieldworkshot_layer, group, plugin_input)
