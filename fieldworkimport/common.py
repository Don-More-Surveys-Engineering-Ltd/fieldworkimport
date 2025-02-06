import string
from typing import Optional
from uuid import uuid4

from qgis.core import QgsFeature, QgsSettings, QgsVectorLayer

from fieldworkimport.helpers import settings_key


def _validate_single_code(
    code: str,
    previous_code: Optional[str],
    valid_codes: list[str],
    valid_special_characters: list[str],
    parameterized_special_characters: list[str],
) -> bool:
    """Validate a single code.

    :param code: Description
    :type code: str
    :param previous_code: Description
    :type previous_code:
    :param valid_codes: Description
    :type valid_codes:
    :param valid_code_special_characters: Description
    :type valid_code_special_characters:
    """
    # Special characters can appear after a code or another special character
    if code.upper() in valid_special_characters and previous_code is not None:
        return True
    # If the previous code was a special character that is "parameterized" meaning
    # it can take paramteters like "V 0.15" where 0.15 is the param,
    # check if this code is a number. If so, it's valid.
    if previous_code and previous_code.upper() in parameterized_special_characters:
        try:
            float(code)
        except ValueError:
            pass
        else:
            return True

    # Codes need to start with a known prefix
    prefix = None
    for curr_code in valid_codes:
        # want to prevent matching on 'WV' if code is 'WVMH'
        # find best match (best match is probably the longest)
        if code.upper().startswith(curr_code) and (prefix is None or len(prefix) < len(curr_code)):
            prefix = curr_code

    if prefix is None:
        return False

    # They may have a string starting with a number appended to the end of them, like '3B4AZ'
    suffix = code.removeprefix(prefix)
    # If there is a suffix and it doesn't start with a number, it's invalid. Otherwise, it is a valid code.
    return len(suffix) == 0 or suffix[0].isdigit()


def validate_code(
    mutlicode: str,
    valid_codes: list[str],
    valid_special_characters: list[str],
    parameterized_special_characters: list[str],
) -> bool:
    """Validate a fieldwork process point code/multicode string.

    :param mutlicode: Description
    :type mutlicode: str
    :param valid_codes: Description
    :type valid_codes:
    :param valid_code_special_characters: Description
    :type valid_code_special_characters:
    """
    # split multi code into individual codes
    codes = mutlicode.strip().upper().split(" ")

    # return true if all single codes are valid
    previous_code: Optional[str] = None

    for code in codes:
        if not _validate_single_code(
            code,
            previous_code,
            valid_codes,
            valid_special_characters,
            parameterized_special_characters,
        ):
            return False
        previous_code = code

    return True


def validate_point(
        point: QgsFeature,
        hrms_tolerance: float,
        vrms_tolerance: float,
        valid_codes: list[str],
        valid_special_characters: list[str],
        parameterized_special_characters: list[str],
    ) -> bool:
    hrms: float = point["HRMS"]
    vrms: float = point["VRMS"]
    code: str = point["code"]
    status: Optional[str] = point["status"]
    invalid = False

    if hrms > hrms_tolerance:
        point.setAttribute("bad_hrms_flag", True)
        invalid = True
    if vrms > vrms_tolerance:
        point.setAttribute("bad_vrms_flag", True)
        invalid = True
    if status and "fixed" not in status.lower():
        point.setAttribute("bad_fixed_status_flag", True)
        invalid = True

    code_valid = validate_code(
        code,
        valid_codes=valid_codes,
        valid_special_characters=valid_special_characters,
        parameterized_special_characters=parameterized_special_characters,
    )
    if not code_valid:
        point.setAttribute("bad_code_flag", True)
        invalid = True
    return not invalid


def parent_point_name(child_name: str):
    if child_name[-1] not in string.ascii_letters:
        return child_name + "A"
    if child_name[-1] == "Z":
        return child_name + "A"
    return child_name[:-1] + chr(ord(child_name[-1]) + 1)


def get_average_point(fieldworkshot_layer: QgsVectorLayer, points: list[QgsFeature]) -> QgsFeature:  # noqa: D103, PLR0914
    n = len(points)

    f = QgsFeature(points[0])
    fields = fieldworkshot_layer.fields()
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

    s = QgsSettings()

    validate_point(
        f,
        float(s.value(settings_key("hrms_tolerance"), 0)),
        float(s.value(settings_key("vrms_tolerance"), 0)),
        s.value(settings_key("valid_codes"), "").split(","),
        s.value(settings_key("valid_special_chars"), "").split(","),
        s.value(settings_key("parameterized_special_chars"), "").split(","),
    )

    return f


def calc_parent_child_residuals(parent_point: QgsFeature, child_point: QgsFeature):
    parent_point_northing = parent_point["northing"]
    parent_point_easting = parent_point["easting"]
    parent_point_elevation = parent_point["elevation"]
    child_point_northing = child_point["northing"]
    child_point_easting = child_point["easting"]
    child_point_elevation = child_point["elevation"]

    return (
        parent_point_easting - child_point_easting,
        parent_point_northing - child_point_northing,
        parent_point_elevation - child_point_elevation,
    )
