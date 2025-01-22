from pathlib import Path
from typing import Optional, TypedDict
from xml.etree import ElementTree

from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsPoint, QgsProject


class ParseLOCResult(TypedDict):
    """Result from parsing LOC file."""

    measured_point: tuple[float, float, float]
    """Point that rover measured."""
    grid_point: Optional[tuple[float, float, float]]
    """Point that we know that the rover is actually at. Only returned if geoid seperation is passed."""
    description: str


def parse_loc_file(path: Path, geoid_seperation: Optional[float]) -> ParseLOCResult:
    """Parse coordinate from loc file.

    Geoid seperation is used to convert local z from orthometric to ellipsoidal. If it isn't passed,
    the grid point will not be returned

    Example contents:
    ``` xml
    <?xml version="1.0" encoding="us-ascii" ?>
    <carlson_xml version="1.0">
    <table>
    <record id="Localization Points" >
    <record id="Point 1" >
    <value name="Lat" value="45.3852386147312"></value>
    <value name="Lon" value="-65.8200557130003"></value>
    <value name="Ellipsoid_Elv" value="86.095055029296887"></value>
    <value name="Geoid_Separation" value="0"></value>
    <value name="Local_X" value="2553249.73"></value>
    <value name="Local_Y" value="7376327.1299999999"></value>
    <value name="Local_Z" value="0"></value>
    <value name="HRMS" value="0.0058425730094313622"></value>
    <value name="VRMS" value="0.0096671702340245247"></value>
    <value name="Use_Horizontal" value="Yes"></value>
    <value name="Use_Vertical" value="Yes"></value>
    <value name="Description" value="1380HPN"></value>
    </record>
    <value name="Units" value="WGS84, Decimal Degrees, Metric"></value>
    </record>
    </table>
    </carlson_xml>

    ```
    """
    document = ElementTree.fromstring(path.read_text())
    point_1_record = document.find(".//record[@id='Point 1']")
    if point_1_record is None:
        msg = "No record with id 'Point 1'."
        raise ValueError(msg)
    lat = float(point_1_record.findall("./value[@name='Lat']")[0].get("value", ""))
    lon = float(point_1_record.findall("./value[@name='Lon']")[0].get("value", ""))
    ellipsoid_elv = float(point_1_record.findall("./value[@name='Ellipsoid_Elv']")[0].get("value", ""))
    srcCrs = QgsCoordinateReferenceSystem(4617)
    dstCrs = QgsCoordinateReferenceSystem(2953)
    transform = QgsCoordinateTransform(srcCrs, dstCrs, QgsProject.instance())

    point = QgsPoint(x=lon, y=lat, z=ellipsoid_elv)
    point.transform(transform)
    measured_point = (point.x(), point.y(), point.z())

    grid_point = None
    if geoid_seperation:
        local_x = float(point_1_record.findall("./value[@name='Local_X']")[0].get("value", ""))
        local_y = float(point_1_record.findall("./value[@name='Local_Y']")[0].get("value", ""))
        local_z = float(point_1_record.findall("./value[@name='Local_Z']")[0].get("value", ""))
        local_z_ellipsoidal = local_z - geoid_seperation
        """Local Z plus geoid seperation to convert to ellipsoidal elv from orthometric elv."""
        grid_point = (local_x, local_y, local_z_ellipsoidal)

    description = point_1_record.findall("./value[@name='Description']")[0].get("value", "")

    return {
        "measured_point": measured_point,
        "grid_point": grid_point,
        "description": description,
    }
