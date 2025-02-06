import base64
import datetime
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Any

import jinja2
import requests
from qgis.core import QgsFeature, QgsMessageLog
from qgis.gui import QgisInterface
from qgis.utils import iface as _iface

iface: QgisInterface = _iface  # type: ignore

from fieldworkimport.helpers import BASE_DIR, get_layers_by_table_name, nullish

if TYPE_CHECKING:
    from fieldworkimport.plugin import PluginInput

loader = jinja2.FileSystemLoader(f"{BASE_DIR!s}/resources/templates")
env = jinja2.Environment(autoescape=True, loader=loader)


def feature_attribute_filter(input: QgsFeature, attr: str):
    return input.attribute(attr)


def try_safe_round(val: Any, prec: int):
    if nullish(val):
        return ""
    return round(val, prec)


def image_url_to_base64(url: str):
    request = requests.get(url)
    ct = request.headers.get("content-type") or request.headers.get("Content-Type") or "image/png"
    return f"data:{ct};base64," + str(base64.b64encode(request.content))[2:-1]


env.filters["nullish"] = nullish
env.filters["attr"] = feature_attribute_filter
env.filters["safe_round"] = try_safe_round

env.globals["downloadB64"] = image_url_to_base64
env.globals["datetime"] = datetime.datetime
env.globals["nullish"] = nullish

report_template = env.get_template("report.jinja")


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
    fieldworkshot_layer = get_layers_by_table_name("public", "sites_fieldworkshot", raise_exception=True, no_filter=True, require_geom=True)[0]
    fieldrun_layer = get_layers_by_table_name("public", "sites_fieldrun", raise_exception=True, no_filter=True)[0]
    fieldrunshot_layer = get_layers_by_table_name("public", "sites_fieldrunshot", raise_exception=True, no_filter=True, require_geom=True)[0]
    fieldrunshotimage_layer = get_layers_by_table_name("public", "sites_fieldrunshotimage", raise_exception=True, no_filter=True)[0]
    controlpointdata_layer = get_layers_by_table_name("public", "sites_controlpointdata", raise_exception=True, no_filter=True)[0]
    fieldwork_id = fieldwork_feature["id"]
    fieldrun_id = fieldwork_feature["field_run_id"]
    fieldrun_feature = None
    if not nullish(fieldrun_id):
        fieldrun_feature = next(fieldrun_layer.getFeatures(f"id = {fieldrun_id}"))
    QgsMessageLog.logMessage(f"REPORT {fieldwork_id}")

    report = {
        "fw": fieldwork_feature,
        "fr": fieldrun_feature,
        "job_number": job_number,
        "client_name": client_name,
        "shots_summary_str": "",
        "final_shots": [],
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
        "crdb_rows": [],
        "rw5_raw": "",
        "sum_raw": "",
        "ref_raw": "",
        "loc_raw": "",
        "header_b64": get_header_image_b64(),
        "DETAILED_REPORT": plugin_input is not None,
    }

    all_fieldworkshots: list[QgsFeature] = [*fieldworkshot_layer.getFeatures(f"fieldwork_id = '{fieldwork_id}'")]  # type: ignore
    fieldworkshot_ids = [f["id"] for f in all_fieldworkshots]

    top_level_shots = []
    top_level_shot_names = []
    new_control_names = []
    observed_control_names = []

    # build map of children by parent_id
    QgsMessageLog.logMessage("build map of children by parent_id")
    child_by_parent_id: dict[str, list[QgsFeature]] = {}
    for fw_shot in all_fieldworkshots:
        QgsMessageLog.logMessage(f"- {fw_shot['name']}")
        parent_point_id = fw_shot["parent_point_id"]
        if not nullish(parent_point_id):
            if parent_point_id not in child_by_parent_id:
                child_by_parent_id[parent_point_id] = []
            child_by_parent_id[parent_point_id].append(fw_shot)

    # iterate over all top-level fieldwork shots to build out report
    QgsMessageLog.logMessage("iterate over all top-level fieldwork shots to build out report")
    for fw_shot in all_fieldworkshots:
        fw_shot_id = fw_shot["id"]
        parent_point_id = fw_shot["parent_point_id"]
        # get all top level shots w.r.t. this fieldwork
        # meaning its a top level shot if the parent point isn't set or isn't from this fieldwork
        if parent_point_id in fieldworkshot_ids:
            continue

        name = fw_shot["name"]
        matching_fieldrun_shot_id = fw_shot["matching_fieldrun_shot_id"]

        # build out top level shots (a.k.a. final shots) section of report
        top_level_shots.append(fw_shot)
        top_level_shot_names.append(name)

        if fw_shot_id in child_by_parent_id:
            report["averaged_shots"].append({
                "parent_shot": fw_shot,
                "child_shots": child_by_parent_id[fw_shot_id],
            })

        if nullish(matching_fieldrun_shot_id):
            continue
        matching_fr_shot = next(fieldrunshot_layer.getFeatures(f"id = '{matching_fieldrun_shot_id}'"))
        fr_shot_name = matching_fr_shot["name"]

        # build out control point section
        controlpointdata = next(controlpointdata_layer.getFeatures(f"fieldrun_shot_id = '{matching_fieldrun_shot_id}'"), None)
        if controlpointdata is None:
            continue

        published_by_fieldwork_id = controlpointdata["published_by_fieldwork_id"]
        # check if the control point has an easting as a test to see if it's been published yet
        has_been_published = not nullish(controlpointdata["easting"])

        if not has_been_published:
            continue
        # if true, this control is "new", i.e. published in this fieldwork
        if published_by_fieldwork_id == fieldwork_id:
            QgsMessageLog.logMessage("-- published")
            report["new_controls"].append({
                "fw_shot": fw_shot,
                "fr_shot": matching_fr_shot,
                "control_point_data": controlpointdata,
            })
            new_control_names.append(fr_shot_name)
        else:
            QgsMessageLog.logMessage("-- observed")
            report["observed_controls"].append({
                "fw_shot": fw_shot,
                "fr_shot": matching_fr_shot,
                "control_point_data": controlpointdata,
            })
            observed_control_names.append(fr_shot_name)

    # iterate over controls used in shift to build out coordinate shift section
    QgsMessageLog.logMessage("iterate over controls used in shift to build out coordinate shift section")
    shift_control_ids: list[str] = fieldwork_feature["shift_control_ids"].split(",")
    shift_control_ids_cause = ",".join([f"'{i}'" for i in shift_control_ids])
    shift_controls: list[QgsFeature] = [*fieldrunshot_layer.getFeatures(f"id in ({shift_control_ids_cause})")]  # type: ignore
    for shift_control in shift_controls:
        QgsMessageLog.logMessage(f"- {shift_control['name']}")
        shift_control_id = shift_control["id"]
        # build out control point section
        controlpointdata = next(controlpointdata_layer.getFeatures(f"fieldrun_shot_id = '{shift_control_id}'"))

        report["coordinate_shift"]["shift_controls"].append({
            "fr_shot": shift_control,
            "control_point_data": controlpointdata,
        })

    report["shots_summary_str"] = summary_str(top_level_shot_names)
    report["new_controls_summary_str"] = ", ".join(new_control_names)
    report["observed_controls_summary_str"] = ", ".join(observed_control_names)

    if fieldrun_feature:
        # iterate over fieldrun shots to build out fieldrun section
        all_fieldrunshots: list[QgsFeature] = [*fieldrunshot_layer.getFeatures(f"field_run_id = {fieldrun_id}")]  # type: ignore
        for fr_shot in all_fieldrunshots:
            fr_shot_id = fr_shot["id"]
            fr_shot_images: list[QgsFeature] = [*fieldrunshotimage_layer.getFeatures(f"fieldrun_shot_id = '{fr_shot_id}'")]  # type: ignore # noqa: E501
            report["fieldrun_shots"].append({
                "shot": fr_shot,
                "images": fr_shot_images,
            })

    report["final_shots"] = top_level_shots

    # build out detailed report stuff (raw data)
    if plugin_input:
        report["crdb_name"] = Path(plugin_input.crdb_path).name
        crdb_connection = sqlite3.connect(plugin_input.crdb_path)
        crdb_connection.row_factory = sqlite3.Row
        cursor = crdb_connection.cursor()
        crdb_query = cursor.execute("SELECT * FROM Coordinates")
        crdb_rows = crdb_query.fetchall()
        report["crdb_rows"] = crdb_rows

        report["rw5_name"] = Path(plugin_input.rw5_path).name
        report["rw5_raw"] = Path(plugin_input.rw5_path).read_text(encoding="iso-8859-1")
        if plugin_input.ref_path:
            report["ref_name"] = Path(plugin_input.ref_path).name
            report["ref_raw"] = Path(plugin_input.ref_path).read_text(encoding="utf-8")
        if plugin_input.loc_path:
            report["loc_name"] = Path(plugin_input.loc_path).name
            report["loc_raw"] = Path(plugin_input.loc_path).read_text(encoding="utf-8")
        if plugin_input.sum_path:
            report["sum_name"] = Path(plugin_input.sum_path).name
            report["sum_raw"] = Path(plugin_input.sum_path).read_text(encoding="utf-8")

    return report


def create_report(variables: dict):
    report_template = env.get_template("report.jinja")
    return report_template.render(**variables)
