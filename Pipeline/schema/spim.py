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
from scipy.sparse import csr_matrix, save_npz
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
class PostProcessing(dj.Manual):
    """The different parameters for the post-processing"""

    definition = """
    -> Scan
    postprocess_key: int
    ---
    threshold = 0.65: double
    spot_sigma = 0.7: double
    outline_sigma = 0.7: double
    clear_small_size = 5: int
    clear_large_objects = 500: int
    """

    def get_postprocessing_config(self, key):
        return inference.PostProcessConfig(
            (self & key).fetch1("threshold"),
            (self & key).fetch1("spot_sigma"),
            (self & key).fetch1("outline_sigma"),
            None,
            (self & key).fetch1("clear_small_size"),
            (self & key).fetch1("clear_large_objects"),
        )


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
        mask: varchar(200)
        mask_shape: longblob
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
        mask_shape: longblob
        x_min : int
        x_max : int
        y_min : int
        y_max : int
        z_min : int
        z_max : int
        """

    def make(self, key):
        roi_ids = (ROIs() & key).fetch1("regions_of_interest_ids")
        id_key = (ROIs() & key).fetch1("ids_key")
        parent_path = (BrainRegistration() & key).fetch1("registration_path")
        registred_atlas_path = parent_path + "/registered_atlas.tiff"
        CFOS_path = (Scan() & key).fetch1("cfos_path")
        brain_regions = rois_brainreg.BrainRegions(
            registred_atlas_path, CFOS_path, roi_ids
        )
        for k, value in brain_regions.Cont_Masks.items():
            if not (
                parent_path
                / Path("mask_cont_reg_" + str(k) + "_ids_key_" + str(id_key))
            ).is_file():
                save_npz(
                    parent_path
                    / Path(
                        "mask_cont_reg_" + str(k) + "_ids_key_" + str(id_key)
                    ),
                    value[0],
                )
        for k, value in brain_regions.ROI_Masks.items():
            if not (parent_path / Path("mask_roi_" + str(k))).is_file():
                save_npz(parent_path / Path("mask_roi_" + str(k)), value[0])
        self.insert1(key)
        BrainRegistrationResults.ContinuousRegion.insert(
            dict(
                key,
                cont_region_id=num,
                mask=parent_path / Path("mask_cont_reg_" + str(num) + ".npz"),
                mask_shape=brain_regions.Cont_Masks[num][1],
                x_min=brain_regions.Cont_Masks[num][2].xmin,
                x_max=brain_regions.Cont_Masks[num][2].xmax,
                y_min=brain_regions.Cont_Masks[num][2].ymin,
                y_max=brain_regions.Cont_Masks[num][2].ymax,
                z_min=brain_regions.Cont_Masks[num][2].zmin,
                z_max=brain_regions.Cont_Masks[num][2].zmax,
            )
            for num in brain_regions.Cont_Masks
        )
        BrainRegistrationResults.BrainregROI.insert(
            dict(
                key,
                roi_id=num,
                mask=parent_path / Path("mask_roi_" + str(num) + ".npz"),
                mask_shape=brain_regions.ROI_Masks[num][1],
                x_min=brain_regions.ROI_Masks[num][2].xmin,
                x_max=brain_regions.ROI_Masks[num][2].xmax,
                y_min=brain_regions.ROI_Masks[num][2].ymin,
                y_max=brain_regions.ROI_Masks[num][2].ymax,
                z_min=brain_regions.ROI_Masks[num][2].zmin,
                z_max=brain_regions.ROI_Masks[num][2].zmax,
            )
            for num in brain_regions.ROI_Masks
        )


@schema
class Segmentation(dj.Computed):
    """Semantic and Instance image segmentation"""

    definition = """  # semantic image segmentation
    -> BrainRegistrationResults.ContinuousRegion
    -> PostProcessing
    ---
    semantic_labels: varchar(200)
    instance_labels: varchar(200)
    stats: varchar(200)
    stats_resized: varchar(200)
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
        results = inference.inference_on_images(reg_cfos)
        post_process = inference.post_processing(
            results, (PostProcessing() & key).get_postprocessing_config(key)
        )

        infer = results[0]
        reg_semantic_labels = infer.semantic_segmentation
        reg_stats = post_process["Not resized"]["stats"]
        reg_stats_resized = post_process["Resized"]["stats"]
        reg_instance_labels = post_process["Not resized"]["labels"]

        df = pd.DataFrame(reg_stats.get_dict())
        df_resized = pd.DataFrame(reg_stats_resized.get_dict())

        parent_path = (BrainRegistration() & key).fetch1("registration_path")
        result_path = parent_path / Path("inference_results")
        if not Path(result_path).is_dir():
            result_path.mkdir()

        result_path_reg = result_path / Path(
            mouse_name
            + "_semantic_cont_reg_"
            + str(cont_region_id)
            + "_ids_key_"
            + str(att)
            + ".tiff"
        )
        imio.to_tiff(reg_semantic_labels, result_path_reg)

        result_path_reg_instance = result_path / Path(
            mouse_name
            + "_instance_seg_cont_reg_"
            + str(cont_region_id)
            + "_ids_key_"
            + str(att)
            + ".tiff"
        )
        imio.to_tiff(reg_instance_labels, result_path_reg_instance)

        result_path_reg_stats = result_path / Path(
            mouse_name
            + "_stats_seg_cont_reg_"
            + str(cont_region_id)
            + "_ids_key_"
            + str(att)
            + ".csv"
        )
        df.to_csv(result_path_reg_stats)

        result_path_reg_stats_resized = result_path / Path(
            mouse_name
            + "_stats_resized_seg_cont_reg_"
            + str(cont_region_id)
            + "_ids_key_"
            + str(att)
            + ".csv"
        )
        df_resized.to_csv(result_path_reg_stats_resized)

        key["semantic_labels"] = result_path_reg
        key["instance_labels"] = result_path_reg_instance
        key["stats"] = result_path_reg_stats
        key["stats_resized"] = result_path_reg_stats_resized
        self.insert1(key)


@schema
class Analysis(dj.Computed):
    """Analysis of the instance segmentation."""

    definition = """
    -> Segmentation
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

        labels_path = (Segmentation() & key).fetch1("instance_labels")
        labels = imio.load_any(labels_path)
        stats_path = (Segmentation() & key).fetch1("stats")
        stats = pd.read_csv(stats_path)

        key["cell_counts"] = np.unique(labels.flatten()).size - 1
        key["density"] = np.nansum(stats["Filling ratio"].values)
        key["image_size"] = stats["Image size"].values
        key["centroids"] = [
            stats["Centroid x"].values,
            stats["Centroid y"].values,
            stats["Centroid z"].values,
        ]
        key["volumes"] = stats["Volume"].values
        key["filled_pixels"] = np.nansum(
            stats["Total object volume (pixels)"].values
        )
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
        roi_name = "Continuous region " + str(roi_id)

        email = (user.User() & key).fetch1("email")
        username = (user.User() & key).fetch1("name")
        stats = (Analysis() & key).get_stats_summary(key)
        labels_path = (Segmentation() & key).fetch1("instance_labels")
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

        # report.send_report()
        report.write_to_csv()

        key["date"] = datetime.today()
        key["stats_summary"] = stats
        key["instance_samples"] = labels

        self.insert1(key)
