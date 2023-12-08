import sys
import logging
from pathlib import Path
import login

sys.path.append("scripts")
sys.path.append("schema")

login.connectToDatabase()

from schema import mice, spim, user
from scripts import brainreg_config, determine_ids

SCAN_PATH = Path("/data/seb/CFOS_exp").resolve()
assert SCAN_PATH.is_dir()
print(SCAN_PATH)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def test_populate():
    brainreg_config.write_json_file_brainreg()

    """Populate all tables as test."""
    test_mouse = mice.Mouse()
    test_mouse.insert1(
        ("mouse_chickadee", 0, "2022-01-01", "U", "WT"), skip_duplicates=True
    )
    test_user = user.User()
    test_user.insert1(
        ("cyril_tit", "cyril.achard@epfl.ch"), skip_duplicates=True
    )

    test_scan = spim.Scan()

    cfos_path = SCAN_PATH / Path(
        "CHICKADEE_Mag1.25x_Tile0_Ch561_Sh0_Rot0.tiff"
    )
    autofluo_path = SCAN_PATH / Path(
        "CHICKADEE_Mag1.25x_Tile0_Ch488_Sh0_Rot0.tiff"
    )
    logger.info(f"File for cFOS : {cfos_path}")
    logger.info(f"File for autofluo : {autofluo_path}")
    time = "2022-01-01 16:16:16"

    test_scan.insert1(
        (
            "mouse_chickadee",
            0,
            "cyril_tit",
            autofluo_path,
            cfos_path,
            time,
        ),
        skip_duplicates=True,
    )
    gn = ["primary visual area", "primary motor area", "retrosplenial area"]
    rois_list = determine_ids.extract_ids_of_selected_areas(
        atlas_name="allen_mouse_25um", list_global_names=gn
    )

    # rois_list = [656, 962, 767]
    test_scan_part = spim.ROIs()
    test_scan_part.insert1(
        (
            "mouse_chickadee",
            0,
            0,
            rois_list,
        ),
        skip_duplicates=True,
    )

    test_scan_postprocess = spim.PostProcessing()
    test_scan_postprocess.insert1(
        (
            "mouse_chickadee",
            0,
            0,
        ),
        skip_duplicates=True,
    )

    logger.info(test_scan)

    test_brainreg = spim.BrainRegistration()
    test_brainreg.populate()

    logger.info(test_brainreg)

    test_brg_results = spim.BrainRegistrationResults()
    test_brg_results.populate()

    logger.info(test_brg_results)

    test_inference = spim.Inference()
    test_inference.populate()

    logger.info(test_inference)

    test_analysis = spim.Analysis()
    test_analysis.populate()

    logger.info(test_analysis)

    test_report = spim.Report()
    test_report.populate()

    logger.info(test_report)


if __name__ == "__main__":
    login.connectToDatabase()
    test_populate()
