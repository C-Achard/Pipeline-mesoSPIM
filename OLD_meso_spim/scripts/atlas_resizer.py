# Script to resize atlas based on related brain
import os
import glob
from tifffile import imread, imwrite
from skimage.transform import resize
from bg_space import map_stack_to

# Prompt user for mouse name
mouse_name = input("Please enter the name of the mouse: ")

# Validate mouse name
if not mouse_name:
    raise ValueError("Mouse name cannot be empty.")

# Paths
brain_image_path_template = f'/data/seb/CFOS_exp/{mouse_name}*Mag1.25x*Ch488*.tiff'
brain_image_path = glob.glob(brain_image_path_template)

# Validate brain image path
if not len(brain_image_path):
    raise FileNotFoundError(f"Brain image for mouse {mouse_name} not found at path: {brain_image_path}")

corresponding_brain_atlas_path = f'/home/cyril/Desktop/results_CFos_1.25x/reg_results_{mouse_name}/'

# Validate atlas path
if not os.path.exists(corresponding_brain_atlas_path):
    raise FileNotFoundError(f"Corresponding brain atlas directory for mouse {mouse_name} not found at path: {corresponding_brain_atlas_path}")

# Get actual shape of main image
try:
    brain_image_shape = imread(brain_image_path).shape
except Exception as e:
    raise IOError(f"Error reading brain image at {brain_image_path}. Error: {str(e)}")

# Get atlas
atlas_path = os.path.join(corresponding_brain_atlas_path, 'registered_atlas.tiff')
if not os.path.exists(atlas_path):
    raise FileNotFoundError(f"Atlas image not found at path: {atlas_path}")

try:
    atlas = imread(atlas_path)
except Exception as e:
    raise IOError(f"Error reading atlas image at {atlas_path}. Error: {str(e)}")

target_space = ["s", "a", "r"]
source_space = ["a", "s", "r"]

# Map atlas and resize it
atlas = map_stack_to(source_space, target_space, atlas, copy=False)
atlas = resize(atlas, brain_image_shape, order=0, preserve_range=True, anti_aliasing=False)

# Save image
output_path = os.path.join(corresponding_brain_atlas_path, f'registered_atlas_resize_{mouse_name}.tiff')
try:
    imwrite(output_path, atlas)
    print(f"Resized atlas saved successfully at: {output_path}")
except Exception as e:
    raise IOError(f"Error writing resized atlas to {output_path}. Error: {str(e)}")
