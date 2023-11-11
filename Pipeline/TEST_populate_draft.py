import sys

sys.path.append("scripts")
sys.path.append("schema")
import logging
from pathlib import Path
import login

login.connectToDatabase()
from schema import mice, spim, user

USER_PATH = Path.home()
SCAN_PATH = USER_PATH / Path("Desktop/Code/BRAINREG_DATA/test_data")

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def test_populate():
    """Populate all tables as test."""
    mice.Mouse().insert1(
        ("mouse", 0, "2022-01-01", "U", "WT"), skip_duplicates=True
    )
    user.User().insert1(
        ("cyril", "cyril.achard@epfl.ch"), skip_duplicates=True
    )

    test_scan = spim.Scan()

    cfos_path = SCAN_PATH / Path("cfos_downsampled.tiff")
    autofluo_path = SCAN_PATH / Path("downsampled.tiff")
    logger.info(f"File for cFOS : {cfos_path}")
    logger.info(f"File for autofluo : {autofluo_path}")
    time = "2022-01-01 16:16:16"

    test_scan.insert1(
        (
            "mouse",
            0,
            "cyril",
            autofluo_path,
            cfos_path,
            time,
        ),
        skip_duplicates=True,
    )
    test_scan_part = spim.Scan.ROI_list()
    test_scan_part.insert1((0, [656, 962, 767]), skip_duplicates=True)

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
