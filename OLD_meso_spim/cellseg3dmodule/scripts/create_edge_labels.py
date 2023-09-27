import numpy as np
import os
from utils import read_tiff_stack_labels
from skimage import io


# 1 should be axons and 2 should be artifacts
def process_labels(vol):
    print(vol.shape)
    print(np.unique(vol, return_counts=True))
    # vol[vol > 0] = 1
    for i in range(vol.shape[0]):
        slice = vol[i]

        # if np.max(slice) > 0:  # for all non empty slices !
        # print(np.unique(slice))
        # Increment whole slice by 1 to have background be 1
        # slice += 1
        for x in range(1, slice.shape[0] - 1):
            for y in range(1, slice.shape[1] - 1):
                if slice[x][y] == 0 and is_axon_close(slice, x, y):
                    # Set edge label
                    slice[x][y] = 2

    return vol


def is_axon_close(slice, x, y):
    return (
        slice[x][y + 1] == 1
        or slice[x + 1][y + 1] == 1
        or slice[x + 1][y] == 1
        or slice[x + 1][y - 1] == 1
        or slice[x][y - 1] == 1
        or slice[x - 1][y - 1] == 1
        or slice[x - 1][y] == 1
        or slice[x - 1][y + 1] == 1
    )


base_path = "/home/maximevidal/Documents/cell-segmentation-models/data/validation_labels_semantic"
labels_paths = [
    "c5labels.tif"
]  # ["c1labels.tif", "c2labels.tif", "c3labels.tif", "c4labels.tif", "v1clabels.tif"]
edge_labels_path = "/home/maximevidal/Documents/cell-segmentation-models/data/validation_edge_labels/"

os.makedirs(edge_labels_path, exist_ok=True)

for label_path in labels_paths:
    label = read_tiff_stack_labels(os.path.join(base_path, label_path))
    edge_vol = process_labels(label)
    io.imsave(
        os.path.join(edge_labels_path, label_path),
        edge_vol,
    )
    # write_tiff_stack(edge_vol, os.path.join(output_folder, label_name))
