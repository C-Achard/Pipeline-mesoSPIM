# TODO

```{note}
Priority/critical items are in **bold**
```

## Data processing:

- **Find a way to use sliding_window_inference without creating bad predictions on window edges.**
  Using the largest window possible without running out of memory could help.
  *See window_size in ```cellseg3dmodule/inference_config.json``` and MONAI's ```sliding_window_inference```*
- **Align cFOS scan using normalization tranforms (the parameters of which can be found in brainreg results). Can apparently be done using
``reg_transform`` from NiftyReg. See [related code on brainreg's GH page](https://github.com/brainglobe/brainreg/blob/87c5d8aca032f65f8fb939da7ca66a9df44726be/brainreg/backend/niftyreg/registration.py#L200)
This is needed to ensure ROIs extracted in the brainreg results match with the cFOS scan. Also having the cFOS scan in normalized space is probably good regardless.**

- **Figure out the best way to extract ROIs.** For now **```scripts.brainreg_utils.split_volumes```** is used to crop each region completely separately.
 It's possible users would want to run segmentation on a fused version of all regions instead.
  Also, to improve cellseg3d performance, there should be as little "empty" (all 0) regions as possible.
  Maybe crop the smallest bounding volume that contains the ROI from cFOS. Still not perfect for regions on the outside of the brain.

```{figure} ./images/sketch_roi_extraction_method.png
---
name: crop-sketch
---
*Rough sketch of a way to crop ROIs that might improve performance of the segmentation.*
```
Otherwise, keeping track of the ROI coordinates in the whole brain referential is probably a great thing to have.
It could be added an ROI secondary key to help with the analysis and inspection of results.

- **Handle anisotropy and orientation robustly.** I'd be in favor of removing any rescaling until the very end. cellseg can run on
 anisotropic data anyway; rescaling is just here as a user convenience and to allow easier review of cells. *See ``zoom`` in inference_config.json*.
 Maybe we also want to reorient all results to a standard orientation *See ``brainreg_utils.reorient_volume``*
 Also remove padding where not necessary, the main requirement being that volume sizes are a power of two. E.g. $256 \times 64 \times 32$ *See SpatialPad in ``predict.py``*

- Better instance segmentation: cell labels can sometimes get fused by the watershed method. Maybe use Voronoi-Otsu.

- Create more config handles via .json files (for pipeline, brainreg default parameters, cellseg3d)
 e.g. in ```scripts.napari_brainreg_ui``` *See ```cellseg3dmodule/inference_config.json``` + ```cellseg3dmodule/config.py``` for an example*

- Later on, we can use the command line version of BRAINREG. This requires Nifti files, so we'd have to write code to convert the data to that file storage.
 This would avoid a lot of issues regarding the napari GUI opening in the middle of the process.

## Storage and user reports/analysis:

- Unify the path storage. For now the FILE_STORAGE variable indicates where to store results in several files, maybe add that to some config file for the pipeline
- Figure out a suitable directory structure. Something like :

  - RESULTS_PATH
    - Results_pipeline_run_{datetime}
      - brainreg_results (*Brainreg* Datajoint table) -> for brainreg (brainreg.json, downsampled.tiff, mapped_atlas.tiff)
      - cropped_regions (*Brainreg.ROI*) -> containing each ROI
        - roi_name_1 -> cropped .tif (name corresponds to brain region reference, see sidebar)
        - roi_name_2
        - ...
      - cellseg results
        - semantic (*SemanticSegmentation*)
        - instance (*Instance Segmentation*)
        - analysis (*Analysis* and *Report* csv + plots for email)

- Format the user report in a nicer way, find a good way to automate results sample cropping & emailing
- Find out if better stats libraries exist. Maybe use napari-nsr to get the stats Dataframe

## Correction:

- Add the possibility for users to correct the prediction, maybe later re-train models based on the corrected data.
 Should be stored separately and shouldn't overwrite any other data. Stats analysis could also be re-computed from correction.
