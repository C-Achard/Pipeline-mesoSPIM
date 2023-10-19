import json
import os
import imio
import logging
import bg_space as bg
import numpy as np
import scripts.brainreg_utils as brg_utils
from pathlib import Path
from bg_atlasapi import BrainGlobeAtlas


class Coordinates:
    def __init__(xmin, xmax, ymin, ymax, zmin, zmax):
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax
        self.zmin = zmin
        self.zmax = zmax


def roi_image(
    roi_id, registred_atlas_path, cfos_scan_path, original_orientation, atlas
):
    cFOS = imio.load_any(cfos_scan_path)
    rAtlas = imio.load_any(registred_atlas_path)
    cFOS = brg_utils.reorient_volume(
        cFOS.compute(),
        source=original_orientation,
        target=get_atlas_orientation(atlas),
    )
    rAtlas = brg_utils.rescale_labels(rAtlas.compute(), cFOS.shape)
    roi_label = brg_utils.get_roi_label(roi_id, rAtlas)
    roi_image = brg_utils.get_roi_image(
        cFOS.compute(), roi_label
    )  # .compute() ?????

    return roi_image


def find_coordinates_roi(roid_id, cfos_roi_image):
    xmin, xmax, ymin, ymax, zmin, zmax = 0, 0, 0, 0, 0, 0
    for x in range(cfos_roi_image.shape[0]):
        if np.any(
            cfos_roi_image[x, :, :] != 0
        ):  # is it the best approach ???? (or 0.0)????
            xmin = x
            break
    for x in range(cfos_roi_image.shape[0] - 1, -1, -1):
        if np.any(
            cfos_roi_image[x, :, :] != 0
        ):  # is it the best approach ???? (or 0.0)????
            xmax = x
            break
    for y in range(cfos_roi_image.shape[1]):
        if np.any(
            cfos_roi_image[:, y, :] != 0
        ):  # is it the best approach ???? (or 0.0)????
            ymin = y
            break
    for y in range(cfos_roi_image.shape[0] - 1, -1, -1):
        if np.any(
            cfos_roi_image[:, y, :] != 0
        ):  # is it the best approach ???? (or 0.0)????
            ymax = y
            break
    for z in range(cfos_roi_image.shape[2]):
        if np.any(
            cfos_roi_image[:, :, z] != 0
        ):  # is it the best approach ???? (or 0.0)????
            xmin = x
            break
    for z in range(cfos_roi_image.shape[2]):
        if np.any(
            cfos_roi_image[:, :, z] != 0
        ):  # is it the best approach ???? (or 0.0)????
            xmin = x
            break
    return xmin, xmax, ymin, ymax, zmin, zmax


def extract_roi(coordinates, cfos_roi_image):
    return
    cfos_roi_image[
        coordinates.xmin : coordinates.xmax + 1,
        coordinates.ymin : coordinates.ymax + 1,
        coordinates.zmin : coordinates.zmax + 1,
    ]


def crop_brain(
    roi_ids, registred_atlas_path, cfos_scan_path, original_orientation, atlas
):
    cropped_rois = {}
    for roi_id in roi_ids:
        cfos_roi_image = roi_image(
            roi_id,
            registred_atlas_path,
            cfos_scan_path,
            original_orientation,
            atlas,
        )
        coos = Coordinates(find_coordinates_roi(roid_id, cfos_roi_image))
        cropped_cfos_roi_image = extract_roi(coos, cfos_roi_image)
        cropped_rois[str(roi_id)] = cropped_cfos_roi_image
    return cropped_rois
