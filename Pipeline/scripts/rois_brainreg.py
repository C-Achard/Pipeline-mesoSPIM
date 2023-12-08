from dataclasses import dataclass

import brainreg_utils as brg_utils
import imio
import numpy as np
from skimage.measure import label
from scipy.sparse import csr_matrix


@dataclass
class Coordinates:
    """Cropping coordinates of regions of interest on a 3D array
    xmin --> xmax: delimiting coordinates along first dimension
    ymin --> ymax: delimiting coordinates along second dimension
    zmin --> zmax: delimiting coordinates along third dimension.
    """

    xmin: int
    xmax: int
    ymin: int
    ymax: int
    zmin: int
    zmax: int


class BrainRegions:
    def __init__(self, registred_atlas_path, CFOS_path, roi_ids):
        """Class storing all the required components necessary to run segmentaion on selected brain regions
        CFOS (nump_array): CFOS image
        Atlas_rois (numpy_array): upscaled registred atlas image with ROIs
        Atlas_regions (numpy_array): upscaled registred atlas image with continuous regions
        num_regions (int): number of continuous regions
        coordinates_rois (dict{roi_id : coordinates}): dictionnary of cropping coordinates of ROIs
        coordinates_regions (dict{roi_id : coordinates}): dictionnary of cropping coordinates of cont. regions
        """
        self.CFOS = imio.load_any(CFOS_path)
        Atlas_rois, self.ROI_Masks = self.compute_rois(
            registred_atlas_path, roi_ids, self.CFOS.shape
        )
        self.coordinates_rois = self.compute_coordinates(Atlas_rois, roi_ids)
        del Atlas_rois
        (
            Atlas_regions,
            self.Cont_Masks,
            self.num_regions,
        ) = self.compute_continuous_regions(
            registred_atlas_path, roi_ids, self.CFOS.shape
        )
        self.coordinates_regions = self.compute_coordinates(
            Atlas_regions, range(1, self.num_regions + 1)
        )
        del Atlas_regions

    def compute_rois(self, registred_atlas_path, roi_ids, CFOS_shape):
        """Compute ROIs.

        Args:
            registred_atlas_path (string): path to .tiff atlas file obtained though the brain registration
            rois_ids (list[int]): list of user defined regions of interest labeled on the registred atlas
            CFOS_shape (numpy_array(int)): shape of CFOS image for the rescaling of atlas
        Returns:
            rAtlas_rois (numpy_array(int)): upscaled registred atlas image with ROIs
        """
        whole_brain = len(roi_ids) > 830
        # Load the atlas
        rAtlas = imio.load_any(registred_atlas_path)
        # Select only rehions of interest
        if not whole_brain:
            rAtlas = brg_utils.get_roi_labels(roi_ids, rAtlas)
        # Rescale atlas to the shape of yur CFOS image
        print("Rescaling labels")
        rAtlas_rois = brg_utils.rescale_labels(rAtlas, CFOS_shape)

        Masks = {}
        for roi_id in roi_ids:
            mask = np.isin(rAtlas_rois, roi_id)
            if np.any(mask):
                print("Creating mask for ROI " + str(roi_id))
                Masks[roi_id] = [
                    csr_matrix(mask.reshape(mask.shape[0], -1)),
                    mask.shape,
                ]
            del mask

        return rAtlas_rois, Masks

    def compute_continuous_regions(
        self, registred_atlas_path, roi_ids, CFOS_shape
    ):
        """Compute continuous regions based on selected regions of interests.

        Args:
            registred_atlas_path (string): path to .tiff atlas file obtained though the brain registration
            rois_ids (list[int]): list of user defined regions of interest labeled on the registred atlas
            CFOS_shape (numpy_array(int)): shape of CFOS image for the rescaling of atlas
        Returns:
            rAtlas_regions (numpy_array(int)): upscaled registred atlas image with continuous regions
            num_regions (int): number of continuous regions
        """
        whole_brain = len(roi_ids) > 830
        # Load the atlas
        rAtlas = imio.load_any(registred_atlas_path)
        # Select only regions of interest
        Masks = {}
        if not whole_brain:
            rAtlas = brg_utils.get_roi_labels(roi_ids, rAtlas)
            # Put the id of every selected region to 1, to extract continuous regions
            rAtlas[rAtlas != 0] = 1
            # Determinate continuous regions with label from skimage.measure
            rAtlas_regions, num_regions = label(rAtlas, return_num=True)
            # Rescale atlas to the shape of yur CFOS image
            print("Rescaling labels")
            rAtlas_regions = brg_utils.rescale_labels(
                rAtlas_regions, CFOS_shape
            )
            for roi_id in range(1, num_regions + 1):
                print("Creating mask for continuous region " + str(roi_id))
                mask = np.isin(rAtlas_regions, roi_id)
                Masks[roi_id] = [
                    csr_matrix(mask.reshape(mask.shape[0], -1)),
                    mask.shape,
                ]
                del mask
            return rAtlas_regions, Masks, num_regions
        else:
            rAtlas[rAtlas != 0] = 1
            num_regions = 1
            rAtlas_regions = brg_utils.rescale_labels(
                rAtlas_regions, CFOS_shape
            )
            for roi_id in range(1, num_regions + 1):
                print("Creating mask for continuous region " + str(roi_id))
                mask = np.isin(rAtlas_regions, roi_id)
                Masks[roi_id] = [
                    csr_matrix(mask.reshape(mask.shape[0], -1)),
                    mask.shape,
                ]
                del mask
            return rAtlas_regions, Masks, num_regions

    def compute_coordinates(self, rAtlas_regions_upscaled, list_ids):
        """Compute the coordinates of regions of the upscaled registred atlas.

        Args:
            rAtlas_regions_upscaled (numpy_array(int)): upscaled registred atlas image with continuous regions
            list_ids (int): list of ids for the different regions of interest
        Returns:
            Coos (dict{roi_id : coordinates}): dictionnary of 3D cropping coordinates of continuous regions
        """
        Coos = {}
        for roi_id in list_ids:
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
            Coos[roi_id] = coos

        return Coos
