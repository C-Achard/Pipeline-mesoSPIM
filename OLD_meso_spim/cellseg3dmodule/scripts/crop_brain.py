import napari
from dask_image.imread import imread
from skimage import io
from utils import read_tiff_stack_labels
import numpy as np
import os

# # c5image
# im = io.imread(
#     "/home/maximevidal/Documents/cell-segmentation-models/data/validation_volumes/c5images.tif"
# )
# print(im.shape)
# im_crop = im[:250, :, :]
# io.imsave(
#     "/home/maximevidal/Documents/cell-segmentation-models/data/cropped_volumes/c51.tif",
#     im_crop,
# )
# im_crop = im[250:, :, :]
# io.imsave(
#     "/home/maximevidal/Documents/cell-segmentation-models/data/cropped_volumes/c52.tif",
#     im_crop,
# )
# # c5label
# os.makedirs("/home/maximevidal/Documents/cell-segmentation-models/data/cropped_labels/",exist_ok=True)
# label = read_tiff_stack_labels( "/home/maximevidal/Documents/cell-segmentation-models/data/labels/c5labels.tif")
#
# print(label.shape)
# label_crop =label[:250, :, :]
# io.imsave(
#     "/home/maximevidal/Documents/cell-segmentation-models/data/cropped_labels/c51_label.tif",
#     label_crop,
# )
# label_crop = label[250:, :, :]
# io.imsave(
#     "/home/maximevidal/Documents/cell-segmentation-models/data/cropped_labels/c52_label.tif",
#     label_crop,
# )

# c5image
im = io.imread(
    "/home/maximevidal/Documents/cell-segmentation-models/data/validation_volumes/c5images.tif"
)
print(im.shape)
im_crop = im[-64:, :, :]
io.imsave(
    "/home/maximevidal/Documents/cell-segmentation-models/data/cropped_volumes/c53.tif",
    im_crop,
)

label = read_tiff_stack_labels(
    "/home/maximevidal/Documents/cell-segmentation-models/data/labels/c5labels.tif"
)
#
print(label.shape)
label_crop = label[-64:, :, :]
io.imsave(
    "/home/maximevidal/Documents/cell-segmentation-models/data/cropped_labels/c53_label.tif",
    label_crop,
)

# im = io.imread("/home/maximevidal/Downloads/braindata/A/ExpA_VIP_ASLM_on.tif")
# im_coronal = np.transpose(im, (2, 0, 1))

# Somatosensorish
# ss_left = im_coronal[950:1375, :1050, :950]
# ss_left_orig = np.transpose(ss_left, (1,2,0))
# io.imsave("/home/maximevidal/Downloads/braindata/A/ss_left.tif",ss_left_orig)
# ss_right = im_coronal[950:1375, :1050, 950:]
# ss_right_orig = np.transpose(ss_right, (1, 2, 0))
# io.imsave("/home/maximevidal/Downloads/braindata/A/ss_right.tif", ss_right_orig)

# Visualish

# visual_left = im_coronal[580:750, :1050, :950]
# visual_left_orig = np.transpose(visual_left, (1, 2, 0))
# io.imsave("/home/maximevidal/Downloads/braindata/A/visual_left.tif", visual_left_orig)
# visual_right = im_coronal[580:750, :1050, 950:]
# visual_right_orig = np.transpose(visual_right, (1, 2, 0))
# io.imsave("/home/maximevidal/Downloads/braindata/A/visual_right.tif", visual_right_orig)


# # Smaller crops
#
# volume = io.imread("/Users/maximevidal/Downloads/sample_0/volume.tif")
# labels = io.imread("/Users/maximevidal/Downloads/sample_0/labels.tif")
# vol_shape = volume.shape
# labels_shape = labels.shape
# assert vol_shape == labels_shape
#
#
#
# # Crop volume
# vol_11 = volume[:int(vol_shape[0] ), :int(vol_shape[1] / 2), :int(vol_shape[2] / 2)]
# vol_12 = volume[:int(vol_shape[0]), :int(vol_shape[1] / 2), int(vol_shape[2] / 2):]
# vol_21 = volume[:int(vol_shape[0]), int(vol_shape[1] / 2):, :int(vol_shape[2] / 2)]
# vol_22 = volume[:int(vol_shape[0]), int(vol_shape[1] / 2):, int(vol_shape[2] / 2):]
#
# io.imsave("/Users/maximevidal/Downloads/sample_0/vol_11.tif", vol_11)
# io.imsave("/Users/maximevidal/Downloads/sample_0/vol_12.tif", vol_12)
# io.imsave("/Users/maximevidal/Downloads/sample_0/vol_21.tif", vol_21)
# io.imsave("/Users/maximevidal/Downloads/sample_0/vol_22.tif", vol_22)
#
# # Crop labels
# labels_11 = labels[:int(vol_shape[0]), :int(vol_shape[1] / 2), :int(vol_shape[2] / 2)]
# labels_12 = labels[:int(vol_shape[0]), :int(vol_shape[1] / 2), int(vol_shape[2] / 2):]
# labels_21 = labels[:int(vol_shape[0]), int(vol_shape[1] / 2):, :int(vol_shape[2] / 2)]
# labels_22 = labels[:int(vol_shape[0]), int(vol_shape[1] / 2):, int(vol_shape[2] / 2):]
#
# io.imsave("/Users/maximevidal/Downloads/sample_0/labels_11.tif", labels_11)
# io.imsave("/Users/maximevidal/Downloads/sample_0/labels_12.tif", labels_12)
# io.imsave("/Users/maximevidal/Downloads/sample_0/labels_21.tif", labels_21)
# io.imsave("/Users/maximevidal/Downloads/sample_0/labels_22.tif", labels_22)
