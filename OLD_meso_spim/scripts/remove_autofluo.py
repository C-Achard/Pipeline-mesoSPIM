import numpy as np
import os
import glob
from tifffile import imread, imwrite

cropped_images_folder = '/home/cyril/Desktop/results_CFos_1.25x/cropped_regions'
brain_region = 'primary motor'


# Find files in folder that contain autofluo in their name
pattern = os.path.join(cropped_images_folder, '*{}_autofluo.tiff'.format(brain_region))
autofluo_tiff_files = glob.glob(pattern)

for autofluo_file in autofluo_tiff_files:
    print('Remove background for:',autofluo_file)
    # Load images
    ## Load background image (autofluo)
    background_image = imread(autofluo_file)
    ## Load cfos image
    cfos_file = autofluo_file.replace('_autofluo', '')
    cfos_image = imread(cfos_file)

    # Convert both into int32 to allow correct sutraction
    background_image = background_image.astype(np.int32)
    cfos_image = cfos_image.astype(np.int32)

    # Background corrected image:
    corrected = cfos_image-background_image

    # Zero all the values lower than 0
    corrected[corrected<0] = 0
    
    corrected = corrected.astype(np.uint16)

    # Save the result to a desired location
    output_filename = autofluo_file.replace('_autofluo', '_backgroundCorrected')
    output_path = os.path.join(cropped_images_folder, output_filename)
    imwrite(output_path, corrected)  

