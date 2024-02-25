# Parameters for the brain registration

The brain registration algorithm requires a couple of parameters that have to be determined by the user. For this pipeline, the following parameters have to be set:

## Parameters

- **```output_directory```**: path to directory storing the results of the brain registration
- **```additional_images (optional)```**: list of paths to additional image files to downsample to the same coordinate space
- **```atlas```**: name of the atlas (ex: allen_mouse_10um)
- **```n_free_cups```**: number of CPU cores on the machine to leave unused by the program to spare resources
- **```brain_geometry ("full", "hemisphere_r", "hemisphere_l")```**: option to specify when the brain is not complete and which part it is (can only be right or left hemisphere)
- **```voxel_sizes```**: voxel sizes in microns, in the order of data orientation (3 terms in x,y,z)
- **```orientation```**: orientation of the sample brain according to the BrainGlobe nomenclature
- **```preprocessing```**: pre-processing method to be applied before registration
- **```sort_input_file (True or False)```**: if set to True, the input text file will be sorted using natural sorting
- **```save_original_orientation (True or False)```**: specification for saving the original orientation of the sample brain
- **```debug (True or False)```**: specification for the debug mode
- **```affine_n_steps```**: this parameter determines how many downsampling steps are being performed for the affine registration, with each step halving the data size along each dimension
- **```affine_use_n_steps```**: this parameter determines how many of the downsampling steps defined by "affine-n-steps" will have their registration computed
- **```freeform_n_steps```**: this parameter determines how many downsampling steps are being performed for the freeform registration, with each step halving the data size along each dimension
- **```freeform_use_n_steps```**: this parameter determines how many of the downsampling steps defined by "freeform-n-steps" will have their registration computed
- **```bending_energy_weight```**: bending energy, which is the coefficient of the penalty term, preventing the freeform registration from over-fitting
- **```grid_spacing```**: sets the control point grid spacing in x, y & z.
- **```smoothing_sigma_reference```**: adds a Gaussian smoothing to the brain sample image
- **```smoothing_sigma_floating```**: adds a Gaussian smoothing to the atlas image
- **```histogram_n_bins_floating```**: number of bins used for the generation of the histograms used for the calculation of Normalized Mutual Information on the atlas image.
- **```histogram_n_bins_reference```**: number of bins used for the generation of the histograms used for the calculation of Normalized Mutual Information on the brain sample image

```{tip}
For more information about the different parameters used by the registration algorithm of brainreg, visit its [GitHub page](https://github.com/brainglobe/brainreg)
```

## About brain orientation

Brain orientation is an especially critical parameter for the brain registration and is encoded using three letters that decribe the orientation of the top-most, left-most and front-most voxels of the brain sample.

```{important}
 Both the **letter itself** and the **order of the letters** in the string used to describe the orientation matter.
```

This is described using the following letters:

- **p**/**a** : **posterior/anterior**
- **s**/**i** : **superior/inferior**
- **l**/**r** : **left/right**

Examples : "sal" for "superior, anterior, left" or "pir" for "posterior, inferior, right".

To easily check orientation, either use the corresponding button in the brainreg napari plugin, or use the Streamlit GUI to visualize the brain sample and check the orientation.

## Napari plugin

The same parameters have to be set in the napari plugin of brainreg:

```{figure} ./images/brainreg_param.png
---
name: napari plugin
---
Napari plugin for brainreg
```
