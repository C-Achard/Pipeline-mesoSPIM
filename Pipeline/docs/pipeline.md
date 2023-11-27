# Running the pipeline

The pipeline can be separated in two main data processing components:

- The brain registration (registration, using **brainreg**)
- The cell segmentation (cellseg, using **cellseg3d**)

These are technically independent, but for the purpose of this pipeline they are arranged in dependent tables[^ERD].

The brain registration runs on **a whole brain imaged with autofluorescence**,
whereas cellseg runs on **cropped images with cFOS staining** (from a whole brain scan).

```{figure} ./images/autofluo.png
---
name: autofluo-fig
---
**Example of an autofluorescence scan** Note the consistent color, no regions are really brighter.
*This is ideal for brainreg*.
```

```{figure} ./images/cfos_whole.png
---
name: cfos-fig
---
**Example of a cFOS scan** Note the brighter regions. On the high-res version you'd be able to see ***individual neurons***.
*This is what cellseg has been trained on (cropped regions of it) and is critical for proper segmentation.*
```

This means that in order to test the whole pipeline, you'd need two whole scans of the same brain with different imaging modalities. Furthermore, there are 2 "ways" to run the pipeline. The first one is manual: it requires to create a .py file to declare all the parameters before running the pipeline. The second one is more user-friendly and is based on streamlit.


## (1) Running the pipeline with a python file

We assume that the .py file is created in the **```Pipeline```** folder of the Pipeline-MesoSPIM repository. To ensure that all the modules of the repository are included in the seach path of your .py file, it would be useful to write the following lines at the beginning of your file:

```
import sys
sys.path.append("scripts")
sys.path.append("schema")
```

### Connecting to DataJoint

The module **```login.connectToDatabase```** allows you to connect to DataJoint with the IP address, username and password already specified.

```
import login
login.connectToDatabase()
```

### Determining parameters for the brain registration

As described in the section [Parameters for the brain registration](parameters_brainreg.md), the brainreg algorithm requires a few parameters. In our case, these parameters have to be stored in a dictionary (see code below). The dictionary is then passed to **```scripts.brainreg_config.write_json_file_brainreg```** in order to create a json file that will be used by brainreg. An example code could be:

```
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

### Populating manual tables

As described in the section [Organisation of the DataJoint tables](datajoint_tables.md), the pipeline needs to manually "populate" the tables *Mouse*, *User*, *Scan* and its sub-class *Scan.ROIs* before populating automatic tables downstream. *Mouse* and *User* are declared in **```schema.mice```** and **```schema.user```** respectively, whereas *Scan* and *Scan.ROIs* are declared in **```schema.spim```**  The different keys (parameters) are described in details in [Organisation of the DataJoint tables](datajoint_tables.md). An example code would be:

```
from schema import mice, spim, user

mice.Mouse().insert1(("mouse", 0, "2022-01-01", "U", "WT"), skip_duplicates=True)
user.User().insert1(("cyril", "cyril.achard@epfl.ch"), skip_duplicates=True)

scan = spim.Scan()

cfos_path = path/to/cfos
autofluo_path = path/to/autofluo
time = "2022-01-01 16:16:16"

gobal_names = ["primary visual area", "primary motor area", "retrosplenial area"]
rois_list = determine_ids.extract_ids_of_selected_areas(
    atlas_name="allen_mouse_25um",
    list_global_names=gn
)

test_scan.insert1(
    (
        "mouse",
        0,
        "cyril",
        autofluo_path,
        cfos_path,
        time
    ),
    skip_duplicates=True,
)

test_scan_part = spim.Scan.ROIs()
test_scan_part.insert1((0, rois_list), skip_duplicates=True)
```

ROI IDs can be determined in 3 ways:
- The user can directly give the IDs (number) by refereing to [Brain regions reference](brainreg_atlas_ref.ipynb)
- The user can give the specfic names of the ROIs by refereing to [Brain regions reference](brainreg_atlas_ref.ipynb). To retrieve the list of IDs, the function **```determine_ids.extract_ids_of_selected_areas```** has to be called.
- The user can give "global names" as presented in the example code. The function **```determine_ids.extract_ids_of_selected_areas```** will look for every areas containing the names and return the list of IDs. Of course, the names should respect the nomenclature of the specified atlas.


### Populating automatic tables

The tables *BrainRegistration*, *BrainRegistrationResults*, *BrainRegistrationResults.BrainregROI*, *BrainRegistrationResults.ContinuousRegion* and *Inference* inherit the aforementionned upstream tables and are populated automatically when the **```.populate```** method is called. They represent the last steps of the pipeline. The order in which these tables are sequentially populated should be respected:

```
test_brainreg = spim.BrainRegistration()
test_brainreg.populate()

test_brg_results = spim.BrainRegistrationResults()
test_brg_results.populate()

test_inference = spim.Inference()
test_inference.populate()
```

## (2) Running the pipeline using Streamlit

This approach requires Streamlit and is based on the .py file **```user_inteface```**. After going into the right folder **```Pipeline-mesoSPIM/Pipeline```**, the user should only run in the command line:

```
streamlit run user_interface.py
```

The user should see the following interface whit 4 section, where he respectively has to enter parameters for the brain registration, the mouse, the user and the scan tables. Please go to [Parameters for the brain registration](parameters_brainreg.md) and [Orgnisation of the DataJoint tables](datajoint_tables.md) for more information.

```{figure} ./images/streamlit.png
---
name: interface
---
Interface of Streamlit for defining parameters of the pipeline
```
