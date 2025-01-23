from pathlib import Path
from typing import TypedDict

from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsPoint, QgsProject


class ParseSUMResult(TypedDict):
    """Result of parsing SUM file from NRCAN."""

    point: tuple[float, float, float]
    """True coordiante from NRCAN representing LOC fiel coordinates."""
    orthometric_system: str
    """Used for reporting."""
    orthometric_model: str
    """Used for reporting."""
    geoid_seperation: float
    """Used by LOC file to convert orthometric elevation to ellipsoidal elevation."""


def dms_dd(degrees: float, minutes: float, seconds: float):
    """Convert from DMS to decimal."""
    if degrees >= 0:
        decimal = degrees + minutes / 60.0 + seconds / 3600.0
    else:
        decimal = degrees - minutes / 60.0 - seconds / 3600.0
    return decimal


SUM_FILE_LAT_LON_SRID = 4617
"""SUM file uses NAD83 for lat/lng (as opposed to the global 4326)"""
SUM_FILE_LOCAL_SRID = 2953


def parse_sum_file(path: Path) -> ParseSUMResult:
    """Parse SUM file from NRCAN.

    SUM files hold data that we get back from NRCAN after sending our REF and LOC files to them.
    Holds true coordinate and geoid seperation.
    Relevant section is midway through file.

    Example of relevant section.
    ``` txt
    POS CRD  SYST        EPOCH          A_PRIORI         ESTIMATED       DIFF SIG_PPP(95%) SIG_TOT(95%) CORRELATIONS
    POS   X NAD83 97:001:00000      1876338.3955      1876339.5340     1.1385       0.0066       0.0250   1.0000
    POS   Y NAD83 97:001:00000     -4012676.5744     -4012678.8820    -2.3076       0.0120       0.0209  -0.6666  1.0000
    POS   Z NAD83 97:001:00000      4573630.8987      4573629.9001    -0.9986       0.0134       0.0194   0.6667 -0.8357  1.0000
    POS LAT NAD83 97:001:00000    46  6 29.50207    46  6 29.41960    -2.5463       0.0051       0.0246   1.0000
    POS LON NAD83 97:001:00000   -64 56 20.69708   -64 56 20.69457     0.0539       0.0046       0.0178   0.0351  1.0000
    POS HGT NAD83 97:001:00000           52.0040           53.0679     1.0639       0.0179       0.0228   0.0195 -0.0609  1.0000
    PRJ TYPE ZONE    EASTING     NORTHING   SCALE_POINT   SCALE_COMBINED HEMISPHERE
    PRJ  UTM   20 350146.337  5107894.021    0.99987606       0.99986774          N
    PRJ  MTM    5 270857.022  5107692.431    0.99991416       0.99990584
    OHT     SYST    MODEL             HEIGHT
    OHT   CGVD28    HT2_0            72.5768
    GHT -19.5089
    ```
    """
    text = path.read_text().splitlines()

    lat_line = next(line for line in text if line.startswith("POS LAT"))
    lon_line = next(line for line in text if line.startswith("POS LON"))
    hgt_line = next(line for line in text if line.startswith("POS HGT"))
    oht_line = next(line for line in text if line.startswith("OHT") and "SYST" not in line)
    ght_line = next(line for line in text if line.startswith("GHT"))

    # source of 46 - 64 indices is from @AndrewToole's GPSPPP script
    # it just works? not pretty but it's time-tested
    lat_line_estimated = lat_line[46:64].strip()
    lon_line_estimated = lon_line[46:64].strip()
    hgt_line_estimated = hgt_line[46:64].strip()

    d, m, s = map(float, lat_line_estimated.split())
    lat = dms_dd(d, m, s)
    d, m, s = map(float, lon_line_estimated.split())
    lon = dms_dd(d, m, s)
    hgt = float(hgt_line_estimated)

    oth_line_parts = [p.strip() for p in oht_line.split()]
    orthometric_system = oth_line_parts[1]
    orthometric_model = oth_line_parts[2]

    ght_line_parts = [p.strip() for p in ght_line.split()]
    geoid_seperation = float(ght_line_parts[1])

    srcCrs = QgsCoordinateReferenceSystem(SUM_FILE_LAT_LON_SRID)
    dstCrs = QgsCoordinateReferenceSystem(SUM_FILE_LOCAL_SRID)
    transform = QgsCoordinateTransform(srcCrs, dstCrs, QgsProject.instance())

    point = QgsPoint(x=lon, y=lat)
    point.transform(transform)
    return {
        "point": (point.x(), point.y(), hgt),
        "geoid_seperation": geoid_seperation,
        "orthometric_model": orthometric_model,
        "orthometric_system": orthometric_system,
    }
