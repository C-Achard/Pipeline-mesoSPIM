import sys
import numpy as np
import logging
from pathlib import Path
import login
import napari
import imio
from scipy.sparse import load_npz

sys.path.append("scripts")
sys.path.append("schema")

login.connectToDatabase()

from schema import mice, spim, user
from scripts import brainreg_config, determine_ids, brainreg_utils


def display_resized_atlas(
    name, username, scan_attempt, ids_key, viewer, add_crop=False
):
    query_scan = spim.Scan() & f"scan_attempt='{scan_attempt}'"
    query_scan = query_scan.fetch(as_dict=True)
    CFOS_shape = [
        imio.load_any(table["cfos_path"]).shape
        for table in query_scan
        if table["mouse_name"] == name
    ][0]

    query_reg = spim.BrainRegistration() & f"scan_attempt='{scan_attempt}'"
    query_reg = query_reg.fetch(as_dict=True)
    Atlas_downsized = [
        imio.load_any(table["registration_path"] + "/registered_atlas.tiff")
        for table in query_reg
        if table["mouse_name"] == name
    ][0]

    Atlas_resized = brainreg_utils.rescale_labels(Atlas_downsized, CFOS_shape)
    viewer.add_labels(Atlas_resized, name="Atlas")
    if add_crop:
        query_ROIs = (
            spim.ROIs()
            & f"scan_attempt='{scan_attempt}'"
            & f"ids_key='{ids_key}'"
        )
        query_ROIs = query_ROIs.fetch(as_dict=True)
        atlas_ids = [
            table["regions_of_interest_ids"]
            for table in query_ROIs
            if table["mouse_name"] == name
        ][0]
        Atlas_downsized_rois = brainreg_utils.get_roi_labels(
            atlas_ids, Atlas_downsized
        )
        Atlas_resized_rois = brainreg_utils.rescale_labels(
            Atlas_downsized_rois, CFOS_shape
        )
        viewer.add_labels(Atlas_resized_rois, name="Atlas cropped to ROIs")


def display_cropped_continuous_instance_labels(
    name, username, scan_attempt, ids_key, viewer
):
    query_reg = (
        spim.BrainRegistrationResults.ContinuousRegion()
        & f"scan_attempt='{scan_attempt}'"
        & f"ids_key='{ids_key}'"
    )
    query_reg = query_reg.fetch(as_dict=True)
    Masks = {
        table["cont_region_id"]: [
            load_npz(table["mask"])
            .toarray()
            .astype("bool")
            .reshape(
                (
                    table["mask_shape_x"],
                    table["mask_shape_y"],
                    table["mask_shape_z"],
                )
            ),
            table["x_min"],
            table["x_max"],
            table["y_min"],
            table["y_max"],
            table["z_min"],
            table["z_max"],
        ]
        for table in query_reg
        if table["mouse_name"] == name
    }

    query_instance = (
        spim.Inference()
        & f"scan_attempt='{scan_attempt}'"
        & f"ids_key='{ids_key}'"
    )
    query_instance = query_instance.fetch(as_dict=True)
    Instance_labels = {
        table["cont_region_id"]: imio.load_any(table["instance_labels"])
        for table in query_instance
        if table["mouse_name"] == name
    }

    for key in Masks:
        sample = np.zeros_like(Masks[key][0])
        sample[
            Masks[key][1] : Masks[key][2] + 1,
            Masks[key][3] : Masks[key][4] + 1,
            Masks[key][5] : Masks[key][6] + 1,
        ] = Instance_labels[key]
        crop = np.where(Masks[key][0], sample, np.zeros_like(sample))
        viewer.add_labels(
            crop, name="instance labels for region n°" + str(key)
        )


if __name__ == "__main__":
    login.connectToDatabase()
    viewer = napari.Viewer()
    display_cropped_continuous_instance_labels(
        "mouse_chickadee", "cyril_tit", 0, 0, viewer
    )
    display_resized_atlas(
        "mouse_chickadee", "cyril_tit", 0, 0, viewer, add_crop=True
    )
