from pathlib import Path

from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsPoint, QgsProject


def parse_ref_file(path: Path) -> tuple[float, float, float]:
    """Parse coordinate from ref file.

    Example contents:
    ``` ref
    VERSION2
    45.38820832600608
    -66.07724327229201
    19.4263717865

    0
    ```
    """
    lines = path.read_text().splitlines()
    x = float(lines[1].strip())
    y = float(lines[2].strip())
    z = float(lines[3].strip())

    srcCrs = QgsCoordinateReferenceSystem(4617)
    dstCrs = QgsCoordinateReferenceSystem(2953)
    transform = QgsCoordinateTransform(srcCrs, dstCrs, QgsProject.instance())

    point = QgsPoint(x=y, y=x, z=z)
    point.transform(transform)

    return (point.x(), point.y(), point.z())
