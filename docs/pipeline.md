# Pipeline use

## Required data

The pipeline can be separated in two main data processing components:

- The brain registration (with **brainreg**)
- The cell segmentation (with **cellseg3d**)

These are technically independent, but for the purpose of this pipeline they are arranged in dependent tables.

- The brain registration runs on **a whole brain imaged with autofluorescence**

```{figure} ./images/autofluo.png
---
name: autofluo-fig
---
**Example of an autofluorescence scan** Note the consistent color, no regions are really brighter.<br>
*This is ideal for brainreg*.
```

- CellSeg3D runs on **cropped images with a *nuclear* immunofluorescence staining** (from a whole brain scan).

```{figure} ./images/cfos_whole.png
---
name: cfos-fig
---
**Example of a cFOS scan** Note the brighter regions.<br>
On the high-res version you'd be able to see ***individual neurons***.<br>
*This is what cellseg has been trained on (cropped regions of it) and is critical for proper segmentation.*
```

This means that in order to test the whole pipeline, you'd need two whole scans of the same brain with different imaging modalities.

## Running the pipeline

There are 2 "ways" to run the pipeline:

### Running the pipeline using Streamlit (GUI)

This approach requires Streamlit and is based on the .py file **```user_inteface```**.
After going into the right folder **```Pipeline-mesoSPIM/Pipeline```**, the user should only run in the command line:

```python
streamlit run user_interface.py
```

The user should see the following interface, where parameters can be entered for the mouse brain scans, brain registration, the user and the whole post-processing.
Brain orientation can be easily checked as well.

```{tip}
Please refer to [Parameters for the brain registration](parameters_brainreg.md) and [Orgnisation of the DataJoint tables](datajoint_tables.md) for more information.
```

```{figure} ./images/streamlit.png
---
name: interface
---
Interface of Streamlit for defining parameters of the pipeline
```

### Running the pipeline with a python file

We assume that the .py file is created in the **```Pipeline```** folder of the Pipeline-MesoSPIM repository. To ensure that all the modules of the repository are included in the seach path of your .py file, it would be useful to write the following lines at the beginning of your file:

```python
import sys
sys.path.append("scripts")
sys.path.append("schema")
```

#### Connecting to DataJoint

The module **```login.connectToDatabase```** allows you to connect to DataJoint with the IP address, username and password already specified.

```python
import login
login.connectToDatabase()
```

#### Determining parameters for the brain registration

As described in the section [Parameters for the brain registration](parameters_brainreg.md), the brainreg algorithm requires several parameters.
In our case, these parameters have to be stored in a dictionary (see code below).
The dictionary is then passed to **```scripts.brainreg_config.write_json_file_brainreg```** in order to create a json file that will be used by brainreg.

An example code could be:

```python
from scripts import brainreg_config

DICT = {
    "output_directory": path/to/output/directory,
    "additional_images": [],
    "atlas": "allen_mouse_25um",
    "n_free_cpus": 4,
    "brain_geometry": "full",
    "voxel_sizes": [5, 5.26, 5.26],
    "orientation": "sar",
    "preprocessing": "default",
    "sort_input_file": False,
    "save_orientation": False,
    "debug": False,
    "affine_n_steps": 6,
    "affine_use_n_steps": 5,
    "freeform_n_steps": 6,
    "freeform_use_n_steps": 4,
    "bending_energy_weight": 0.95,
    "grid_spacing": -10,
    "smoothing_sigma_reference": 1.0,
    "smoothing_sigma_floating": 1.0,
    "histogram_n_bins_floating": 128,
    "histogram_n_bins_reference": 128,
}

brainreg_config.write_json_file_brainreg(dictionary=DICT)
```

#### Populating manual tables

As described in the section [Organisation of the DataJoint tables](datajoint_tables.md), the pipeline needs to manually "populate" the tables :

- *Mouse*
- *User*
- *Scan* and its dependent classes *ROIs* and *PostProcessing*

before populating automatic tables downstream.
*Mouse* and *User* are declared in **```schema.mice```** and **```schema.user```** respectively, whereas *Scan*,  *ROIs* and *PostProcessing* are declared in **```schema.spim```**.

The different keys (parameters) are described in details in [Organisation of the DataJoint tables](datajoint_tables.md).

An example code would be:

```python
"""Populate all tables as test."""
test_mouse = mice.Mouse()
test_mouse.insert1(
    ("mouse_chickadee", 0, "2022-01-01", "U", "WT"), skip_duplicates=True
)
test_user = user.User()
test_user.insert1(
    ("cyril_tit", "cyril.achard@epfl.ch"), skip_duplicates=True
)

test_scan = spim.Scan()

cfos_path = SCAN_PATH / Path(
    "CHICKADEE_Mag1.25x_Tile0_Ch561_Sh0_Rot0.tiff"
)
autofluo_path = SCAN_PATH / Path(
    "CHICKADEE_Mag1.25x_Tile0_Ch488_Sh0_Rot0.tiff"
)
logger.info(f"File for cFOS : {cfos_path}")
logger.info(f"File for autofluo : {autofluo_path}")
time = "2022-01-01 16:16:16"

test_scan.insert1(
    (
        "mouse_chickadee", # must exist upstream
        0,
        "user_test", # must exist upstream
        autofluo_path,
        cfos_path,
        time,
    ),
    skip_duplicates=True,
)
gn = ["primary visual area", "primary motor area", "retrosplenial area"]
rois_list = determine_ids.extract_ids_of_selected_areas(
    atlas_name="allen_mouse_25um", list_global_names=gn
)
test_scan_part = spim.ROIs()
test_scan_part.insert1(
    (
        "mouse_chickadee",
        0,
        0,
        rois_list,
    ),
    skip_duplicates=True,
)

test_scan_postprocess = spim.PostProcessing()
test_scan_postprocess.insert1(
    (
        "mouse_chickadee",
        0,
        0,
        0.65,
        0.7,
        0.7,
        5,
        500,
    ),
    skip_duplicates=True,
)
```

ROI IDs can be determined in 3 ways:

- The user can directly give the IDs (number) by referring to [Brain regions reference](brainreg_atlas_ref.ipynb)
- The user can give the specfic names of the ROIs by referring to [Brain regions reference](brainreg_atlas_ref.ipynb).
  To retrieve the list of IDs, the function **```determine_ids.extract_ids_of_selected_areas```** has to be called.
- The user can give "global names" as presented in the example code.
  The function **```determine_ids.extract_ids_of_selected_areas```** will look for every areas containing the names and return the list of IDs.
  Of course, the names should respect the nomenclature of the specified atlas.

#### Populating automatic tables

The tables:

- *BrainRegistration*
- *BrainRegistrationResults*
- *BrainRegistrationResults.BrainregROI*
- *BrainRegistrationResults.ContinuousRegion*
- *Inference*
- *Analysis*
- *Report*

inherit the aforementionned upstream tables and are populated automatically when the **```.populate```** method is called.
They represent most of the pipeline. The order in which these tables are sequentially populated should be respected:

```python
# Populate the brain registration
test_brainreg = spim.BrainRegistration()
test_brainreg.populate()

# Populate the brain registration results (ROI and continuous region processing)
test_brg_results = spim.BrainRegistrationResults()
test_brg_results.populate()

# Populate the inference, analysis and report
test_inference = spim.Segmentation()
test_inference.populate()

test_analysis = spim.Analysis()
test_analysis.populate()

test_report = spim.Report()
test_report.populate()
```
