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

# Connection to DataJoint
login.connectToDatabase()

from schema import mice, spim, user
from scripts import brainreg_config, determine_ids, brainreg_utils


def get_scan_shape(name, scan_attempt):
    """Function to get the shape of the scan given a mouse name and a scan "attempt"

    Args:
        name (string): name of the mouse
        scan attempt (int): "id" (unique number) of the pipeline run
    Returns:
        scan_shape: shape of the autofluorescence scan (= cFOS scan)
    """

    query_shape = spim.Scan() & f"scan_attempt='{scan_attempt}'"
    query_shape = query_shape.fetch(as_dict=True)
    scan_shape = [
        imio.load_any(table["autofluo_path"]).shape
        for table in query_shape
        if table["mouse_name"] == name
    ][0]
    return scan_shape


def get_roi_masks_dict(name, scan_attempt, roi_id):
    """Function to return a dictionnary of required variables from DataJoint to display a mask for a given ROI

    Args:
        name (string): name of the mouse
        scan attempt (int): "id" (unique number) of the pipeline run
        roi_id (int): ROI id
    Returns:
        Masks (dict{roi_id: [mask, coordinates, ids_key]})
    """

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
    return Masks


def get_cont_reg_masks_dict(name, scan_attempt, ids_key):
    """Function to return a dictionnary of required variables from DataJoint to display maks of continous regions corresponding to a list of ROIs

    Args:
        name (string): name of the mouse
        scan attempt (int): "id" (unique number) of the pipeline run
        ids_key (int): ROI id
    Returns:
        Masks (dict{cont_reg_id: [mask, coordinates]})
    """

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
    return Masks


def get_instance_labels_dict(name, scan_attempt, ids_key):
    """Function to return a dictionnary of required variables from DataJoint to display the instance labels of continous regions corresponding to a list of ROIs

    Args:
        name (string): name of the mouse
        scan attempt (int): "id" (unique number) of the pipeline run
        ids_key (int): ROI "id"
    Returns:
        Instance_labels (dict{cont_reg_id: instance labels})
    """

    query_instance = (
        spim.InstanceSegmentation()
        & f"scan_attempt='{scan_attempt}'"
        & f"ids_key='{ids_key}'"
    )
    query_instance = query_instance.fetch(as_dict=True)
    Instance_labels = {
        table["cont_region_id"]: imio.load_any(table["instance_labels"])
        for table in query_instance
        if table["mouse_name"] == name
    }
    return Instance_labels


def get_coordinates_instance_labels_dict(name, scan_attempt, ids_key):
    """Function to return a dictionnary of required variables from DataJoint to display the coordinates of continuous regions corresponding to a given list of ROIs

    Args:
        name (string): name of the mouse
        scan attempt (int): "id" (unique number) of the pipeline run
        ids_key (int): ROI id
    Returns:
        Coos (dict{cont_reg_id: coordinates})
    """

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
    return Coos


def display_resized_atlas(name, scan_attempt, viewer):
    """Function to display the registered atlas in the sample space on napari

    Args:
        name (string): name of the mouse
        scan_attempt (int): "id" (unique number) of the pipeline run
        viewer: napari window
    """
    # Get the shape of the scan
    shape = get_scan_shape(name, scan_attempt)
    query_reg = spim.BrainRegistration() & f"scan_attempt='{scan_attempt}'"
    query_reg = query_reg.fetch(as_dict=True)
    Atlas_downsized = [
        imio.load_any(table["registration_path"] + "/registered_atlas.tiff")
        for table in query_reg
        if table["mouse_name"] == name
    ][0]
    # rescale the downsampled atlas to the cFOS/sample shape
    Atlas_resized = brainreg_utils.rescale_labels(Atlas_downsized, CFOS_shape)
    # Display on napari
    viewer.add_labels(Atlas_resized, name="Atlas")


def display_cfos_scan(name, scan_attempt, viewer):
    """Function to display the cFOS scan in the sample space on napari

    Args:
        name (string): name of the mouse
        scan_attempt (int): "id" (unique number) of the pipeline run
        viewer: napari window
    """
    query_reg = spim.Scan() & f"scan_attempt='{scan_attempt}'"
    query_reg = query_reg.fetch(as_dict=True)
    cfos = [
        imio.load_any(table["cfos_path"])
        for table in query_reg
        if table["mouse_name"] == name
    ][0]
    # rescale the downsampled atlas to the cFOS/sample shape
    # Display on napari
    viewer.add_image(cfos, name="cFOS scan")


def display_cropped_rois_instance_labels(name, scan_attempt, roi_ids, viewer):
    """Function to display instance labels cropped to the given list of ROIs ids

    Args:
        name (string): name of the mouse
        scan attempt (int): "id" (unique number) of the pipeline run
        roi_ids (list[int]): list of ROIs ids
        viewer: napari window
    """
    shape = get_scan_shape(name, scan_attempt)

    for roi_id in roi_ids:
        display_cropped_roi_instance_labels(
            name, scan_attempt, roi_ids, shape, viewer
        )


def display_cropped_roi_instance_labels(
    name, scan_attempt, roi_id, shape, viewer
):
    """Function to display instance labels cropped to a single ROI id

    Args:
        name (string): name of the mouse
        scan attempt (int): "id" (unique number) of the pipeline run
        roi_id (int): ROI id
        shape: shape of the scan
        viewer: napari window
    """

    Masks = get_roi_masks_dict(name, scan_attempt, roi_id)
    Instance_labels = get_instance_labels_dict(
        name, scan_attempt, Masks[roi_id][7]
    )
    Coos = get_coordinates_instance_labels_dict(
        name, scan_attempt, Masks[roi_id][7]
    )

    for key in Instance_labels:
        if (
            Masks[roi_id][1] >= Coos[key][0]
            and Masks[roi_id][2] <= Coos[key][1]
            and Masks[roi_id][3] >= Coos[key][2]
            and Masks[roi_id][4] <= Coos[key][3]
            and Masks[roi_id][5] >= Coos[key][4]
            and Masks[roi_id][6] <= Coos[key][5]
        ):
            sample = np.zeros(shape, dtype=np.uint16)
            sample_mask = np.zeros(shape, dtype=np.uint16)
            sample[
                Coos[key][0] : Coos[key][1] + 1,
                Coos[key][2] : Coos[key][3] + 1,
                Coos[key][4] : Coos[key][5] + 1,
            ] = Instance_labels[key]
            sample_mask[
                Masks[roi_id][1] : Masks[roi_id][2] + 1,
                Masks[roi_id][3] : Masks[roi_id][4] + 1,
                Masks[roi_id][5] : Masks[roi_id][6] + 1,
            ] = Masks[roi_id][0]
            crop = np.where(sample_mask, sample, np.zeros_like(sample))
            del sample
            del sample_mask
            viewer.add_labels(
                crop, name="instance labels for ROI" + str(roi_id)
            )
            break


def display_cropped_continuous_instance_labels(
    name, scan_attempt, ids_key, viewer
):
    """Function to display instance labels cropped to a continuous region

    Args:
        name (string): name of the mouse
        scan attempt (int): "id" (unique number) of the pipeline run
        ids_key (int): id of the list of the ROIs
        viewer: napari window
    """
    shape = get_scan_shape(name, scan_attempt)
    Masks = get_cont_reg_masks_dict(name, scan_attempt, ids_key)
    Instance_labels = get_instance_labels_dict(name, scan_attempt, ids_key)

    sample = np.zeros(shape, dtype=np.uint16)
    sample[:] = np.nan
    for key in Masks:
        sample[
            Masks[key][1] : Masks[key][2] + 1,
            Masks[key][3] : Masks[key][4] + 1,
            Masks[key][5] : Masks[key][6] + 1,
        ] = (
            Instance_labels[key] * Masks[key][0]
        )
    viewer.add_labels(sample, name="instance labels for continuous regions")
    del sample


def display_cropped_continuous_instance_labels_bounding_box(
    name, scan_attempt, ids_key, viewer
):
    """Function to display instance labels cropped to a continuous region in a given bounding box

    Args:
        name (string): name of the mouse
        scan attempt (int): "id" (unique number) of the pipeline run
        ids_key (int): id of the list of the ROIs
        viewer: napari window
    """
    Masks = get_cont_reg_masks_dict(name, scan_attempt, ids_key)
    Instance_labels = get_instance_labels_dict(name, scan_attempt, ids_key)

    for key in Masks:
        sample = Instance_labels[key] * Masks[key][0]
        viewer.add_labels(
            sample, name="instance labels for continuous regions"
        )


def display_cropped_rois_instance_labels_bounding_box(
    name, scan_attempt, roi_ids, viewer
):
    """Function to display instance labels cropped to a list of ROIs in a given bounding box

    Args:
        name (string): name of the mouse
        scan attempt (int): "id" (unique number) of the pipeline run
        roi_ids (list[int]): list of ROI ids
        viewer: napari window
    """

    for roi_id in roi_ids:
        display_cropped_roi_instance_labels_bounding_box(
            name, scan_attempt, roi_id, viewer
        )


def display_cropped_roi_instance_labels_bounding_box(
    name, scan_attempt, roi_id, viewer
):
    """Function to display instance labels cropped to a single ROI in a given bounding box

    Args:
        name (string): name of the mouse
        scan attempt (int): "id" (unique number) of the pipeline run
        roi_id (int): ROI id
        viewer: napari window
    """

    Masks = get_roi_masks_dict(name, scan_attempt, roi_id)
    Instance_labels = get_instance_labels_dict(
        name, scan_attempt, Masks[roi_id][7]
    )
    Coos = get_coordinates_instance_labels_dict(
        name, scan_attempt, Masks[roi_id][7]
    )

    for key in Instance_labels:
        if (
            Masks[roi_id][1] >= Coos[key][0]
            and Masks[roi_id][2] <= Coos[key][1]
            and Masks[roi_id][3] >= Coos[key][2]
            and Masks[roi_id][4] <= Coos[key][3]
            and Masks[roi_id][5] >= Coos[key][4]
            and Masks[roi_id][6] <= Coos[key][5]
        ):
            sample_mask = np.zeros_like(Instance_labels[key])
            sample_mask[
                -Coos[key][0]
                + Masks[roi_id][1] : np.min(
                    -Coos[key][1] + Masks[roi_id][2], -1
                ),
                -Coos[key][2]
                + Masks[roi_id][3] : np.min(
                    -Coos[key][3] + Masks[roi_id][4], -1
                ),
                -Coos[key][4]
                + Masks[roi_id][5] : np.min(
                    -Coos[key][5] + Masks[roi_id][6], -1
                ),
            ] = Masks[roi_id][0]
            crop = np.where(
                sample_mask,
                Instance_labels[key],
                np.zeros_like(Instance_labels),
            )
            del sample_mask
            viewer.add_labels(
                crop, name="instance labels for ROI" + str(roi_id)
            )
            break


def display_cfos_bounding_box(name, scan_attempt, ids_key, viewer):
    """Function to display cFOS cropped to a continuous region in a given bounding box

    Args:
        name (string): name of the mouse
        scan attempt (int): "id" (unique number) of the pipeline run
        ids_key (int): id of the list of the ROIs
        viewer: napari window
    """
    query_reg = spim.Scan() & f"scan_attempt='{scan_attempt}'"
    query_reg = query_reg.fetch(as_dict=True)
    cfos = [
        imio.load_any(table["cfos_path"])
        for table in query_reg
        if table["mouse_name"] == name
    ][0]

    Masks = get_cont_reg_masks_dict(name, scan_attempt, ids_key)

    for key in Masks:
        cfos_cropped = cfos[
            Masks[key][1] : Masks[key][2] + 1,
            Masks[key][3] : Masks[key][4] + 1,
            Masks[key][5] : Masks[key][6] + 1,
        ]
        sample = cfos_cropped * Masks[key][0]
        viewer.add_image(
            sample, name="CFOS cropped to bounding box of continuous regions"
        )


if __name__ == "__main__":
    login.connectToDatabase()
    viewer = napari.Viewer()
    display_cropped_continuous_instance_labels("mouse_chickadee", 0, 0, viewer)
    display_resized_atlas("mouse_chickadee", 0, viewer)
