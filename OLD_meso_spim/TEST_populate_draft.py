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
            [
                656,
                962,
                767,
            ],  # id of region, refer to scripts.brainreg_utils.get_atlas_ref_df
        ),
        skip_duplicates=True,
    )

    logger.info(test_scan)

    test_brainreg = spim.BrainRegistration()
    test_brainreg.populate()

    logger.info(test_brainreg)

    """
    test_semantic = spim.SemanticSegmentation()  # semantic
    test_semantic.populate()

    logger.info(test_semantic)

    test_instance = spim.InstanceSegmentation()  # instance
    test_instance.populate()

    logger.info(test_instance)

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
