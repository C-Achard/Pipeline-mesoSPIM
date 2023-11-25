from functools import partial
from pathlib import Path

import numpy as np
import torch
from cellseg_utils import InstanceSegmentationWrapper, LogFixture
from napari_cellseg3d.code_models.instance_segmentation import voronoi_otsu
from napari_cellseg3d.code_models.workers import InferenceWorker
from napari_cellseg3d.config import (
    InferenceWorkerConfig,
    InstanceSegConfig,
    ModelInfo,
    SlidingWindowConfig,
)

WINDOW_SIZE = 64

MODEL_INFO = ModelInfo(
    name="SegResNet",
    model_input_size=64,
)

CONFIG = InferenceWorkerConfig(
    device="cuda" if torch.cuda.is_available() else "cpu",
    model_info=MODEL_INFO,
    results_path=str(Path("./results").absolute()),
    compute_stats=True,
    sliding_window_config=SlidingWindowConfig(WINDOW_SIZE, 0.25),
)

###### INSTANCE SEGMENTATION ######
SPOT_SIGMA = 0.7
OUTLINE_SIGMA = 0.7


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
        enabled=True,
        method=InstanceSegmentationWrapper(
            method=partial(
                voronoi_otsu,
                spot_sigma=SPOT_SIGMA,
                outline_sigma=OUTLINE_SIGMA,
            ),
            parameters={
                "spot_sigma": SPOT_SIGMA,
                "outline_sigma": OUTLINE_SIGMA,
            },
        ),
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


if __name__ == "__main__":
    image = np.random.rand(64, 64, 64)
    results = inference_on_images(image)
    # see InferenceResult for more info on results so you can populate tables from them
    # note that the csv with stats is not saved by default, you need to retrieve it from the results
