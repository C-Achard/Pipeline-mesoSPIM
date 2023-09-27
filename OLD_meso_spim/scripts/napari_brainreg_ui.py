import logging
from pathlib import Path

import napari
import scripts.brainreg_utils as utils
from brainreg_napari.register import brainreg_register
from cellseg3dmodule.utils import zoom_factor

DEFAULT_PATH = Path.home() / Path("Desktop/Code/BRAINREG_DATA/test_data")

logger = logging.getLogger(__name__)

# TODO(cyril) add dataclass loaded from json with default values for widget as in cellseg3d config.py
# TODO(cyril) add test mode that closes napari automatically
# TODO(cyril, mariia) find out if running several jobs in parallel works. Would be great if possible

# resolution in microns (placeholder, put in config json later)
X_VOXEL = 1.5
Y_VOXEL = 1.5
Z_VOXEL = 5


def open_brainreg_window(autofluo_scan_path: str):
    """Opens brainreg in napari with default parameters and awaits user input to start registration, then recovers results data.

    NOTE: brainreg will freeze the UI while running. napari should ONLY BE CLOSED ONCE RESULTS HAVE BEEN CREATED.
    The pipeline will fail to populate otherwise.
    """  # TODO(cyril) add exception handling for that case
    viewer = napari.Viewer()

    DEFAULT_PATH.mkdir(parents=True, exist_ok=True)

    widget = brainreg_register()

    widget.x_pixel_um.value = X_VOXEL
    widget.y_pixel_um.value = Y_VOXEL
    widget.z_pixel_um.value = Z_VOXEL

    widget.registration_output_folder.value = str(DEFAULT_PATH)
    widget.registration_output_folder.tooltip = "DO NOT CHANGE"
    widget.registration_output_folder.enabled = False

    widget.save_original_orientation.value = True
    widget.save_original_orientation.enabled = False

    widget.block.value = True
    widget.block.enabled = False

    autofluo_scan = utils.load_volumes(
        autofluo_scan_path
    )  # TODO(cyril) add dimensions handling if x,y not always 2048. Assumption is not always correct
    viewer.add_image(
        autofluo_scan,
        name="Autofluorescence_whole_brain",
        # contrast_limits=[0, 2000],
        multiscale=False,
        scale=zoom_factor(
            [X_VOXEL, Z_VOXEL, Y_VOXEL]
        ),  # TODO(cyril) not sure this is correct, napari is ZYX usually.
    )  # also see spim.py zoom_factor() in SemanticSegmentation table. might be due to orientation ?

    dock = viewer.window.add_dock_widget(widget)
    dock._close_btn = False
    logger.info("Opening napari dock widget for brainreg")
    viewer.show(block=True)

    return utils.BrainregParams.load_from_json(
        str(DEFAULT_PATH / Path("brainreg.json"))
    )
