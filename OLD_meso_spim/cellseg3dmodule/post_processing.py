import logging

# MONAI

logger = logging.getLogger(__name__)

import numpy as np
from skimage.measure import label

# from skimage.measure import marching_cubes
# from skimage.measure import mesh_surface_area
from skimage.morphology import remove_small_objects, dilation
from skimage.segmentation import watershed
from skimage.transform import resize


def binary_connected(
    volume, thres=0.5, thres_small=3, scale_factors=(1.0, 1.0, 1.0)
):
    r"""Convert binary foreground probability maps to instance masks via
    connected-component labeling.

    Args:
        volume (numpy.ndarray): foreground probability of shape :math:`(C, Z, Y, X)`.
        thres (float): threshold of foreground. Default: 0.8
        thres_small (int): size threshold of small objects to remove. Default: 128
        scale_factors (tuple): scale factors for resizing in :math:`(Z, Y, X)` order. Default: (1.0, 1.0, 1.0)
    """
    if volume.shape[0] > 1:
        semantic = volume[0]
    else:
        semantic = volume
    foreground = semantic > thres  # int(255 * thres)
    segm = label(foreground)
    segm = remove_small_objects(segm, thres_small)

    if not all(x == 1.0 for x in scale_factors):
        target_size = (
            int(semantic.shape[0] * scale_factors[0]),
            int(semantic.shape[1] * scale_factors[1]),
            int(semantic.shape[2] * scale_factors[2]),
        )
        segm = resize(
            segm,
            target_size,
            order=0,
            anti_aliasing=False,
            preserve_range=True,
        )

    return segm


def binary_watershed(
    volume,
    thres_seeding=0.9,
    thres_small=10,
    thres_objects=0.01,
    scale_factors=(1.0, 1.0, 1.0),
    rem_seed_thres=3,
):
    r"""Convert binary foreground probability maps to instance masks via
    watershed segmentation algorithm.

    Note:
        This function uses the `skimage.segmentation.watershed <https://github.com/scikit-image/scikit-image/blob/master/skimage/segmentation/_watershed.py#L89>`_
        function that converts the input image into ``np.float64`` data type for processing. Therefore please make sure enough memory is allocated when handling large arrays.

    Args:
        volume (numpy.ndarray): foreground probability of shape :math:`(C, Z, Y, X)`.
        thres_seeding (float): threshold for seeding. Default: 0.98
        thres_objects (float): threshold for foreground objects. Default: 0.3
        thres_small (int): size threshold of small objects removal. Default: 10
        scale_factors (tuple): scale factors for resizing in :math:`(Z, Y, X)` order. Default: (1.0, 1.0, 1.0)
        rem_seed_thres (int): threshold for small seeds removal. Default : 3
    """
    semantic = np.squeeze(volume)
    # if volume.shape[0] > 1:
    #     semantic = volume[0]
    # else:
    #     semantic = volume
    seed_map = semantic > thres_seeding
    foreground = semantic > thres_objects
    seed = label(seed_map)
    seed = remove_small_objects(seed, rem_seed_thres)
    segm = watershed(-semantic.astype(np.float64), seed, mask=foreground)
    segm = remove_small_objects(segm, thres_small)

    if not all(x == 1.0 for x in scale_factors):
        target_size = (
            int(semantic.shape[0] * scale_factors[0]),
            int(semantic.shape[1] * scale_factors[1]),
            int(semantic.shape[2] * scale_factors[2]),
        )
        segm = resize(
            segm,
            target_size,
            order=0,
            anti_aliasing=False,
            preserve_range=True,
        )

    return np.array(segm)


def bc_watershed(
    volume,
    thres1=0.9,
    thres2=0.8,
    thres3=0.85,
    thres_small=128,
    scale_factors=(1.0, 1.0, 1.0),
):
    """From binary foreground probability map and instance contours to
    instance masks via watershed segmentation algorithm.
    Args:
        volume (numpy.ndarray): foreground and contour probability of shape :math:`(C, Z, Y, X)`.
        thres1 (float): threshold of seeds. Default: 0.9
        thres2 (float): threshold of instance contours. Default: 0.8
        thres3 (float): threshold of foreground. Default: 0.85
        thres_small (int): size threshold of small objects to remove. Default: 128
        scale_factors (tuple): scale factors for resizing in :math:`(Z, Y, X)` order. Default: :math:`(1.0, 1.0, 1.0)`
        remove_small_mode (str): ``'background'`` or ``'neighbor'``. Default: ``'background'``
    """
    assert volume.shape == 2
    semantic = volume[0]
    boundary = volume[1]
    seed_map = (semantic > thres1) * (boundary < thres2)  # seed , not contours
    foreground = semantic > thres3
    seed = label(seed_map)
    segm = watershed(-semantic, seed, mask=foreground)
    segm = remove_small_objects(segm, thres_small)

    if not all(x == 1.0 for x in scale_factors):
        target_size = (
            int(semantic.shape[0] * scale_factors[0]),
            int(semantic.shape[1] * scale_factors[1]),
            int(semantic.shape[2] * scale_factors[2]),
        )
        segm = resize(
            segm,
            target_size,
            order=0,
            anti_aliasing=False,
            preserve_range=True,
        )
    return segm.astype(np.uint32)


def bc_connected(
    volume,
    thres1=0.8,
    thres2=0.5,
    thres_small=128,
    scale_factors=(1.0, 1.0, 1.0),
    dilation_struct=(1, 5, 5),
):
    """From binary foreground probability map and instance contours to
    instance masks via connected-component labeling.
    Note:
        The instance contour provides additional supervision to distinguish closely touching
        objects. However, the decoding algorithm only keep the intersection of foreground and
        non-contour regions, which will systematically result in incomplete instance masks.
        Therefore we apply morphological dilation (check :attr:`dilation_struct`) to enlarge
        the object masks.
    Args:
        volume (numpy.ndarray): foreground and contour probability of shape :math:`(C, Z, Y, X)`.
        thres1 (float): threshold of foreground. Default: 0.8
        thres2 (float): threshold of instance contours. Default: 0.5
        thres_small (int): size threshold of small objects to remove. Default: 128
        scale_factors (tuple): scale factors for resizing in :math:`(Z, Y, X)` order. Default: :math:`(1.0, 1.0, 1.0)`
        dilation_struct (tuple): the shape of the structure for morphological dilation. Default: :math:`(1, 5, 5)`
        remove_small_mode (str): ``'background'`` or ``'neighbor'``. Default: ``'background'``
    """
    assert volume.shape == 2
    semantic = volume[0]
    boundary = volume[1]
    foreground = (semantic > thres1) * (boundary < thres2)

    segm = label(foreground)
    struct = np.ones(dilation_struct)
    segm = dilation(segm, struct)
    segm = remove_small_objects(segm, thres_small)

    if not all(x == 1.0 for x in scale_factors):
        target_size = (
            int(semantic.shape[0] * scale_factors[0]),
            int(semantic.shape[1] * scale_factors[1]),
            int(semantic.shape[2] * scale_factors[2]),
        )
        segm = resize(
            segm,
            target_size,
            order=0,
            anti_aliasing=False,
            preserve_range=True,
        )
    return segm.astype(np.uint32)
