import numpy as np
import os
from utils import read_tiff_stack_labels
from skimage import io
from collections import defaultdict


# 1 should be axons and 2 should be artifacts
def process_labels(vol):
    print(vol.shape)
    cells_seen = []
    new_id = 20000
    new_ids = defaultdict(list)
    for i in range(vol.shape[0] - 1):
        slice = vol[i]

        if i == 0:
            slice_instances = list(np.unique(slice))
        next_slice_instances = list(np.unique(vol[i + 1]))
        for slice_instance in slice_instances:
            if (
                slice_instance not in next_slice_instances
                and slice_instance not in cells_seen
            ):
                cells_seen.append(slice_instance)
        for next_slice_instance in next_slice_instances:
            if (
                next_slice_instance not in slice_instances
                and next_slice_instance in cells_seen
            ):
                print(i, next_slice_instance)
                vol[i + 1][vol[i + 1] == next_slice_instance] = new_id
                new_ids[str(next_slice_instance)].append(new_id)
                new_id += 1
            if str(next_slice_instance) in new_ids.keys():
                # print("changingvalue", next_slice_instance, new_ids.keys())
                vol[i + 1][vol[i + 1] == next_slice_instance] = new_ids[
                    str(next_slice_instance)
                ][-1]

        slice_instances = next_slice_instances
        # Add if connected to instance in the x y direction
        # # slice[slice==slice_instance]
        # for x in range(1, slice.shape[0] - 1):
        #     for y in range(1, slice.shape[1] - 1):
        #         if slice[x][y] == 0 and is_axon_close(slice, x, y, slice_instance):
        #
        #             slice[x][y] = 2

    return vol


# def is_axon_close(slice, x, y, instance):
#     return slice[x][y + 1] == instance or slice[x + 1][y + 1] == instance or slice[x + 1][y] == instance or slice[x + 1][y - 1] == instance or \
#            slice[x][y - 1] == instance or \
#            slice[x - 1][y - 1] == instance or slice[x - 1][y] == instance or slice[x - 1][y + 1] == instance


base_path = "/home/maximevidal/Documents/cell-segmentation-models/data/validation_new_labels"
labels_paths = [
    "c5labels.tif"
]  # ["c1labels.tif", "c2labels.tif", "c3labels.tif", "c4labels.tif", "v1clabels.tif"]
new_labels_path = "/home/maximevidal/Documents/cell-segmentation-models/data/validation_new_labels/"
os.makedirs(new_labels_path, exist_ok=True)

for label_path in labels_paths:
    label = read_tiff_stack_labels(os.path.join(base_path, label_path))
    # _, count = np.unique(label,return_counts=True)
    new_vol = process_labels(label)
    # io.imsave(
    #     os.path.join(new_labels_path, label_path),
    #     new_vol,
    # )
