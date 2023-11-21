"""Draft for the meso spim schema."""
import logging
import imio
from datetime import datetime
from pathlib import Path
import datajoint as dj
import numpy as np
import user
import mice
from utils.path_dataclass import PathConfig
from scripts import rois_brainreg, run_brainreg, inference

# from scripts.napari_brainreg_ui import open_brainreg_window
from tifffile import imread, imwrite

# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
schema = dj.schema("tutorial", locals(), create_tables=True)


@schema
class Scan(dj.Manual):
    """The original .tif/.tiff/.raw scans from the mesoSPIM."""

    definition = """ # The original .tif/.tiff/.raw scans from the mesoSPIM
    -> mice.Mouse
    attempt: int
    ---
    -> user.User
    autofluo_path: varchar(200)
    cfos_path: varchar(200)
    timestamp = CURRENT_TIMESTAMP: timestamp
    """

    def get_shape(self):
        """Returns the shape of the scan."""
        path = (Scan() & self).fetch1("autofluo_path")
        image = imio.load_any(path)
        return image.shape

    class ROIs(dj.Part):
        """The list of ids of regions of interest for segmentation"""

        definition = """
        attempt_modif : int
        ---
        regions_of_interest_ids : longblob
        """


@schema
class BrainRegistration(dj.Computed):
    """Brain registration table. Contains the parameters of brainreg."""

    definition = """ # The map from brainreg
    -> Scan
    ---
    registration_path : varchar(200)
    atlas: varchar(30)
    voxel_size_x = 1.5: double
    voxel_size_y = 1.5: double
    voxel_size_z = 5: double
    orientation = 'sal': char(3)
    """

    def make(self, key):
        """Runs brainreg on the autofluo scan."""
        autofluo_scan_path = (Scan() & key).fetch1("autofluo_path")

        brainreg_data = run_brainreg.registration(autofluo_scan_path)

        key["registration_path"] = brainreg_data.output_directory
        key["atlas"] = brainreg_data.atlas
        key["voxel_size_x"] = brainreg_data.voxel_size_x
        key["voxel_size_y"] = brainreg_data.voxel_size_y
        key["voxel_size_z"] = brainreg_data.voxel_size_z
        key["orientation"] = brainreg_data.orientation
        self.insert1(key)


@schema
class BrainRegistrationResults(dj.Computed):
    """Results of brain registration table. Contains the results of brainreg"""

    definition = """
    -> BrainRegistration
    -> Scan.ROIs
    """

    class BrainregROI(dj.Part):
        """Regions of interest in the brainreg labels"""

        definition = """
        -> BrainRegistrationResults
        roi_id : int
        ---
        x_min : int
        x_max : int
        y_min : int
        y_max : int
        z_min : int
        z_max : int
        """

    class ContinuousRegion(dj.Part):
        """Continuous regions of interest based on brainreg labels"""

        definition = """
        -> BrainRegistrationResults
        cont_region_id : int
        ---
        x_min : int
        x_max : int
        y_min : int
        y_max : int
        z_min : int
        z_max : int
        """

    def make(self, key):
        roi_ids = (Scan.ROIs() & key).fetch1("regions_of_interest_ids")
        registred_atlas_path = (BrainRegistration() & key).fetch1(
            "registration_path"
        ) + "/registered_atlas.tiff"
        CFOS_path = (Scan() & key).fetch1("cfos_path")
        brain_regions = rois_brainreg.BrainRegions(
            registred_atlas_path, CFOS_path, roi_ids
        )
        self.insert1(key)
        BrainRegistrationResults.ContinuousRegion.insert(
            dict(
                key,
                cont_region_id=num,
                x_min=brain_regions.coordinates_regions[num].xmin,
                x_max=brain_regions.coordinates_regions[num].xmax,
                y_min=brain_regions.coordinates_regions[num].ymin,
                y_max=brain_regions.coordinates_regions[num].ymax,
                z_min=brain_regions.coordinates_regions[num].zmin,
                z_max=brain_regions.coordinates_regions[num].zmax,
            )
            for num in brain_regions.coordinates_regions
        )
        BrainRegistrationResults.BrainregROI.insert(
            dict(
                key,
                roi_id=num,
                x_min=brain_regions.coordinates_rois[num].xmin,
                x_max=brain_regions.coordinates_rois[num].xmax,
                y_min=brain_regions.coordinates_rois[num].ymin,
                y_max=brain_regions.coordinates_rois[num].ymax,
                z_min=brain_regions.coordinates_rois[num].zmin,
                z_max=brain_regions.coordinates_rois[num].zmax,
            )
            for num in brain_regions.coordinates_rois
        )


@schema
class Inference(dj.Computed):
    """Semantic image segmentation"""

    definition = """  # semantic image segmentation
    -> BrainRegistrationResults.ContinuousRegion
    ---
    inference_labels: varchar(200)
    """

    def make(self, key):  # from ROI in brainreg
        """Runs cellseg3d on the cFOS scan."""
        cfos_path = (Scan() & key).fetch1("cfos_path")
        att = (Scan.ROIs() & key).fetch1("attempt_modif")
        mouse_name = (mice.Mouse() & key).fetch1("mouse_name")
        reg_x_min = (BrainRegistrationResults.ContinuousRegion() & key).fetch1(
            "x_min"
        )
        reg_x_max = (BrainRegistrationResults.ContinuousRegion() & key).fetch1(
            "x_max"
        )
        reg_y_min = (BrainRegistrationResults.ContinuousRegion() & key).fetch1(
            "y_min"
        )
        reg_y_max = (BrainRegistrationResults.ContinuousRegion() & key).fetch1(
            "y_max"
        )
        reg_z_min = (BrainRegistrationResults.ContinuousRegion() & key).fetch1(
            "z_min"
        )
        reg_z_max = (BrainRegistrationResults.ContinuousRegion() & key).fetch1(
            "z_max"
        )
        cont_region_id = (
            BrainRegistrationResults.ContinuousRegion() & key
        ).fetch1("cont_region_id")
        cfos = imio.load_any(cfos_path)
        reg_cfos = cfos[
            reg_x_min : reg_x_max + 1,
            reg_y_min : reg_y_max + 1,
            reg_z_min : reg_z_max + 1,
        ]
        reg_res = inference.inference_on_images(reg_cfos)[0].result

        parent_path = Path.home() / Path("Desktop/Pipeline-mesoSPIM/Pipeline")
        result_path = parent_path / Path("inference_results")
        if not Path(result_path).is_dir():
            result_path.mkdir()
        result_path_reg = result_path / Path(
            mouse_name
            + "_inference_cont_reg_"
            + str(cont_region_id)
            + "_"
            + str(att)
            + ".tiff"
        )
        imio.to_tiff(reg_res, result_path_reg)

        key["inference_labels"] = result_path_reg
        self.insert1(key)
