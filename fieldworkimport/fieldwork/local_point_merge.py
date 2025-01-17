"""Functions for performing a local point merge on fieldwork data."""

import math
from collections.abc import Generator, Iterable, Sequence
from typing import Any, Callable, Optional, TypeVar

from qgis.core import QgsFeature, QgsFeatureRequest

from fieldworkimport.fieldwork.helpers import ImportStageReturn, ReturnCode, get_layers_by_table_name
from fieldworkimport.ui.same_point_shots_dialog import SamePointShotsDialog

_GC_T = TypeVar("_GC_T")


def should_be_averaged_together(
    p1: QgsFeature,
    p2: QgsFeature,
    same_point_tolerance: float,
    control_point_codes: list[str],
) -> bool:
    """Return True if the two coords belong in an averaging group together."""  # noqa: DOC201
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
    if p1_code in control_point_codes:
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

    if distance > same_point_tolerance:  # noqa: SIM103
        return False
    return True


def _group_consecutively(iterable: Iterable[_GC_T], comparator: Callable[[_GC_T, _GC_T], bool]) -> Generator[list[_GC_T], Any, None]:  # noqa: E501
    pval: Optional[_GC_T] = None  # noqa: FA100
    group: list[_GC_T] = []
    for val in iterable:
        is_same_group = pval is None or comparator(val, pval)

        if pval is not None and not is_same_group and len(group) > 0:
            yield group
            group = []
        else:
            group.append(val)

        pval = val

    yield group


def find_groups_of_same_shots(
    points: Sequence[QgsFeature],
    same_point_tolerance: float,
    control_point_codes: list[str],
) -> list[list[QgsFeature]]:
    def is_same_group(p1: QgsFeature, p2: QgsFeature) -> bool:
        return should_be_averaged_together(
            p1,
            p2,
            same_point_tolerance=same_point_tolerance,
            control_point_codes=control_point_codes,
        )

    # Consecutive
    return [group for group in _group_consecutively(points, is_same_group) if len(group) > 1]


def local_point_merge(
    fieldwork_id: int,
    same_point_tolerance: float,
    control_point_codes: list[str],
) -> ImportStageReturn:
    fieldworkshots_layer = get_layers_by_table_name("public", "sites_fieldworkshot", no_filter=True, raise_exception=True)[0]  # noqa: E501

    points = [
        *fieldworkshots_layer.getFeatures(
            QgsFeatureRequest()
            .setFilterExpression(f"\"fieldwork_id\" = '{fieldwork_id}'")
            .addOrderBy("name", ascending=True),
        ),
    ]

    groups = find_groups_of_same_shots(
        points,
        same_point_tolerance=same_point_tolerance,
        control_point_codes=control_point_codes,
    )

    dialog = SamePointShotsDialog(same_point_tolerance=same_point_tolerance, groups=groups)
    return_code = dialog.exec_()
    if return_code == dialog.Rejected:
        return (ReturnCode.ABORT, {})

    return (ReturnCode.CONTINUE, {})
