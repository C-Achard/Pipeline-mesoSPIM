"""Draft for the meso spim schema."""
import logging
import imio
from datetime import datetime
from pathlib import Path
import datajoint as dj
import numpy as np
import pandas as pd
import user
import mice
from utils.path_dataclass import PathConfig
from scripts import (
    rois_brainreg,
    run_brainreg,
    inference,
    determine_ids,
    generate_report,
)

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
    scan_attempt: int
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


@schema
class ROIs(dj.Manual):
    """The list of ids of regions of interest for segmentation"""

    definition = """
    -> Scan
    ids_key: int
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
    -> ROIs
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
        mask: varchar(200)
        x_min : int
        x_max : int
        y_min : int
        y_max : int
        z_min : int
        z_max : int
        """

    def make(self, key):
        roi_ids = (ROIs() & key).fetch1("regions_of_interest_ids")
        parent_path = (BrainRegistration() & key).fetch1("registration_path")
        registred_atlas_path = parent_path + "/registered_atlas.tiff"
        CFOS_path = (Scan() & key).fetch1("cfos_path")
        brain_regions = rois_brainreg.BrainRegions(
            registred_atlas_path, CFOS_path, roi_ids
        )
        for k, value in brain_regions.Masks.items():
            np.save(parent_path / Path("mask_cont_reg_" + str(k)), value)
        self.insert1(key)
        BrainRegistrationResults.ContinuousRegion.insert(
            dict(
                key,
                cont_region_id=num,
                mask=parent_path / Path("mask_cont_reg_" + str(num)),
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
    semantic_labels: varchar(200)
    instance_labels: varchar(200)
    stats: varchar(200)
    """

    def make(self, key):  # from ROI in brainreg
        """Runs cellseg3d on the cFOS scan."""
        cfos_path = (Scan() & key).fetch1("cfos_path")
        att = (ROIs() & key).fetch1("ids_key")
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
        infer = inference.inference_on_images(reg_cfos)[0]

        reg_res = infer.result
        reg_stats = infer.stats
        reg_instance_labels = infer.instance_labels

        df = pd.DataFrame()
        for stats in reg_stats:
            df = pd.DataFrame(stats.get_dict())
            print(df)

        parent_path = (BrainRegistration() & key).fetch1("registration_path")
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

        result_path_reg_instance = result_path / Path(
            mouse_name
            + "_instance_seg_cont_reg_"
            + str(cont_region_id)
            + "_"
            + str(att)
            + ".tiff"
        )
        imio.to_tiff(reg_instance_labels, result_path_reg_instance)

        result_path_reg_stats = result_path / Path(
            mouse_name
            + "_stats_seg_cont_reg_"
            + str(cont_region_id)
            + "_"
            + str(att)
            + ".csv"
        )
        df.to_csv(result_path_reg_stats)

        key["semantic_labels"] = result_path_reg
        key["instance_labels"] = result_path_reg_instance
        key["stats"] = result_path_reg_stats
        self.insert1(key)


@schema
class Analysis(dj.Computed):
    """Analysis of the instance segmentation."""

    definition = """
    -> Inference
    ---
    cell_counts : int
    filled_pixels: int
    density: float
    image_size: longblob
    centroids: longblob
    volumes: longblob
    sphericity: longblob
    """

    def make(self, key):
        """Runs analysis on the instance segmentation."""

        labels_path = (Inference() & key).fetch1("instance_labels")
        labels = imio.load_any(labels_path)
        stats_path = (Inference() & key).fetch1("stats")
        stats = pd.read_csv(stats_path)

        print(stats["Filling ratio"].values)
        print(stats["Total object volume (pixels)"].values)

        key["cell_counts"] = np.unique(labels.flatten()).size - 1
        key["density"] = stats["Filling ratio"].values
        key["image_size"] = stats["Image size"].values
        key["centroids"] = [
            stats["Centroid x"].values,
            stats["Centroid y"].values,
            stats["Centroid z"].values,
        ]
        key["volumes"] = stats["Volume"].values
        key["filled_pixels"] = stats["Total object volume (pixels)"].values
        key["sphericity"] = stats["Sphericity (axes)"].values

        self.insert1(key)

    def get_stats_summary(self, key):
        """Returns all stats to be included in the user report."""
        return (self & key).fetch1()


@schema
class Report(dj.Computed):
    """Report to be sent to user for review."""

    definition = """
    -> Analysis
    date : date
    ---
    instance_samples : longblob
    stats_summary : longblob
    """

    def make(self, key):
        """Generates a report and sends it to the user."""
        scan_name = (Scan() & key).fetch1("cfos_path")

        roi_id = (BrainRegistrationResults.ContinuousRegion() & key).fetch1(
            "cont_region_id"
        )
        roi_name = brg_utils.get_atlas_region_name_from_id(roi_id)

        email = (user.User() & key).fetch1("email")
        username = (user.User() & key).fetch1("name")
        stats = (Analysis() & key).get_stats_summary(key)
        labels_path = (Inference() & key).fetch1("instance_labels")
        labels = imio.load_any(labels_path)

        parent_path = (BrainRegistration() & key).fetch1("registration_path")
        result_path = parent_path / Path("inference_results")

        logger.debug(stats)

        report = generate_report.Report(
            email=email,
            user=username,
            scan_name=scan_name,
            roi_name=roi_name,
            results_path=result_path,
            stats_summary=stats,
            labels=labels,
        )

        report.send_report()
        report.write_to_csv()

        key["date"] = datetime.today()
        key["stats_summary"] = stats
        key["instance_samples"] = labels

        self.insert1(key)
