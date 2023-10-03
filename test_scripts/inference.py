import logging
from pathlib import Path
from typing import List

import torch
from napari_cellseg3d.code_models.worker_inference import InferenceWorker
from napari_cellseg3d.config import (
    InferenceWorkerConfig,
    ModelInfo,
    SlidingWindowConfig,
)
from napari_cellseg3d.utils import LOGGER as logger

############################################
logger.setLevel(logging.DEBUG)
############################################

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
    # post_process_config=
    sliding_window_config=SlidingWindowConfig(WINDOW_SIZE, 0.3),
)


def inference_on_images(
    images: List[str], config: InferenceWorkerConfig = CONFIG
):
    """This functons provides inference on a list of images with minimal config.

    Args:
        images (List[str]): List of image filepaths
        config (InferenceWorkerConfig, optional): Config for InferenceWorker. Defaults to CONFIG, see above.
    """
    config.post_process_config.zoom.enabled = False
    config.post_process_config.thresholding.enabled = False

    config.images_filepaths = images
    for im in config.images_filepaths:
        assert Path(im).exists(), f"Image {im} does not exist"
        print(f"Image : {im}")

    worker = InferenceWorker(config)
    print(f"Worker config: {worker.config}")
    worker._use_thread_logging = False
    assert not worker._use_thread_logging, "Thread logging should be False"

    worker.log_parameters()

    results = []
    # append the InferenceResult when yielded by worker to results
    for result in worker.inference():
        results.append(result)

    return results


if __name__ == "__main__":
    images = sorted(Path.glob(Path("./test_images").resolve(), "*.tif"))

    results = inference_on_images(images)

    for result in results:
        [
            print(f"{attr}: {getattr(result, attr)}")
            for attr in dir(result)
            if not attr.startswith("__")
        ]
