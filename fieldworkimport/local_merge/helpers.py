import string
from uuid import uuid4

from qgis.core import QgsFeature

from fieldworkimport.helpers import get_layers_by_table_name


def parent_point_name(child_name: str):
    if child_name[-1] not in string.ascii_letters:
        return child_name + "A"
    if child_name[-1] == "Z":
        return child_name + "A"
    return child_name[:-1] + chr(ord(child_name[-1]) + 1)


def get_average_point(points: list[QgsFeature]) -> QgsFeature:  # noqa: D103, PLR0914
    n = len(points)

    layer = get_layers_by_table_name("public", "sites_fieldworkshot", no_filter=True, raise_exception=True)[0]
    f = QgsFeature(points[0])
    fields = layer.fields()
    id_index = fields.indexFromName("id")
    name_index = fields.indexFromName("name")
    northing_index = fields.indexFromName("northing")
    easting_index = fields.indexFromName("easting")
    elevation_index = fields.indexFromName("elevation")
    HRMS_index = fields.indexFromName("HRMS")  # noqa: N806
    VRMS_index = fields.indexFromName("VRMS")  # noqa: N806
    PDOP_index = fields.indexFromName("PDOP")  # noqa: N806
    HDOP_index = fields.indexFromName("HDOP")  # noqa: N806
    VDOP_index = fields.indexFromName("VDOP")  # noqa: N806
    TDOP_index = fields.indexFromName("TDOP")  # noqa: N806
    GDOP_index = fields.indexFromName("GDOP")  # noqa: N806

    n_with_HRMS = len([p for p in points if p[HRMS_index]])  # noqa: N806
    n_with_VRMS = len([p for p in points if p[VRMS_index]])  # noqa: N806
    n_with_PDOP = len([p for p in points if p[PDOP_index]])  # noqa: N806
    n_with_HDOP = len([p for p in points if p[HDOP_index]])  # noqa: N806
    n_with_VDOP = len([p for p in points if p[VDOP_index]])  # noqa: N806
    n_with_TDOP = len([p for p in points if p[TDOP_index]])  # noqa: N806
    n_with_GDOP = len([p for p in points if p[GDOP_index]])  # noqa: N806

    f[id_index] = str(uuid4())
    f[name_index] = parent_point_name(f[name_index])
    f[northing_index] = sum(p[northing_index] for p in points) / n
    f[easting_index] = sum(p[easting_index] for p in points) / n
    f[elevation_index] = sum(p[elevation_index] for p in points) / n
    f[HRMS_index] = sum(p[HRMS_index] for p in points if p[HRMS_index]) / max(n_with_HRMS, 1)
    f[VRMS_index] = sum(p[VRMS_index] for p in points if p[VRMS_index]) / max(n_with_VRMS, 1)
    f[PDOP_index] = sum(p[PDOP_index] for p in points if p[PDOP_index]) / max(n_with_PDOP, 1)
    f[HDOP_index] = sum(p[HDOP_index] for p in points if p[HDOP_index]) / max(n_with_HDOP, 1)
    f[VDOP_index] = sum(p[VDOP_index] for p in points if p[VDOP_index]) / max(n_with_VDOP, 1)
    f[TDOP_index] = sum(p[TDOP_index] for p in points if p[TDOP_index]) / max(n_with_TDOP, 1)
    f[GDOP_index] = sum(p[GDOP_index] for p in points if p[GDOP_index]) / max(n_with_GDOP, 1)

    return f


def calc_parent_child_residuals(parent_point: QgsFeature, child_point: QgsFeature):
    parent_point_northing = parent_point.attribute("northing")
    parent_point_easting = parent_point.attribute("easting")
    parent_point_elevation = parent_point.attribute("elevation")
    child_point_northing = child_point.attribute("northing")
    child_point_easting = child_point.attribute("easting")
    child_point_elevation = child_point.attribute("elevation")

    return (
        parent_point_northing - child_point_northing,
        parent_point_easting - child_point_easting,
        parent_point_elevation - child_point_elevation,
    )
