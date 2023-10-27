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


class Coordinates:
    def __init__(self, xmin, xmax, ymin, ymax, zmin, zmax):
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax
        self.zmin = zmin
        self.zmax = zmax


class BrainRegions:
    def __init__(self, registred_atlas_path, CFOS_path, roi_ids):
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
        rAtlas = imio.load_any(registred_atlas_path)
        rAtlas = brg_utils.get_roi_labels(roi_ids, rAtlas)
        rAtlas[rAtlas != 0] = 1
        rAtlas_regions, num_regions = label(rAtlas, return_num=True)
        rAtlas_regions = brg_utils.rescale_labels(rAtlas_regions, CFOS_shape)

        return rAtlas_regions, num_regions

    def compute_continuous_regions_coordinates(
        self, rAtlas_regions_upscaled, num_regions
    ):
        Coos = {}
        for roi_id in range(1, num_regions + 1):
            rAtlas_region = np.where(
                rAtlas_regions_upscaled == roi_id,
                rAtlas_regions_upscaled,
                np.zeros_like(rAtlas_regions_upscaled),
            )
            xmin, xmax, ymin, ymax, zmin, zmax = self.find_coordinates_roi(
                rAtlas_region
            )
            coos = Coordinates(xmin, xmax, ymin, ymax, zmin, zmax)
            Coos[str(roi_id)] = coos
        return Coos

    def find_coordinates_roi(self, cfos_roi_image):
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
        for y in range(cfos_roi_image.shape[1] - 1, -1, -1):
            if np.any(
                cfos_roi_image[:, y, :] != 0
            ):  # is it the best approach ???? (or 0.0)????
                ymax = y
                break
        for z in range(cfos_roi_image.shape[2]):
            if np.any(
                cfos_roi_image[:, :, z] != 0
            ):  # is it the best approach ???? (or 0.0)????
                zmin = z
                break
        for z in range(cfos_roi_image.shape[2] - 1, -1, -1):
            if np.any(
                cfos_roi_image[:, :, z] != 0
            ):  # is it the best approach ???? (or 0.0)????
                zmax = z
                break
        return xmin, xmax, ymin, ymax, zmin, zmax

    def extract_continuous_region(self, coordinates, CFOS):
        return CFOS[
            coordinates.xmin : coordinates.xmax + 1,
            coordinates.ymin : coordinates.ymax + 1,
            coordinates.zmin : coordinates.zmax + 1,
        ]

    def extract_continous_regions(self, Coordinates, CFOS):
        CFOS_extracted_regions = {}
        for key in Coordinates:
            CFOS_extracted_regions[key] = self.extract_continuous_region(
                Coordinates[key], CFOS
            )
        return CFOS_extracted_regions
