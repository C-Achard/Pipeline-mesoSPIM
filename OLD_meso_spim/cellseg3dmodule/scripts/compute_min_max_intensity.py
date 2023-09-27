import napari
from dask_image.imread import imread
from skimage import io
from utils import read_tiff_stack_labels
import numpy as np
import os

base_path = "/home/maximevidal/Documents/cell-segmentation-models/data/volumes"
images_paths = [
    "c1images.tif",
    "c2images.tif",
    "c3images.tif",
    "c4images.tif",
    "c5images.tif",
    "images.tif",
]

for image_path in images_paths:
    im = io.imread(os.path.join(base_path, image_path))
    print(image_path, np.min(im), np.max(im), im.shape)
