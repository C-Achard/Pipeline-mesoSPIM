import sys
import logging
from pathlib import Path
import login

sys.path.append("scripts")
sys.path.append("schema")

login.connectToDatabase()
from schema import mice, spim, user
from scripts import *

# USER_PATH = Path.home()
SCAN_PATH = Path("/data/seb/CFOS_exp").resolve()
assert SCAN_PATH.is_file()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def test_populate():
    """Populate all tables as test."""
    mice.Mouse().insert1(
        ("mouse_chickadee", 0, "2022-01-01", "U", "WT"), skip_duplicates=True
    )
    user.User().insert1(
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
    test_scan_part = spim.Scan.ROI_list()
    test_scan_part.insert1(
        ("mouse_chickadee", 0, [656, 962, 767]), skip_duplicates=True
    )

    logger.info(test_scan)

    test_brainreg = spim.BrainRegistration()
    test_brainreg.populate()

    logger.info(test_brainreg)

    test_brg_results = spim.BrainRegistrationResults()
    test_brg_results.populate()

    logger.info(test_brg_results)

    """
    test_inference = spim.Inference()
    test_inference.populate()

    logger.info(test_inference)
    """

    """
    test_stats = (
        spim.Analysis()
    )  # stats on instance seg. : sphericity, centroids, etc...
    test_stats.populate()

    logger.info(test_stats)

    test_report = spim.Report()
    test_report.populate()

    logger.info(test_report)
    """


if __name__ == "__main__":
    login.connectToDatabase()
    test_populate()
