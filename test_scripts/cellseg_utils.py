import logging

import numpy as np
from napari_cellseg3d.utils import LOGGER as logger

############################################
logger.setLevel(logging.DEBUG)
############################################


class InstanceSegmentationWrapper:
    def __init__(self, method, parameters, name="voronoi_otsu"):
        """Creates a wrapper for an instance segmentation method.

        The InstanceMethod class from cellseg3d cannot be used as it is meant to provide Qt widgets for the GUI.
        Since we are not within a QApplication, we cannot use it.
        """
        self.method = method
        self.recorded_parameters = parameters
        self.name = name

    def run_method_from_params(self, image):
        """Runs the method with the RECORDED parameters set in the widget."""
        params = [
            self.recorded_parameters[key] for key in self.recorded_parameters
        ]
        result = self.method(image, *params)
        return np.array(result)

    def _make_list_from_channels(self, image):
        """Makes a list of images from the channels of the input image."""
        if len(image.shape) > 4:
            raise ValueError(
                f"Image has {len(image.shape)} dimensions, but should have at most 4 dimensions (CHWD)"
            )
        if len(image.shape) < 2:
            raise ValueError(
                f"Image has {len(image.shape)} dimensions, but should have at least 2 dimensions (HW)"
            )
        if len(image.shape) == 4:
            image = np.squeeze(image)
            if len(image.shape) == 4:
                return [im for im in image]
        return [image]

    def run_method_on_channels_from_params(self, image):
        """Runs the method on each channel of the image with the RECORDED parameters set in the widget.

        Args:
            image: image data to run method on

        Returns: processed image from self._method
        """
        image_list = self._make_list_from_channels(image)
        result = np.array(
            [self.run_method_from_params(im) for im in image_list]
        )
        return result.squeeze()


class LogFixture:
    """Fixture for napari-less logging, replaces napari_cellseg3d.interface.Log in model_workers."""

    def __init__(self):
        """Creates a LogFixture object."""
        super(LogFixture, self).__init__()

    def print_and_log(self, text, printing=None):
        """Prints and logs text."""
        print(text)

    def warn(self, warning):
        """Logs warning."""
        logger.warning(warning)

    def error(self, e):
        """Logs error."""
        raise (e)
