from functools import partial
from pathlib import Path
from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import List
import numpy as np
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
    print(f"Worker config: {worker.config}")

    worker.log_signal.connect(log.print_and_log)
    worker.warn_signal.connect(log.warn)
    worker.error_signal.connect(log.error)

    worker.log_parameters()

    results = []
    # append the InferenceResult when yielded by worker to results
    for result in worker.inference():
        results.append(result)

    return results


def post_processing(results, config: PostProcessConfig = PostProcessConfig()):
    """Run post-processing on inference results."""
    if config.anisotropy_correction is None:
        config.anisotropy_correction = [1, 1, 1]

    for result in results:
        image = result.result
        # apply threshold to semantic segmentation
        image = threshold(image, config.threshold)
        # remove artifacts by clearing large objects
        image = clear_large_objects(image, config.clear_large_objects)
        # run instance segmentation
        labels = voronoi_otsu(
            image,
            spot_sigma=config.spot_sigma,
            outline_sigma=config.outline_sigma,
        )
        # clear small objects
        labels = clear_small_objects(labels, config.clear_small_size).astype(
            np.uint16
        )
        # get volume stats WITH ANISOTROPY
        stats_not_resized = volume_stats(labels)
        # resize labels to match original image
        labels_resized = resize(labels, config.anisotropy_correction).astype(
            np.uint16
        )
        # get volume stats WITHOUT ANISOTROPY
        stats_resized = volume_stats(labels)

        return {
            "Not resized": {"labels": labels, "stats": stats_not_resized},
            "Resized": {"labels": labels_resized, "stats": stats_resized},
        }
