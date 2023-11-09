"""Draft for the meso spim schema."""

import logging
from datetime import datetime
from pathlib import Path

import datajoint as dj
import numpy as np
from schema import user
from schema.utils.path_dataclass import PathConfig
from scripts import generate_report
from Brain_registration import rois_brainreg, run_brainreg
import imio

# from scripts.napari_brainreg_ui import open_brainreg_window
from tifffile import imread, imwrite

# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# 127.0.0.1
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

    class ROI_list(dj.Part):
        """The list of ids of regions of interest for segmentation"""

        defintion = """
        -> Scan
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

        brainreg_data = run_brg.registration(autofluo_scan_path)

        key["registration_path"] = brainreg_data.output_directory
        key["atlas"] = brainreg_data.atlas
        key["voxel_size_x"] = brainreg_data.voxel_size_x
        key["voxel_size_y"] = brainreg_data.voxel_size_y
        key["voxel_size_z"] = brainreg_data.voxel_size_z  # A DISCUTER
        key["orientation"] = brainreg_data.orientation
        self.insert1(key)


@schema
class BrainRegistrationResults(dj.Computed):
    """Results of brain registration table. Contains the results of brainreg"""

    definition = """
    -> BrainRegistration
    -> Scan.ROI_list
    """

    def make(self, key):
        roi_ids = (Scan.ROI_list() & self).fetch1("regions_of_interest_ids")
        registred_atlas_path = (BrainRegistration() & self).fetch1(
            "registration_path"
        ) + "/registered_atlas.tiff"
        CFOS_path = (Scan() & key).fetch1("cfos_path")
        brain_regions = rois_brg.BrainRegions(
            registred_atlas_path, CFOS_path, roi_ids
        )
        BrainRegistrationResults.Continuous_Region.insert(
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
        BrainRegistrationResults.Brainreg_ROI.insert(
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

    class Brainreg_ROI(dj.Part):
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

    class Continuous_Region(dj.Part):
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


@schema
class SemanticSegmentation(dj.Computed):
    """Semantic image segmentation."""

    definition = """  # semantic image segmentation
    -> BrainRegistration.ROI
    ---
    semantic_labels: varchar(200)
    """

    def make(self, key):  # from ROI in brainreg
        """Runs cellseg3d on the cFOS scan."""
        roi_volume_path = (BrainRegistration.ROI() & key).fetch1(
            "roi_volume_path"
        )
        roi_id = (BrainRegistration.ROI() & key).fetch1("roi_id")
        voxel_x = (BrainRegistration() & key).fetch1("voxel_size_x")
        voxel_y = (BrainRegistration() & key).fetch1("voxel_size_y")
        voxel_z = (BrainRegistration() & key).fetch1("voxel_size_z")
        cFOS_scan = imread(roi_volume_path)

        config = CELLSEG_CONFIG
        config.image = cFOS_scan

        zoom = zoom_factor(
            [voxel_x, voxel_z, voxel_y]
        )  # TODO(cyril) fix orientation. also see napari_brainreg_ui
        logger.debug(f"zoom : {zoom}")
        config.post_process_config.zoom.zoom_values = zoom

        config.results_path = FILE_STORAGE

        logger.info(f"Starting prediction on : {roi_volume_path}")

        inference_worker = Inference(config)
        result_path = inference_worker.inference(image_id=roi_id)

        key["semantic_labels"] = result_path
        self.insert1(key)


@schema
class InstanceSegmentation(dj.Computed):
    """Instance image segmentation."""

    definition = """  # instance image segmentation
    -> SemanticSegmentation
    ---
    instance_labels: varchar(200)
    """

    def make(self, key):
        """Runs instance segmentation on the semantic labels."""
        config = CELLSEG_CONFIG
        inference_worker = Inference(config)

        labels_path = (SemanticSegmentation() & key).fetch1("semantic_labels")
        semantic_labels = imread(labels_path)

        roi_id = (BrainRegistration.ROI() & key).fetch1("roi_id")
        key["instance_labels"] = inference_worker.instance_seg(
            semantic_labels, image_id=roi_id
        )
        self.insert1(key)


@schema
class Analysis(dj.Computed):
    """Analysis of the instance segmentation."""

    definition = """
    -> InstanceSegmentation
    ---
    cell_counts : int
    filled_pixels: int
    density: float
    image_size: longblob
    centroids: longblob
    volumes: longblob
    sphericity: longblob
    """

    # type for storage ? in table ?

    def make(self, key):
        """Runs analysis on the instance segmentation."""
        labels_path = (InstanceSegmentation & key).fetch1("instance_labels")

        labels = imread(labels_path)

        stats = volume_stats(labels)

        key["cell_counts"] = (
            np.unique(labels.flatten()).size - 1
        )  # remove background
        key["density"] = stats.filling_ratio
        key["image_size"] = stats.image_size
        key["centroids"] = [
            stats.centroid_x,
            stats.centroid_y,
            stats.centroid_z,
        ]
        key["volumes"] = stats.volume
        key["filled_pixels"] = stats.total_filled_volume
        key["sphericity"] = stats.sphericity_ax

        self.insert1(key)

    def get_stats_summary(self, key):
        """Returns all stats to be included in the user report."""
        return (self & key).fetch1()


@schema
class Report(
    dj.Computed
):  # to be sent to user for review. Modality : pdf, cropped cubes..?
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

        roi_id = (BrainRegistration.ROI() & key).fetch1("roi_id")
        roi_name = brg_utils.get_atlas_region_name_from_id(roi_id)

        email = (user.User() & key).fetch1("email")
        username = (user.User() & key).fetch1("name")
        stats = (Analysis() & key).get_stats_summary(key)
        labels_path = (InstanceSegmentation() & key).fetch1("instance_labels")

        labels = imread(labels_path)

        logger.debug(stats)

        report = generate_report.Report(
            email=email,
            user=username,
            scan_name=scan_name,
            roi_name=roi_name,
            results_path=FILE_STORAGE,
            stats_summary=stats,
            labels=labels,
        )

        # report.stats_report()
        report.send_report()
        report.write_to_csv()

        key["date"] = datetime.today()
        key["stats_summary"] = stats
        key["instance_samples"] = labels

        self.insert1(key)


@schema
class Correction(dj.Manual):  # user made corrections to the masks
    """User made corrections to the masks."""

    definition = """
    -> user.User
    -> Report
    date : date
    """
