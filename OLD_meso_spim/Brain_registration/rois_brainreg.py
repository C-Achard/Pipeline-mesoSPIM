import json
import os
import imio
import logging
import bg_space as bg
import numpy as np
import scripts.brainreg_utils as brg_utils
from pathlib import Path
from bg_atlasapi import BrainGlobeAtlas
from skimage.measure import label
from dataclasses import dataclass


@dataclass
class Coordinates:
    """
    Cropping coordinates of regions of interest on a 3D array
    xmin --> xmax: delimiting coordinates along first dimension
    ymin --> ymax: delimiting coordinates along second dimension
    zmin --> zmax: delimiting coordinates along third dimension
    """

    xmin: int
    xmax: int
    ymin: int
    ymax: int
    zmin: int
    zmax: int


class BrainRegions:
    def __init__(self, registred_atlas_path, CFOS_path, roi_ids):
        """
        Class storing all the required components necessary to run segmentaion on selected brain regions
        CFOS (nump_array): CFOS image
        Atlas_regions (numpy_array): upscaled registred atlas image with continuous regions
        num_regions (int): number of continuous regions
        coordinates_regions (dict{roi_id : coordinates}): dictionnary of cropping coordinates of cont. regions
        CFOS_extracted_regions (dict{roi_id : CFOS image}}): dictionary of cropped CFOS images
        """
        self.CFOS = imio.load_any(CFOS_path)
        self.Atlas_regions, self.num_regions = self.compute_continuous_regions(
            registred_atlas_path, roi_ids, self.CFOS.shape
        )
        self.coordinates_regions = self.compute_continuous_regions_coordinates(
            self.Atlas_regions, self.num_regions
        )
        self.CFOS_extracted_regions = self.extract_continous_regions(
            self.coordinates_regions, self.CFOS
        )

    def compute_continuous_regions(
        self, registred_atlas_path, roi_ids, CFOS_shape
    ):
        """
        Compute continuous regions based on selected regions of interests

        Args:
            registred_atlas_path (string): path to .tiff atlas file obtained though the brain registration
            rois_ids (list[int]): list of user defined regions of interest labeled on the registred atlas
            CFOS_shape (numpy_array(int)): shape of CFOS image for the rescaling of atlas
        Returns:
            rAtlas_regions (numpy_array(int)): upscaled registred atlas image with continuous regions
            num_regions (int): number of continuous regions
        """
        # Load the atlas
        rAtlas = imio.load_any(registred_atlas_path)
        # Select only rehions of interest
        rAtlas = brg_utils.get_roi_labels(roi_ids, rAtlas)
        # Put the id of every selected region to 1, to extract continuous regions
        rAtlas[rAtlas != 0] = 1
        # Determinate continuous regions with label from skimage.measure
        rAtlas_regions, num_regions = label(rAtlas, return_num=True)
        # Rescale atlas to the shape of yur CFOS image
        rAtlas_regions = brg_utils.rescale_labels(rAtlas_regions, CFOS_shape)

        return rAtlas_regions, num_regions

    def compute_continuous_regions_coordinates(
        self, rAtlas_regions_upscaled, num_regions
    ):
        """
        Compute the coordinates of continuous regions of the upscaled registred atlas

        Args:
            rAtlas_regions_upscaled (numpy_array(int)): upscaled registred atlas image with continuous regions
            num_regions (int): number of continous regions
        Returns:
            Coos (dict{roi_id : coordinates}): dictionnary of 3D cropping coordinates of continuous regions
        """
        Coos = {}
        for roi_id in range(1, num_regions + 1):
            # Create a mask with regions of interest
            mask = np.isin(rAtlas_regions_upscaled, roi_id)
            # Corresponding indices
            inds = np.where(mask)
            # Finds mins and maxs to get the cropping coordinates
            mins = np.min(inds, axis=1)
            maxs = np.max(inds, axis=1)
            coos = Coordinates(
                mins[0], maxs[0], mins[1], maxs[1], mins[2], maxs[2]
            )
            Coos[str(roi_id)] = coos

        return Coos

    def extract_continuous_region(self, coordinates, CFOS):
        """
        Extract the cropped CFOS image of your continuous region of interest

        Args:
            coordinates (dataclass): cropping coordinates
            CFOS (nump_array): CFOS image
        Returns:
            cropped CFOS image
        """
        return CFOS[
            coordinates.xmin : coordinates.xmax + 1,
            coordinates.ymin : coordinates.ymax + 1,
            coordinates.zmin : coordinates.zmax + 1,
        ]

    def extract_continous_regions(self, Coordinates, CFOS):
        """
        Extract all the continuous regions of interest from your CFOS image

        Args:
            Coordinates (dict{roi_id : coordinates}): dictionnary of 3D cropping coordinates of continuous regions
            CFOS (nump_array): CFOS image
        Returns:
            CFOS_extracted_regions (dict{roi_id : CFOS image}}): dictionary of cropped CFOS images
        """
        CFOS_extracted_regions = {}
        for key in Coordinates:
            CFOS_extracted_regions[key] = self.extract_continuous_region(
                Coordinates[key], CFOS
            )
        return CFOS_extracted_regions
