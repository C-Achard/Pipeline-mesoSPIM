import sys

sys.path.append("")
import logging
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import List

import bg_space as bgs
import numpy as np
from bg_atlasapi import BrainGlobeAtlas
from dask.array.image import imread as dask_imread
from dataclasses_json import dataclass_json
from scipy.ndimage import find_objects, label
from skimage.transform import resize
from tifffile import imread as tif_imread
from tqdm import tqdm

logger = logging.getLogger(__name__)


def load_json_config(path):
    logger.info(f"Loading json config: {path}")
    f = open(path)
    data = json.load(f)
    return data


def get_date_time():
    """Get date and time in the following format : year_month_day_hour_minute_second."""
    return "{:%Y_%m_%d_%H_%M_%S}".format(datetime.now())


def prepare_roi_cfos(
    roi_ids: List[int],
    cfos_scan_path: str,
    brainreg_labels_path: str,
    original_orientation: str,
    atlas: str,
):
    """Crops the cFOS scan regions of interest.

    Args:
        roi_ids (List[int]): list of IDs for the region of interest. See get_atlas_ref_df
        cfos_scan_path (str): path to the cFOS scan for cellseg
        brainreg_labels_path (str): path to the labels from brainreg
        original_orientation (str): 3-characters string containing original orientation of the brain used for brainreg
        atlas (str): atlas name from BrainGlobeAtlas
    Returns:
        Cropped cFOS scan with only specified ROIS.
    """
    cFOS = load_volumes(
        cfos_scan_path
    )  # TODO(Cyril) adapt if dims not always 2048x2048
    labels = load_volumes(brainreg_labels_path)
    logger.info(
        f"Loaded labels at {brainreg_labels_path} of shape {labels.shape}"
    )

    labels = reorient_volume(
        labels.compute(),
        source=get_atlas_orientation(atlas),
        target=original_orientation,
    )
    logger.info("Rescaling image, please wait...")
    labels = rescale_labels(labels, cFOS.shape)
    logger.info("Done")
    logger.info("Extracting ROIs...")
    rois_dict = {}

    for roi_id in tqdm(roi_ids):
        roi_label = get_roi_label(roi_id, labels)
        roi_image = get_roi_image(cFOS.compute(), roi_label)
        #############################
        debug_path = Path.home() / Path("Desktop")
        np.save(str(debug_path / Path("lab1")), roi_label)
        np.save(str(debug_path / Path("im1")), roi_image)
        ############################# # DEBUG TODO REMOVE
        # roi_image = split_volumes(
        #     roi_image
        # )  # TODO(cyril) find optimal way of removing smaller
        rois_dict[str(roi_id)] = roi_image
        logger.debug(f"roi shape {roi_image.shape}")

    return rois_dict


def load_volumes(path, x=2048, y=2048):
    """Lazily loads .raw and .tif volumes. If raw, x and y are required."""
    logger.info(f"Loading {path}")
    raw_reader = imread_load_raw(x, y)
    if Path(path).suffix == ".raw":
        return dask_imread(path, imread=raw_reader)[
            0
        ]  # FIXME might not be correct to load first
    elif not (Path(path).suffix == ".tif" or Path(path).suffix == ".tiff"):
        raise ValueError(f"Filetype {Path(path).suffix} not supported")

    return dask_imread(path, imread=tif_imread)[0]


def imread_load_raw(x=2048, y=2048):
    """Partial function to load raw image from the mesoSPIM."""
    return partial(load_raw, x=x, y=y)


def load_raw(path, x=2048, y=2048):
    """Load raw image from the mesoSPIM."""
    vol = np.fromfile(path, dtype=np.unint16, count=-1)
    return vol.reshape((-1, x, y))


def get_atlas_ref_df(atlas: str = "allen_mouse_25um"):
    """Get reference dataframe from BrainGlobeAtlas as a pandas dataframe."""
    return BrainGlobeAtlas(atlas).lookup_df  # asr


def get_atlas_orientation(atlas: str = "allen_mouse_25um"):
    """Get orientation from given atlas."""
    return BrainGlobeAtlas(atlas).orientation


def get_atlas_shape(atlas: str = "allen_mouse_25um"):
    """Get shape from given atlas."""
    return BrainGlobeAtlas(atlas).shape


def get_atlas_region_name_from_id(
    roi_id: int, atlas: str = "allen_mouse_25um"
):
    """Get region name from given atlas and region id."""
    return BrainGlobeAtlas(atlas).structures[roi_id]["name"]


def format_roi_name_to_path(roi_name: str):
    """Format brain ROI name from lookup df to a path-compatible name."""
    roi_name = roi_name.replace(",", "")  # valid for all atlas csv ?
    roi_name = roi_name.replace(" ", "_")
    roi_name = roi_name.replace("/", "_")
    return roi_name


def get_roi_label(roi_id, labels):
    """Get label for a given id in a label image."""
    return np.where(labels == roi_id, labels, np.zeros_like(labels))


def get_roi_labels(roi_ids, labels):
    """Get labels for a given list of ids in a label image."""
    res = np.zeros_like(labels)
    for roi_id in roi_ids:
        res += get_roi_label(roi_id, labels)
    return res


def get_roi_image(volume, region_labels):
    """Get image for a given region label."""
    return np.where(region_labels != 0, volume, np.zeros_like(volume))


def rescale_labels(labels, volume_shape):
    """Rescale labels to match volume shape."""
    return resize(
        labels, volume_shape, order=0, preserve_range=True, anti_aliasing=False
    )


def reorient_volume(scan, source="asr", target="sal"):
    """Reorient volume from source to target orientation."""
    return bgs.map_stack_to(source, target, scan, copy=False)


def split_volumes(cFOS_cropped_volume):
    """Helper function to split every connected ROI to crop it for cellseg.

    Removes all volumes smaller than minimal_cube_size.
    """
    labeled = label(cFOS_cropped_volume)[0]
    locations = find_objects(labeled)

    results = []
    for location in locations:
        res = cFOS_cropped_volume[location]
        results.append(res)

    biggest_id = np.argmax([res.flatten().shape for res in results])
    # logger.debug(f"{results}")
    return results[biggest_id]


@dataclass_json
@dataclass
class BrainregParams:
    """BrainReg parameters."""

    path: str
    voxel_size_x: float
    voxel_size_y: float
    voxel_size_z: float
    orientation: str
    atlas: str

    @classmethod
    def load_from_json(cls, path):
        """Load config from json file."""
        data = load_json_config(path)
        logger.info("Config loaded from json for brainreg results")

        data_dict = {
            "path": data["registration_output_folder"],
            "voxel_size_x": data["voxel_sizes"][1],
            "voxel_size_y": data["voxel_sizes"][2],
            "voxel_size_z": data["voxel_sizes"][0],
            "orientation": data["orientation"],
            "atlas": data["atlas"],
        }

        return cls.from_dict(data_dict)
