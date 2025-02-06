from collections.abc import Generator
from typing import Any

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsMapLayer,
    QgsMessageLog,
    QgsProject,
    QgsSpatialIndex,
    QgsVectorLayer,
)
from qgis.gui import QgisInterface
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.utils import iface as _iface

from fieldworkimport.common import get_average_point, parent_point_name
from fieldworkimport.exceptions import AbortError
from fieldworkimport.helpers import assert_true, nullish, progress_dialog, timed
from fieldworkimport.ui.possible_same_point_shot_dialog import PossibleSamePointShotDialog
from fieldworkimport.ui.recalculate_shot_dialog import RecalculateShotDialog

iface: QgisInterface = _iface  # type: ignore

MAX_SOLVING_ITERATIONS = 20


def is_layer_type(layer: QgsMapLayer, schema: str, table: str):
    src = layer.source()
    src_table_snippet = f'table="{schema}"."{table}"'
    src_layername_snippet = f"layername={table}"

    return bool(src_table_snippet in src or src.endswith(src_layername_snippet))


class FindSamePointShots:
    """Find same point shots, and decide on how to handle them.

    Input is the current selection QGIS (must be a sites_fieldworkshot layer).
    Only those shots will be used for calcuations, including nearest neighbor.

    This process is solved in iterations. This is because the algorithm finds pairs of same point shots,
    and there may be more than two same poitn shots. So once one pair is decided on, we'll recalculate and
    see if there is a second pair.
    """

    layer: QgsVectorLayer
    distance_threshold: float
    do_nothing_ids: set[int]
    """Ids of shots that we chose to do nothing with. We remember this so we don't spam user with same question."""

    def __init__(self, distance_threshold: float = 0.075) -> None:
        layer = iface.activeLayer()
        if layer is None or not is_layer_type(layer, "public", "sites_fieldworkshot") or not isinstance(layer, QgsVectorLayer):
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText("Invalid Layer")
            msg_str = "Please select features from a fieldwork shots layer before running this tool."
            msg.setInformativeText(msg_str)
            msg.setWindowTitle("Invalid Layer")
            msg.exec()
            raise AbortError(msg_str)

        assert isinstance(layer, QgsVectorLayer)
        self.layer = layer
        self.distance_threshold = distance_threshold
        self.do_nothing_ids = set()

    def __get_selection(self) -> list[QgsFeature]:
        features = self.layer.selectedFeatures()
        # filter the selected features further
        return [
            f for f in features
            if nullish(f["parent_point_id"])  # top level points only
        ]

    def __find_same_point_shots(self) -> Generator[tuple[QgsFeature, QgsFeature], Any, None]:
        """Find pairs of same point shots, excluding pairs that we've already decided on in previous iterations."""  # noqa: DOC402
        features = self.__get_selection()

        # get list of codes that were used in selected
        unique_codes = {feature["code"] for feature in features}

        qgsproj = QgsProject.instance()
        assert qgsproj is not None

        # prepare crs transformation so that we can use meters in calculation
        layer_crs = self.layer.crs()
        projected_crs = QgsCoordinateReferenceSystem("EPSG:3857")  # Web Mercator so we can use meters
        transform_to_m = QgsCoordinateTransform(layer_crs, projected_crs, qgsproj.transformContext())

        # keep track of visited neighbors so that we don't try to action them twice in same iteration
        # this is important because, unless the user chooses the do nothing option, the second time we see
        # a shot it has already been actioned (recalced into a new shot and now isn't top level,
        # or possibly parented to another shot) and our data is out of date
        # this is why we run mutliple iterations, so that if we do see a shot twice, we're acting with up to date data
        visited = set()

        # only cluster groups of same-code points
        for curr_code in unique_codes:
            features_of_code: list[QgsFeature] = []
            # setup spatial index for this code type
            spatial_index = QgsSpatialIndex()
            for f in features:
                if f["code"] == curr_code:
                    features_of_code.append(f)
                    spatial_index.addFeature(f)

            # iterate over each feature, and find their nearest neighbours using the spatial index
            # then iterate over the neighbours and decide if they're under the distance threshold
            for feature in features_of_code:
                geom = feature.geometry()
                geom.transform(transform_to_m)
                point = geom.asPoint()

                neighbors = spatial_index.nearestNeighbor(point, 2)
                # iterate over the neighbors
                for neighbor_id in neighbors:
                    neighbor = self.layer.getFeature(neighbor_id)
                    # can't be your own neighbor
                    if feature.id() == neighbor_id:
                        continue
                    # if this pair has been ignored already, don't use (this is so we respect the user's choice and dont spam them)  # noqa: E501
                    if feature["id"] in self.do_nothing_ids and neighbor["id"] in self.do_nothing_ids:
                        continue
                    # if we've already seen this point this iteration, don't use it (as explained above)
                    if neighbor["id"] in visited:
                        continue
                    neighbor_geom = neighbor.geometry()
                    neighbor_geom.transform(transform_to_m)
                    neighbor_point = neighbor_geom.asPoint()

                    # test if within threshold
                    distance = point.distance(neighbor_point)
                    if distance > self.distance_threshold:
                        continue

                    visited.add(neighbor["id"])

                    QgsMessageLog.logMessage(f"{visited=}")
                    yield (feature, neighbor)

                visited.add(feature["id"])

    def __parent_child_to_shot(self, parent: QgsFeature, child: QgsFeature):
        """Sets a shot as the child of a parent shot."""  # noqa: D401
        child["parent_point_id"] = parent["id"]  # parent child
        # if the child has a fieldrun shot match and the parent doesn't,
        # propagate the match to the parent.
        if not nullish(child["matching_fieldrun_shot_id"]) and nullish(parent["matching_fieldrun_shot_id"]):
            parent["matching_fieldrun_shot_id"] = child["matching_fieldrun_shot_id"]
            assert_true(self.layer.updateFeature(parent), "Failed to propagate matched fieldrun shot.")
        assert_true(self.layer.updateFeature(child), "Failed to parent child to parent shot.")

    def __prompt_user_with_recalculate(self, point_1: QgsFeature, point_2: QgsFeature) -> None:
        """Ask the user which points to include in the new average shot, then create it.

        The user may wish to recalculate the shot, creating a new avg shot made up of all the child shots.

        The child shots must be the very root shots of the tree.
        (Ex. if one of the shots is 5000A, we need to avg with 5000, 5001, ...etc
            so that we don't bias the average with the new shot.)
        """
        def get_root_shots(shot: QgsFeature) -> list[QgsFeature]:
            child_shots: list[QgsFeature] = [*self.layer.getFeatures(f"parent_point_id = '{shot['id']}'")]  # type: ignore
            if child_shots:
                root_shots = []
                for c in child_shots:
                    root_shots.extend(get_root_shots(c))
                return root_shots
            return [shot]

        # get all root shots
        root_shots = [*get_root_shots(point_1), *get_root_shots(point_2)]

        # prompt user
        dialog = RecalculateShotDialog(root_shots, self.layer)
        return_code = dialog.exec()
        if return_code == dialog.Rejected:
            return

        # create average shot
        checked_shots = dialog.get_checked_shots()
        avg_shot = get_average_point(self.layer, checked_shots)
        avg_shot["name"] = parent_point_name(point_1["name"])
        avg_shot["fieldwork_id"] = point_1["fieldwork_id"]

        # for geopackage testing, make sure we're not using a fid from a child point
        idx = self.layer.fields().indexFromName("fid")
        if idx is not None:
            avg_shot[idx] = None

        # make sure the matched fieldrun shot of one of the two top same point shots are propagated.
        if not nullish(point_1["matching_fieldrun_shot_id"]):
            avg_shot["matching_fieldrun_shot_id"] = point_1["matching_fieldrun_shot_id"]
        elif not nullish(point_2["matching_fieldrun_shot_id"]):
            avg_shot["matching_fieldrun_shot_id"] = point_2["matching_fieldrun_shot_id"]

        # parent children to new shot and save changes
        assert_true(self.layer.addFeature(avg_shot), "Failed to add average shot.")
        point_1["parent_point_id"] = avg_shot["id"]
        assert_true(self.layer.updateFeature(point_1), "Failed to parent point 1 to average shot.")
        point_2["parent_point_id"] = avg_shot["id"]
        assert_true(self.layer.updateFeature(point_2), "Failed to parent point 2 to average shot.")

    def __prompt_user_with_same_point(self, point_1: QgsFeature, point_2: QgsFeature) -> None:
        """Prompt user with options on how to handle the merge.

        Allow user to:
        - select which point to keep as the top level point
        - opt to recalculate a new point with all points in the tree
        - do nothing
        """
        with timed("Show dialog"):
            dialog = PossibleSamePointShotDialog(
                point_1,
                point_2,
            )
        with timed("Show dialog (exec)"):
            dialog.exec()

        do_nothing = dialog.do_nothing_radio.isChecked()
        if do_nothing:
            # mark pair as decided on so we don't ask again in next iteration
            self.do_nothing_ids.add(point_1["id"])
            self.do_nothing_ids.add(point_2["id"])
            return

        keep_p1 = dialog.keep_p1_radio.isChecked()
        if keep_p1:
            self.__parent_child_to_shot(dialog.point_1, dialog.point_2)

        keep_p2 = dialog.keep_p2_radio.isChecked()
        if keep_p2:
            self.__parent_child_to_shot(dialog.point_2, dialog.point_1)

        recalculate = dialog.recalculate_new_point_radio.isChecked()
        if recalculate:
            self.__prompt_user_with_recalculate(point_1, point_2)

    def run(self):
        self.layer.startEditing()
        for i in range(MAX_SOLVING_ITERATIONS):
            QgsMessageLog.logMessage(f"Solving iteration {i + 1}.")
            changed = False

            with timed("find pairs"), progress_dialog("Searching for same point shots...", indeterminate=True):
                pairs = self.__find_same_point_shots()

            for pair in pairs:
                changed = True
                self.__prompt_user_with_same_point(pair[0], pair[1])
            if not changed:
                QgsMessageLog.logMessage("No new pairs found, breaking out of loop.")
                break
        self.layer.commitChanges()
