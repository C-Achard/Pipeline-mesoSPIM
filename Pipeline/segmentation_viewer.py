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
    for roi_id in roi_ids:
        display_cropped_roi_instance_labels(
            name, scan_attempt, roi_ids, viewer
        )


def display_cropped_roi_instance_labels(name, scan_attempt, roi_id, viewer):
    query_reg = (
        spim.BrainRegistrationResults.BrainregROI()
        & f"scan_attempt='{scan_attempt}'"
    )
    query_reg = query_reg.fetch(as_dict=True)
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
            table["scan_shape"],
        ]
        for table in query_reg
        if table["mouse_name"] == name and table["roi_id"] == roi_id
    }

    for key in Masks:
        sample = np.zeros_like(Masks[key][8])
        sample[
            Masks[key][1] : Masks[key][2] + 1,
            Masks[key][3] : Masks[key][4] + 1,
            Masks[key][5] : Masks[key][6] + 1,
        ] = Mask[key][0]
        Masks[key][0] = sample

    ids_key_view = 0
    for key in Masks:
        ids_key_view = Masks[key][7]
    query_instance = (
        spim.Segmentation()
        & f"scan_attempt='{scan_attempt}'"
        & f"ids_key='{ids_key_view}'"
    )
    query_instance = query_instance.fetch(as_dict=True)
    Instance_labels = {
        table["cont_region_id"]: imio.load_any(table["instance_labels"])
        for table in query_instance
        if table["mouse_name"] == name
    }

    for key in Masks:
        sample = np.zeros_like(Masks[key][8])
        sample[
            Masks[key][1] : Masks[key][2] + 1,
            Masks[key][3] : Masks[key][4] + 1,
            Masks[key][5] : Masks[key][6] + 1,
        ] = Instance_labels[key]
        crop = np.where(Masks[key][0], sample, np.zeros_like(sample))
        viewer.add_labels(crop, name="instance labels for ROI" + str(key))
        break


def display_cropped_continuous_instance_labels(
    name, scan_attempt, ids_key, viewer
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
            .reshape(table["mask_shape"]),
            table["x_min"],
            table["x_max"],
            table["y_min"],
            table["y_max"],
            table["z_min"],
            table["z_max"],
            table["scan_shape"],
        ]
        for table in query_reg
        if table["mouse_name"] == name
    }

    for key in Masks:
        sample = np.zeros_like(Masks[key][7])
        sample[
            Masks[key][1] : Masks[key][2] + 1,
            Masks[key][3] : Masks[key][4] + 1,
            Masks[key][5] : Masks[key][6] + 1,
        ] = Mask[key][0]
        Masks[key][0] = sample

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

    for key in Masks:
        sample = np.zeros_like(Masks[key][7])
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
    display_cropped_continuous_instance_labels("mouse_chickadee", 0, 0, viewer)
    display_resized_atlas("mouse_chickadee", 0, viewer, 0, add_crop=True)
