# Script to match the cfos brains with their registered homolog brain and cut out regions of interest
# Saves it to a smaller file usable for cell segmentation

import os
import glob
#import napari
import pandas as pd
import numpy as np
from tifffile import imread, imwrite
import time


cfos_images_path = '/data/seb/CFOS_exp/'
registered_brains_path = '/home/cyril/Desktop/results_CFos_1.25x/Registered_Brains'
atlas_ID_dict = '/home/cyril/Desktop/results_CFos_1.25x/allen_mouse_25um_csv_ref.csv'
cropped_regions_output_folder = '/home/cyril/Desktop/results_CFos_1.25x/cropped_regions'

# Either enter Labels or keywords
regions_of_interest = 'primary motor'

# Filter out your regions of interest to get the coresponding labels
df = pd.read_csv(atlas_ID_dict)
filtered_df = df[df['name'].str.contains(regions_of_interest, case=False, na=False)]
area_ids = np.array(filtered_df['id'])

# Find all tiff files in cfos_images_path containing a mouse name followed by Mag1.25x and containing Ch561.
#pattern = os.path.join(cfos_images_path, '*Mag1.25x*Ch561*.tiff')
pattern = os.path.join(cfos_images_path, '*Mag1.25x*Ch488*.tiff')
cfos_tiff_files = glob.glob(pattern)

# Do the same for registered brains
pattern = os.path.join(registered_brains_path, 'registered*.tiff')
registered_brains_tiff_files = glob.glob(pattern)
   
for file_path in cfos_tiff_files:
    start_time = time.time()

    print('brain:', file_path)
    # Load the tiff file
    brain_image = imread(file_path)

    # Extract the mouse name from the file path
    mouse_name = os.path.basename(file_path).split('_Mag1.25x')[0]

    # Find the corresponding atlas_image based on the mouse_name
    matched_atlas_path = [path for path in registered_brains_tiff_files if mouse_name in path]

    if matched_atlas_path and len(matched_atlas_path)==1:
        atlas_image = imread(matched_atlas_path[0]).data
    else:
        print(f"No registered brain found for mouse: {mouse_name}")
        break

    # Create a mask with regions of interest
    print('Create mask')
    mask = np.isin(atlas_image,area_ids) #

    # Corresponding indices
    print('Get indices')
    inds = np.where(mask)

    # 0 all the rest
    print('Zero brain image')
    brain_image[~mask] = 0

    # Finds mins and maxs to get the cropping coordinates
    mins = np.min(inds,axis=1)
    maxs = np.max(inds,axis=1)

    # Get the cropped region
    cropped_region = brain_image[mins[0]:maxs[0], mins[1]:maxs[1], mins[2]:maxs[2]]
    
    # Save the result to a desired location
    output_filename = f"{mouse_name}_ROI_{regions_of_interest}_autofluo.tiff"
    output_path = os.path.join(cropped_regions_output_folder, output_filename)
    print('Saving now')
    imwrite(output_path, cropped_region)
    print('Done')
    print("--- %s seconds ---" % (time.time() - start_time))
    print('Next Brain...')
