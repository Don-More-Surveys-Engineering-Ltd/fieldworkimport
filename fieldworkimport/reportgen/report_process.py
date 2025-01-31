import base64
import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import jinja2
from qgis.core import QgsFeature, QgsMapRendererCustomPainterJob, QgsMapSettings, QgsMessageLog, QgsProject
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QBuffer, QByteArray, QIODevice, QSize
from qgis.PyQt.QtGui import QImage, QPainter
from qgis.utils import iface as _iface

iface: QgisInterface = _iface  # type: ignore

from fieldworkimport.helpers import BASE_DIR, get_layers_by_table_name, not_NULL

if TYPE_CHECKING:
    from fieldworkimport.plugin import PluginInput

loader = jinja2.FileSystemLoader(f"{BASE_DIR!s}/resources/templates")
env = jinja2.Environment(autoescape=True, loader=loader)
report_template = env.get_template("report.jinja")


def feature_attribute_filter(env, input: QgsFeature, attr: str):
    return input.attribute(attr)


def image_url_to_base64(url: str):
    return "BASE64"


def nullish(val):
    return not not_NULL(val)


env.filters["nullish"] = nullish
env.filters["attr"] = feature_attribute_filter
env.filters["url2b64"] = image_url_to_base64

env.globals["datetime"] = datetime.datetime
env.globals["nullish"] = nullish


def get_map_img_b64(fieldwork_id: str):
    fieldworkshot_layer = get_layers_by_table_name("public", "sites_fieldworkshot", raise_exception=True, no_filter=True)[0]
    fieldworkshot_layer.selectByExpression(f"fieldwork_id = '{fieldwork_id}'")
    map_canvas = iface.mapCanvas()
    if not map_canvas:
        return None
    map_canvas.zoomToSelected(fieldworkshot_layer)

    img = QImage(QSize(1024, 1024), QImage.Format_ARGB32_Premultiplied)
    img.setDotsPerMeterX(1)
    img.setDotsPerMeterY(1)

    # create map settings
    ms = QgsMapSettings()

    # create painter
    p = QPainter()
    p.begin(img)
    p.setRenderHint(QPainter.Antialiasing)

    # set layers to render
    project = QgsProject.instance()
    assert project
    layers = map_canvas.layers()
    ms.setLayers(layers)

    # set extent
    rect = map_canvas.extent()
    rect.scale(1.1)
    ms.setExtent(rect)

    # set ouptut size
    ms.setOutputSize(img.size())

    # setup qgis map renderer
    render = QgsMapRendererCustomPainterJob(ms, p)
    render.start()
    render.waitForFinished()
    p.end()

    byte_array = QByteArray()
    buffer = QBuffer(byte_array)
    buffer.open(QIODevice.WriteOnly)
    img.save(buffer, "PNG")
    return byte_array


def get_header_image_b64():
    with Path(BASE_DIR / "resources" / "images" / "header.png").open("rb") as fptr:
        b = fptr.read()
        return "data:image/png;base64," + str(base64.b64encode(b))[2:-1]


def summary_str(names: list[str]):
    sorted_names = sorted(set(names))
    n = len(sorted_names)
    if n == 0:
        return "N/A"
    if n == 1:
        return sorted_names[0]
    return f"{sorted_names[0]} - {sorted_names[-1]}"


def get_report_variables(fieldwork_feature: QgsFeature, plugin_input: "PluginInput | None", job_number: str, client_name: str):
    fieldwork_layer = get_layers_by_table_name("public", "sites_fieldwork", raise_exception=True, no_filter=True)[0]
    fieldworkshot_layer = get_layers_by_table_name("public", "sites_fieldworkshot", raise_exception=True, no_filter=True)[0]
    fieldrun_layer = get_layers_by_table_name("public", "sites_fieldrun", raise_exception=True, no_filter=True)[0]
    fieldrunshot_layer = get_layers_by_table_name("public", "sites_fieldrunshot", raise_exception=True, no_filter=True)[0]
    fieldrunshotimage_layer = get_layers_by_table_name("public", "sites_fieldrunshotimage", raise_exception=True, no_filter=True)[0]
    controlpointdata_layer = get_layers_by_table_name("public", "sites_controlpointdata", raise_exception=True, no_filter=True)[0]
    controlpointcoordinate_layer = get_layers_by_table_name("public", "sites_controlpointcoordinate", raise_exception=True, no_filter=True)[0]
    controlpointelevation_layer = get_layers_by_table_name("public", "sites_controlpointelevation", raise_exception=True, no_filter=True)[0]
    fieldwork_id = fieldwork_feature.attribute("id")
    fieldrun_id = fieldwork_feature.attribute("field_run_id")
    fieldrun_feature = None
    if not_NULL(fieldrun_id):
        fieldrun_feature = next(fieldrun_layer.getFeatures(f"id = {fieldrun_id}"))
    QgsMessageLog.logMessage(f"REPORT {fieldwork_id}")

    report = {
        "plugin_input": plugin_input,
        "fw": fieldwork_feature,
        "fr": fieldrun_feature,
        "job_number": job_number,
        "client_name": client_name,
        "shots_summary_str": "",
        "observed_controls_summary_str": "",
        "new_controls_summary_str": "",
        "coordinate_shift": {
            "shift_controls": [],
        },
        "observed_controls": [],
        "new_controls": [],
        "averaged_shots": [],
        "fieldrun_shots": [],
        "crdb_name": "",
        "rw5_name": "",
        "sum_name": "",
        "ref_name": "",
        "loc_name": "",
        "crdb_data": [],
        "rw5_raw": "",
        "sum_raw": "",
        "ref_raw": "",
        "loc_raw": "",
        "map_img_b64": "",
        "header_b64": get_header_image_b64(),
        "DETAILED_REPORT": plugin_input is not None,
    }

    all_fieldworkshots: list[QgsFeature] = [*fieldworkshot_layer.getFeatures(f"fieldwork_id = '{fieldwork_id}'")]  # type: ignore
    fieldworkshot_ids = [f.attribute("id") for f in all_fieldworkshots]

    top_level_shot_names = []
    new_control_names = []
    observed_control_names = []

    # build map of children by parent_id
    QgsMessageLog.logMessage("build map of children by parent_id")
    child_by_parent_id: dict[str, list[QgsFeature]] = {}
    for fw_shot in all_fieldworkshots:
        QgsMessageLog.logMessage(f"- {fw_shot.attribute('name')}")
        parent_point_id = fw_shot.attribute("parent_point_id")
        if not_NULL(parent_point_id):
            if parent_point_id not in child_by_parent_id:
                child_by_parent_id[parent_point_id] = []
            child_by_parent_id[parent_point_id].append(fw_shot)

    # iterate over all top-level fieldwork shots to build out report
    QgsMessageLog.logMessage("iterate over all top-level fieldwork shots to build out report")
    for fw_shot in all_fieldworkshots:
        shot_id = fw_shot.attribute("id")
        parent_point_id = fw_shot.attribute("parent_point_id")
        # get all top level shots w.r.t. this fieldwork
        # meaning its a top level shot if the parent point isn't set or isn't from this fieldwork
        if parent_point_id in fieldworkshot_ids:
            continue
        QgsMessageLog.logMessage(f"- {fw_shot.attribute('name')}")
        name = fw_shot.attribute("name")
        matching_fieldrun_shot_id = fw_shot.attribute("matching_fieldrun_shot_id")
        QgsMessageLog.logMessage(f"-- {parent_point_id=}")
        QgsMessageLog.logMessage(f"-- {matching_fieldrun_shot_id=}")

        top_level_shot_names.append(name)

        if shot_id in child_by_parent_id:
            report["averaged_shots"].append({
                "parent_shot": fw_shot,
                "child_shots": child_by_parent_id[shot_id],
            })

        if not not_NULL(matching_fieldrun_shot_id):
            continue
        matching_fr_shot = next(fieldrunshot_layer.getFeatures(f"id = '{matching_fieldrun_shot_id}'"))
        fr_shot_name = matching_fr_shot.attribute("name")

        # build out control point section
        controlpointdata = next(controlpointdata_layer.getFeatures(f"fieldrun_shot_id = '{matching_fieldrun_shot_id}'"), None)
        if controlpointdata is None:
            continue

        published_by_fieldwork_id = controlpointdata.attribute("published_by_fieldwork_id")
        primary_coord_id = controlpointdata.attribute("primary_coord_id")
        primary_elevation_id = controlpointdata.attribute("primary_elevation_id")
        primary_coord = None
        primary_elevation = None
        if not_NULL(primary_coord_id):
            primary_coord = next(controlpointcoordinate_layer.getFeatures(f"id = {primary_coord_id}"))
        if not_NULL(primary_elevation_id):
            primary_elevation = next(controlpointelevation_layer.getFeatures(f"id = {primary_elevation_id}"))

        if not primary_coord:
            continue
        # if true, this control is "new", i.e. published in this fieldwork
        if published_by_fieldwork_id == fieldwork_id:
            QgsMessageLog.logMessage("-- published")
            report["new_controls"].append({
                "fw_shot": fw_shot,
                "fr_shot": matching_fr_shot,
                "control_point_data": controlpointdata,
                "primary_coord": primary_coord,
                "primary_eleavtion": primary_elevation,
            })
            new_control_names.append(fr_shot_name)
        else:
            QgsMessageLog.logMessage("-- observed")
            report["observed_controls"].append({
                "fw_shot": fw_shot,
                "fr_shot": matching_fr_shot,
                "control_point_data": controlpointdata,
                "primary_coord": primary_coord,
                "primary_eleavtion": primary_elevation,
            })
            observed_control_names.append(fr_shot_name)

    # iterate over controls used in shift to build out coordinate shift section
    QgsMessageLog.logMessage("iterate over controls used in shift to build out coordinate shift section")
    shift_control_ids: list[str] = fieldwork_feature.attribute("shift_control_ids").split(",")
    shift_control_ids_cause = ",".join([f"'{i}'" for i in shift_control_ids])
    shift_controls: list[QgsFeature] = [*fieldrunshot_layer.getFeatures(f"id in ({shift_control_ids_cause})")]  # type: ignore
    for shift_control in shift_controls:
        QgsMessageLog.logMessage(f"- {shift_control.attribute('name')}")
        shift_control_id = shift_control.attribute("id")
        # build out control point section
        controlpointdata = next(controlpointdata_layer.getFeatures(f"fieldrun_shot_id = '{shift_control_id}'"))
        primary_coord_id = controlpointdata.attribute("primary_coord_id")
        primary_elevation_id = controlpointdata.attribute("primary_elevation_id")
        primary_elevation = None
        primary_coord = next(controlpointcoordinate_layer.getFeatures(f"id = {primary_coord_id}"))
        if not_NULL(primary_elevation_id):
            primary_elevation = next(controlpointelevation_layer.getFeatures(f"id = {primary_elevation_id}"))

        report["coordinate_shift"]["shift_controls"].append({
            "fr_shot": shift_control,
            "control_point_data": controlpointdata,
            "primary_coord": primary_coord,
            "primary_eleavtion": primary_elevation,
        })

    report["shots_summary_str"] = summary_str(top_level_shot_names)
    report["new_controls_summary_str"] = ", ".join(new_control_names)
    report["observed_controls_summary_str"] = ", ".join(observed_control_names)

    if fieldrun_feature:
        # iterate over fieldrun shots to build out fieldrun section
        all_fieldrun_shots: list[QgsFeature] = [*fieldrunshot_layer.getFeatures(f"field_run_id = {fieldrun_id}")]  # type: ignore
        for fr_shot in all_fieldrun_shots:
            fr_shot_id = fr_shot.attribute("id")
            fr_shot_images: list[QgsFeature] = [*fieldrunshotimage_layer.getFeatures(f"fieldrun_shot_id = '{fr_shot_id}'")]  # type: ignore # noqa: E501
            report["fieldrun_shots"].append({
                "shot": fr_shot,
                "images": fr_shot_images,
            })

    # TODO: not working
    report["map_img_b64"] = get_map_img_b64(fieldwork_id)

    return report


def create_report(variables: dict):
    report_template = env.get_template("report.jinja")
    return report_template.render(**variables)
