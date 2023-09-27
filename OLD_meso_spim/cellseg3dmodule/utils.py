import glob
import logging
import os

# MONAI
import torch
from matplotlib import pyplot as plt
from monai.losses import (
    DiceCELoss,
    DiceFocalLoss,
    DiceLoss,
    FocalLoss,
    GeneralizedDiceLoss,
    TverskyLoss,
)

from cellseg3dmodule.models import (
    model_SegResNet as SegResNet,
    model_TRAILMAP as TRAILMAP,
    model_VNet as VNet,
    TRAILMAP_test as TMAP,
    model_Swin as Swin,
)
from cellseg3dmodule.config import ImageStats

logger = logging.getLogger(__name__)

import numpy as np

# from skimage.measure import marching_cubes
# from skimage.measure import mesh_surface_area
from skimage.measure import regionprops
from dask_image.imread import imread


def get_loss(key):
    loss_dict = {
        "Dice loss": DiceLoss(sigmoid=True),
        "Focal loss": FocalLoss(),
        "Dice-Focal loss": DiceFocalLoss(sigmoid=True, lambda_dice=0.5),
        "Generalized Dice loss": GeneralizedDiceLoss(sigmoid=True),
        "DiceCELoss": DiceCELoss(
            to_onehot_y=True,
            softmax=True,
            ce_weight=torch.tensor(
                [0.15, 1, 0.05]
            ).cuda(),  # background, cell, edge
        ),
        "Tversky loss": TverskyLoss(sigmoid=True),
    }
    return loss_dict[key]


def get_model(key):
    models_dict = {
        "VNet": VNet,
        "SegResNet": SegResNet,
        "TRAILMAP_pre-trained": TRAILMAP,
        "TRAILMAP_test": TMAP,
        "Swin": Swin,
    }
    return models_dict[key]


def zoom_factor(voxel_sizes):
    base = min(voxel_sizes)
    return [base / s for s in voxel_sizes]


def create_dataset_dict(volume_directory, label_directory):
    """Creates data dictionary for MONAI transforms and training."""
    images_filepaths = sorted(
        glob.glob(os.path.join(volume_directory, "*.tif"))
    )

    labels_filepaths = sorted(
        glob.glob(os.path.join(label_directory, "*.tif"))
    )
    if len(images_filepaths) == 0 or len(labels_filepaths) == 0:
        raise ValueError("Data folders are empty")

    logger.info("Images :")
    for file in images_filepaths:
        logger.info(os.path.basename(file).split(".")[0])
    logger.info("*" * 10)
    logger.info("Labels :")
    for file in labels_filepaths:
        logger.info(os.path.basename(file).split(".")[0])

    data_dicts = [
        {"image": image_name, "label": label_name}
        for image_name, label_name in zip(images_filepaths, labels_filepaths)
    ]

    return data_dicts


def get_padding_dim(image_shape, anisotropy_factor=None):
    """
    Finds the nearest and superior power of two for each image dimension to zero-pad it for CNN processing,
    accepts either 2D or 3D images shapes. E.g. an image size of 30x40x100 will result in a padding of 32x64x128.
    Shows a warning if the padding dimensions are very large.

    Args:
        image_shape (torch.size): an array of the dimensions of the image in D/H/W if 3D or H/W if 2D

    Returns:
        array(int): padding value for each dim
    """
    padding = []

    dims = len(image_shape)
    logger.info(f"Dimension of data for padding : {dims}D")
    logger.info(f"Image shape is {image_shape}")
    if dims != 2 and dims != 3:
        error = "Please check the dimensions of the input, only 2 or 3-dimensional data is supported currently"
        logger.info(error)
        raise ValueError(error)

    for i in range(dims):
        n = 0
        pad = -1
        size = image_shape[i]
        if anisotropy_factor is not None:
            # problems with zero divs avoided via params for spinboxes
            size = int(size / anisotropy_factor[i])
        while pad < size:
            # if size - pad < 30:
            #     warnings.warn(
            #         f"Your value is close to a lower power of two; you might want to choose slightly smaller"
            #         f" sizes and/or crop your images down to {pad}"
            #     )

            pad = 2**n
            n += 1
            if pad >= 256:
                logger.warning(
                    "Warning : a very large dimension for automatic padding has been computed.\n"
                    "Ensure your images are of an appropriate size and/or that you have enough memory."
                    f"The padding value is currently {pad}."
                )

        padding.append(pad)

    logger.info(f"Padding sizes are {padding}")
    return padding


def volume_stats(volume_image) -> ImageStats:
    """Computes various statistics from instance labels and returns them in a dict.
    Currently provided :

        * "Volume": volume of each object
        * "Centroid": x,y,z centroid coordinates for each object
        * "Sphericity (axes)": sphericity computed from semi-minor and semi-major axes
        * "Image size": size of the image
        * "Total image volume": volume in pixels of the whole image
        * "Total object volume (pixels)": total labeled volume in pixels
        * "Filling ratio": ratio of labeled over total pixel volume
        * "Number objects": total number of unique labeled objects

    Args:
        volume_image: instance labels image

    Returns:
        dict: Statistics described above
    """

    properties = regionprops(volume_image)

    # sphericity_va = []
    def sphericity(region):
        try:
            return sphericity_axis(
                region.axis_major_length * 0.5, region.axis_minor_length * 0.5
            )
        except ValueError:
            return (
                np.nan
            )  # FIXME better way ? inconsistent errors in region.axis_minor_length

    sphericity_ax = [sphericity(region) for region in properties]

    volume = [region.area for region in properties]

    def fill(lst, n=len(properties) - 1):
        return fill_list_in_between(lst, n, "")

    if len(volume_image.flatten()) != 0:
        ratio = np.sum(volume) / len(volume_image.flatten())
    else:
        ratio = 0

    return ImageStats(
        volume=volume,
        centroid_x=[region.centroid[0] for region in properties],
        centroid_y=[region.centroid[0] for region in properties],
        centroid_z=[region.centroid[2] for region in properties],
        sphericity_ax=sphericity_ax,
        image_size=volume_image.shape,
        total_image_volume=len(volume_image.flatten()),
        total_filled_volume=np.sum(volume),
        filling_ratio=ratio,
        number_objects=len(properties),
    )


def fill_list_in_between(lst, n, elem):
    """Fills a list with n * elem between each member of list.
    Example with list = [1,2,3], n=2, elem='&' : returns [1, &, &,2,&,&,3,&,&]

    Args:
        lst: list to fill
        n: number of elements to add
        elem: added n times after each element of list

    Returns :
        Filled list
    """

    new_list = []
    for i in range(len(lst)):
        temp_list = [lst[i]]
        while len(temp_list) < n + 1:
            temp_list.append(elem)
        if i < len(lst) - 1:
            new_list += temp_list
        else:
            new_list.append(lst[i])
            for j in range(n):
                new_list.append(elem)
            return new_list


def sphericity_axis(semi_major, semi_minor):
    """Computes the sphericity from volume semi major (a) and semi minor (b) axes.

    .. math::
        sphericity = \\frac {2 \\sqrt[3]{ab^2}} {a+ \\frac {b^2} {\\sqrt{a^2-b^2}}ln( \\frac {a+ \\sqrt{a^2-b^2}} {b} )}

    """
    a = semi_major
    b = semi_minor

    root = np.sqrt(a**2 - b**2)
    try:
        result = (
            2
            * (a * (b**2)) ** (1 / 3)
            / (a + (b**2) / root * np.log((a + root) / b))
        )
    except ZeroDivisionError:
        print("Zero division in sphericity calculation was replaced by 0")
        result = 0
    except ValueError as e:
        print(f"Error encountered in calculation : {e}")
        result = "Error in calculation"

    return result


def read_tiff_stack_labels(path):
    print(path)
    img = imread(path)
    return img.compute().astype(np.uint16)


def define_matplotlib_defaults():
    p = plt.rcParams

    p["figure.figsize"] = 6, 5
    p["figure.edgecolor"] = "black"
    p["figure.facecolor"] = "#f9f9f9"
    p["image.cmap"] = "cool"

    p["axes.linewidth"] = 1
    p["axes.facecolor"] = "#f9f9f9"
    p["axes.ymargin"] = 0.1
    p["axes.spines.bottom"] = True
    p["axes.spines.left"] = True
    p["axes.spines.right"] = False
    p["axes.spines.top"] = False

    p["axes.grid"] = True
    p["grid.color"] = "black"
    p["grid.linewidth"] = 0.1

    p["xtick.bottom"] = True
    p["xtick.top"] = False
    p["xtick.direction"] = "out"
    p["xtick.major.size"] = 5
    p["xtick.major.width"] = 1
    p["xtick.minor.size"] = 3
    p["xtick.minor.width"] = 0.5
    p["xtick.minor.visible"] = False

    p["ytick.left"] = True
    p["ytick.right"] = False
    p["ytick.direction"] = "out"
    p["ytick.major.size"] = 5
    p["ytick.major.width"] = 1
    p["ytick.minor.size"] = 3
    p["ytick.minor.width"] = 0.5
    p["ytick.minor.visible"] = False

    p["lines.linewidth"] = 2
    p["lines.marker"] = "o"
    p["lines.markeredgewidth"] = 1.5
    p["lines.markeredgecolor"] = "auto"
    p["lines.markerfacecolor"] = "auto"
    p["lines.markersize"] = 3
