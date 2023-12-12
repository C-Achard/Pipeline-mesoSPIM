from functools import partial
from pathlib import Path
from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import List
import numpy as np
import logging
import torch
from cellseg_utils import InstanceSegmentationWrapper, LogFixture
from napari_cellseg3d.code_models.instance_segmentation import (
    voronoi_otsu,
    threshold,
    clear_large_objects,
    clear_small_objects,
    volume_stats,
)
from napari_cellseg3d.code_models.worker_inference import InferenceWorker
from napari_cellseg3d.config import (
    InferenceWorkerConfig,
    InstanceSegConfig,
    ModelInfo,
    SlidingWindowConfig,
)
from napari_cellseg3d.utils import resize

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

WINDOW_SIZE = 128

MODEL_INFO = ModelInfo(
    name="SegResNet",
    model_input_size=64,
)

CONFIG = InferenceWorkerConfig(
    device="cuda" if torch.cuda.is_available() else "cpu",
    model_info=MODEL_INFO,
    results_path=str(Path("./results").absolute()),
    compute_stats=False,
    sliding_window_config=SlidingWindowConfig(WINDOW_SIZE, 0.25),
)


@dataclass_json
@dataclass
class PostProcessConfig:
    """Config for post-processing."""

    threshold: float = 0.65
    spot_sigma: float = 0.7
    outline_sigma: float = 0.7
    isotropic_spot_sigma: float = 0.2
    isotropic_outline_sigma: float = 0.2
    anisotropy_correction: List[
        float
    ] = None  # TODO change to actual values, should be a ratio like [1,1/5,1]
    clear_small_size: int = 5
    clear_large_objects: int = 500


def inference_on_images(
    image: np.array, config: InferenceWorkerConfig = CONFIG
):
    """This function provides inference on an image with minimal config.

    Args:
        image (np.array): Image to perform inference on.
        config (InferenceWorkerConfig, optional): Config for InferenceWorker. Defaults to CONFIG, see above.
    """
    # instance_method = InstanceSegmentationWrapper(voronoi_otsu, {"spot_sigma": 0.7, "outline_sigma": 0.7})

    config.post_process_config.zoom.enabled = False
    config.post_process_config.thresholding.enabled = (
        False  # will need to be enabled and set to 0.5 for the test images
    )
    config.post_process_config.instance = InstanceSegConfig(
        enabled=False,
    )

    config.layer = image

    log = LogFixture()
    worker = InferenceWorker(config)
    logger.info(f"Worker config: {worker.config}")

    worker.log_signal.connect(log.print_and_log)
    worker.warn_signal.connect(log.warn)
    worker.error_signal.connect(log.error)

    worker.log_parameters()

    results = []
    # append the InferenceResult when yielded by worker to results
    for result in worker.inference():
        results.append(result)

    return results


def post_processing(
    semantic_segmentation, config: PostProcessConfig = PostProcessConfig()
):
    """Run post-processing on inference results."""
    # if config.anisotropy_correction is None:
    # config.anisotropy_correction = [1, 1, 1 / 5]

    image = semantic_segmentation
    # apply threshold to semantic segmentation
    logger.info(f"Thresholding with {config.threshold}")
    image = threshold(image, config.threshold)
    logger.debug(f"Thresholded image shape: {image.shape}")
    # remove artifacts by clearing large objects
    logger.info(f"Clearing large objects with {config.clear_large_objects}")
    image = clear_large_objects(image, config.clear_large_objects)
    # run instance segmentation
    logger.info(
        f"Running instance segmentation with {config.spot_sigma} and {config.outline_sigma}"
    )
    labels = voronoi_otsu(
        image,
        spot_sigma=config.spot_sigma,
        outline_sigma=config.outline_sigma,
    )
    # clear small objects
    logger.info(f"Clearing small objects with {config.clear_small_size}")
    labels = clear_small_objects(labels, config.clear_small_size).astype(
        np.uint16
    )
    logger.debug(f"Labels shape: {labels.shape}")
    # get volume stats WITH ANISOTROPY
    logger.debug(f"NUMBER OF OBJECTS: {np.max(np.unique(labels))-1}")
    stats_not_resized = volume_stats(labels)
    ######## RUN WITH ANISOTROPY ########
    result_dict = {}
    result_dict["Not resized"] = {
        "labels": labels,
        "stats": stats_not_resized,
    }
    if config.anisotropy_correction is not None:
        logger.info("Resizing image to correct anisotropy")
        image = resize(image, config.anisotropy_correction)
        logger.debug(f"Resized image shape: {image.shape}")
        logger.info("Running labels without anisotropy")
        labels_resized = voronoi_otsu(
            image,
            spot_sigma=config.isotropic_spot_sigma,
            outline_sigma=config.isotropic_outline_sigma,
        )
        logger.info(
            f"Clearing small objects with {config.clear_large_objects}"
        )
        labels_resized = clear_small_objects(
            labels_resized, config.clear_small_size
        ).astype(np.uint16)
        logger.debug(
            f"NUMBER OF OBJECTS: {np.max(np.unique(labels_resized))-1}"
        )
        logger.info("Getting volume stats without anisotropy !")
        stats_resized = volume_stats(labels_resized)
        result_dict["Resized"] = {
            "labels": labels_resized,
            "stats": stats_resized,
        }
    return result_dict


if __name__ == "__main__":
    image = np.random.rand(64, 64, 64)
    results = inference_on_images(image)
    # see InferenceResult for more info on results so you can populate tables from them
    # note that the csv with stats is not saved by default, you need to retrieve it from the results
    post_process = post_processing(results[0].semantic_segmentation)
    import napari

    viewer = napari.Viewer()
    viewer.add_image(image)
    viewer.add_image(results[0].semantic_segmentation)
    viewer.add_labels(post_process["Not resized"]["labels"])
    # viewer.add_labels(post_process["Resized"]["labels"])
    napari.run()
