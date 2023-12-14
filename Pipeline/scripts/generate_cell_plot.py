import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scripts import brainreg_utils as brg_utils

logging.basicConfig(level=logging.INFO)


def generate_plot(
    image: np.array, filename: str, result_path: str, threshold: float = 0.9
):
    """Generate 3D plot of the cell segmentation."""
    image[image > threshold] = 1
    image[image <= threshold] = 0
    pred3d = image
    z, x, y = pred3d.nonzero()
    plt.figure(figsize=(10, 10))
    ax = plt.axes(projection="3d")
    ax.scatter3D(x, y, z, c=z, alpha=1)

    roi_name = brg_utils.format_roi_name_to_path(filename)

    (Path(result_path) / "plots").mkdir(parents=False, exist_ok=True)

    result_file_path = str(
        Path(result_path) / f"plots/{roi_name}_cell_plot.png"
    )
    plt.savefig(result_file_path)

    return result_file_path
