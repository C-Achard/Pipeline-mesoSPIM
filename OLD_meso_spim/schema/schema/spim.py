"""Draft for the meso spim schema"""

import logging
from datetime import datetime
from pathlib import Path

import datajoint as dj
import numpy as np
import scripts.brainreg_utils as brg_utils
from cellseg3dmodule.config import InferenceWorkerConfig
from cellseg3dmodule.predict import Inference
from cellseg3dmodule.utils import volume_stats
from cellseg3dmodule.utils import zoom_factor
from schema import mice
from schema import user
from schema.utils.path_dataclass import PathConfig
from scripts import generate_report
from scripts.napari_brainreg_ui import open_brainreg_window
from tifffile import imread
from tifffile import imwrite

# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# 127.0.0.1

# dj.config["stores"] = {
#     "spim_storage": {
#         "protocol": "file",
#         "location": os.path.expanduser("~"),
#     }
# }
schema = dj.schema("tutorial", locals(), create_tables=True)
#################
# USE LINE BELOW TO SET FILE STORAGE JSON LOCATION
#################
FILE_STORAGE = PathConfig().load_from_json(
    Path(__file__).parent.resolve() / "path_config.json"
)
#################
# FILE_STORAGE = Path.home() / Path("Desktop/Code/BRAINREG_DATA/test_data")
CELLSEG_CONFIG = InferenceWorkerConfig().load_from_json(
    Path().absolute() / "cellseg3dmodule/inference_config.json"
)


@schema
class Scan(dj.Manual):
    definition = """ # The original .tif/.tiff/.raw scans from the mesoSPIM
    -> mice.Mouse
    attempt: int
    ---
    -> user.User
    autofluo_path: varchar(200) 
    cfos_path: varchar(200) 
    timestamp = CURRENT_TIMESTAMP: timestamp
    regions_of_interest_ids : longblob 
    """

    def get_shape(self):
        path = (Scan() & self).fetch1("autofluo_path")
        # TODO(cyril) check shapes matching between scan files.
        #  Shapes should match, big warning otherwise (no grounds for exception I think)
        image = brg_utils.load_volumes(path)
        return image.shape


@schema
class BrainRegistration(dj.Computed):
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

    # result of brainreg

    class ROI(dj.Part):
        definition = """  # Regions of interest resulting from segmentation, cropped from CFOS
        -> BrainRegistration
        roi_id: int unsigned   # roi id
        ---
        roi_volume_path  : varchar(200)   # path to the cFOS volume cropped to the specified ROI
        """

    def make(self, key):
        autofluo_scan_path = (Scan() & key).fetch1("autofluo_path")

        brainreg_data: brg_utils.BrainRegParams = open_brainreg_window(
            autofluo_scan_path
        )  # has to be removed/modified to use command line brainreg

        key["registration_path"] = brainreg_data.path
        key["atlas"] = brainreg_data.atlas
        key["voxel_size_x"] = brainreg_data.voxel_size_x
        key["voxel_size_y"] = brainreg_data.voxel_size_y
        key["voxel_size_z"] = brainreg_data.voxel_size_z
        key["orientation"] = brainreg_data.orientation
        self.insert1(key)

        rois = (Scan() & key).fetch1("regions_of_interest_ids")
        brainreg_labels_path = Path(brainreg_data.path) / Path("registered_atlas.tiff")

        split_volumes = brg_utils.prepare_roi_cfos(
            roi_ids=rois,
            cfos_scan_path=str(autofluo_scan_path),
            brainreg_labels_path=str(brainreg_labels_path),
            original_orientation=brainreg_data.orientation,
            atlas=brainreg_data.atlas,
        )

        attempt = (Scan() & key).fetch1("attempt")
        mouse_name = (Scan() & key).fetch1("mouse_name")

        for roi in rois:
            roi_name = brg_utils.get_atlas_region_name_from_id(roi, brainreg_data.atlas)
            roi_name = brg_utils.format_roi_name_to_path(roi_name)

            folder = Path(autofluo_scan_path).parent / Path(f"{roi_name}")
            folder.mkdir(parents=True, exist_ok=True)

            volume_path = folder / Path(
                f"{roi}_cropped_{brg_utils.get_date_time()}.tif"
            )

            # standard_orientation = brg_utils.get_atlas_orientation(brainreg_data.atlas)
            # logger.info(f"Re-orienting cropped ROI to atlas standard : {standard_orientation}")
            # brg_utils.reorient_volume(split_volumes[str(roi)], brainreg_data.orientation, standard_orientation)
            logger.info(f"Saving ROI volume {volume_path}")
            imwrite(volume_path, split_volumes[str(roi)])

            results_dict = [mouse_name, attempt, int(roi), str(volume_path)]
            logger.debug(f"brainreg label processing results : {results_dict}")
            BrainRegistration.ROI.insert1(results_dict)


@schema
class SemanticSegmentation(dj.Computed):
    definition = """  # semantic image segmentation
    -> BrainRegistration.ROI
    ---
    semantic_labels: varchar(200)
    """

    def make(self, key):  # from ROI in brainreg

        roi_volume_path = (BrainRegistration.ROI() & key).fetch1("roi_volume_path")
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
    definition = """  # instance image segmentation
    -> SemanticSegmentation
    ---
    instance_labels: varchar(200)
    """

    def make(self, key):

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
        labels_path = (InstanceSegmentation & key).fetch1("instance_labels")

        labels = imread(labels_path)

        stats = volume_stats(labels)

        key["cell_counts"] = np.unique(labels.flatten()).size - 1  # remove background
        key["density"] = stats.filling_ratio
        key["image_size"] = stats.image_size
        key["centroids"] = [stats.centroid_x, stats.centroid_y, stats.centroid_z]
        key["volumes"] = stats.volume
        key["filled_pixels"] = stats.total_filled_volume
        key["sphericity"] = stats.sphericity_ax

        self.insert1(key)

    def get_stats_summary(self, key):
        """Returns all stats to be included in the user report"""
        data_dict = (self & key).fetch1()
        return data_dict


@schema
class Report(
    dj.Computed
):  # to be sent to user for review. Modality : pdf, cropped cubes..?
    definition = """
    -> Analysis
    date : date
    ---
    instance_samples : longblob
    stats_summary : longblob 
    """

    def make(self, key):
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
    definition = """
    -> user.User
    -> Report
    date : date
    """
