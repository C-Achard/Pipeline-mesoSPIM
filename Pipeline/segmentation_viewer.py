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


def get_scan_shape(name, scan_attempt):
    query_shape = spim.Scan() & f"scan_attempt='{scan_attempt}'"
    query_shape = query_shape.fetch(as_dict=True)
    scan_shape = [
        imio.load_any(table["autofluo_path"]).shape
        for table in query_shape
        if table["mouse_name"] == name
    ][0]
    return scan_shape


def display_resized_atlas(
    name, scan_attempt, viewer, ids_key=0, add_crop=False
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
        if query_ROIs:
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


def display_cropped_rois_instance_labels(name, scan_attempt, roi_ids, viewer):
    shape = get_scan_shape(name, scan_attempt)

    for roi_id in roi_ids:
        display_cropped_roi_instance_labels(
            name, scan_attempt, roi_ids, shape, viewer
        )


def display_cropped_roi_instance_labels(
    name, scan_attempt, roi_id, shape, viewer
):
    query_roi = (
        spim.BrainRegistrationResults.BrainregROI()
        & f"scan_attempt='{scan_attempt}'"
    )
    query_roi = query_reg.fetch(as_dict=True)
    Masks = {
        table["roi_id"]: [
            load_npz(table["mask"])
            .toarray()
            .astype("bool")
            .reshape(table["mask_shape"]),
            table["x_min"],
            table["x_max"],
            table["y_min"],
            table["y_max"],
            table["z_min"],
            table["z_max"],
            table["ids_key"],
        ]
        for table in query_roi
        if table["mouse_name"] == name and table["roi_id"] == roi_id
    }

    ids_key_view = Masks[roi_id][7]

    query_instance = (
        spim.Segmentation()
        & f"scan_attempt='{scan_attempt}'"
        & f"ids_key='{ids_key_view}'"
    )
    query_instance = query_instance.fetch(as_dict=True)
    Instance_labels = {
        table["cont_region_id"]: [imio.load_any(table["instance_labels"])]
        for table in query_instance
        if table["mouse_name"] == name
    }

    query_reg = (
        spim.BrainRegistrationResults.ContinuousRegion()
        & f"scan_attempt='{scan_attempt}'"
        & f"ids_key='{ids_key}'"
    )
    query_reg = query_reg.fetch(as_dict=True)
    Coos = {
        table["cont_region_id"]: [
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

    sample = np.zeros(shape)
    for key in Instance_labels:
        if (
            Masks[roi_id][1] >= Coos[key][0]
            and Masks[roi_id][2] <= Coos[key][1]
            and Masks[roi_id][3] >= Coos[key][2]
            and Masks[roi_id][4] <= Coos[key][3]
            and Masks[roi_id][5] >= Coos[key][4]
            and Masks[roi_id][6] <= Coos[key][5]
        ):
            sample[
                Coos[key][0] : Coos[key][1] + 1,
                Coos[key][2] : Coos[key][3] + 1,
                Coos[key][4] : Coos[key][5] + 1,
            ] = Instance_labels[key]
            sample[
                Masks[roi_id][1] : Masks[roi_id][2] + 1,
                Masks[roi_id][3] : Masks[roi_id][4] + 1,
                Masks[roi_id][5] : Masks[roi_id][6] + 1,
            ] *= Masks[roi_id][0]
    viewer.add_labels(sample, name="instance labels for ROI" + str(roi_id))


def display_cropped_continuous_instance_labels(
    name, scan_attempt, ids_key, viewer
):
    shape = get_scan_shape(name, scan_attempt)

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
            .reshape(table["mask_shape"]),
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
        spim.Segmentation()
        & f"scan_attempt='{scan_attempt}'"
        & f"ids_key='{ids_key}'"
    )
    query_instance = query_instance.fetch(as_dict=True)
    Instance_labels = {
        table["cont_region_id"]: imio.load_any(table["instance_labels"])
        for table in query_instance
        if table["mouse_name"] == name
    }

    sample = np.zeros_like(shape)
    for key in Masks:
        sample[
            Masks[key][1] : Masks[key][2] + 1,
            Masks[key][3] : Masks[key][4] + 1,
            Masks[key][5] : Masks[key][6] + 1,
        ] = (
            Instance_labels[key] * Masks[key][0]
        )
    viewer.add_labels(sample, name="instance labels for continuous regions")


if __name__ == "__main__":
    login.connectToDatabase()
    viewer = napari.Viewer()
    display_cropped_continuous_instance_labels("mouse_chickadee", 0, 0, viewer)
    display_resized_atlas("mouse_chickadee", 0, viewer, 0, add_crop=True)
