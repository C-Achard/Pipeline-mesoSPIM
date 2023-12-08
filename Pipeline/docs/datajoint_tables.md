# Orgnisation of the DataJoint tables

"""
ADD DIAGRAM
"""

## Scan

This table conceptually represents the brain scan of a given mouse. It is implemented manually and inherits both a *Mouse* and a *User* table that are defined by the user.

A *Scan* table needs:
- An attempt id (unique number for each pipeline run)
- A path to an autofluorescence scan
- A path to a cFOS scan
- A timestamp in YYYY-MM-DD h:m:s format (e.g. *2022-01-01 16:03:15*)

```
@schema
class Scan(dj.Manual):
    """The original .tif/.tiff/.raw scans from the mesoSPIM."""

    definition = """ # The original .tif/.tiff/.raw scans from the mesoSPIM
    -> mice.Mouse
    scan_attempt: int
    ---
    -> user.User
    autofluo_path: varchar(200)
    cfos_path: varchar(200)
    timestamp = CURRENT_TIMESTAMP: timestamp
    """
...
```

### ROIs

This table represents the list of ids of regions of interest defined by the user on which the segmentation will be performed. This table is manually defined by the user, inherits *Scan* and has been initially implemented the avoid the necessity to run the brain registration whenever a new set of ids is given to the pipeline.

A *ROIs* table needs:
- An integer (unique number for each set of ids)
- A list of ids representing labels on a registered atlas

```{note}
The integer representing the set of ids has to be implemented because DataJoint doesn't allow lists as primary keys
```

```
@schema
class ROIs(dj.Part):
     """The list of ids of regions of interest for segmentation"""
     definition = """
     ids_key : int
     ---
     regions_of_interest_ids : longblob
     """
...
```

### Postprocessing

This table represents the different postprocessing parameters that are applied after performing semantic segmenation in order to improve instance segmentation. This table is also manually defined by the user, inherits *Scan* and has been  implemented the avoid the necessity to run the brain registration and compute continuous regions whenever a new set of paramters is given.

A *Postprocessing* table needs:
- An integer (unique number for each set of parametrs)
- A threshold
- A sigma spot
- A sigma outline
- A size for clearing small objects
- A size for clearing large objects

```{note}
The integer representing the set of parameters has to be implemented because DataJoint doesn't allow lists as primary keys
```

```
@schema
class ROIs(dj.Part):
     """The list of ids of regions of interest for segmentation"""
     definition = """
     ids_key : int
     ---
     regions_of_interest_ids : longblob
     """
...
```

## BrainRegistration

This table automatically performs the brain registration on the inherited *Scan* tables.

A *BrainRegistration* table stores:
- The registration path (output directory of brainreg)
- The atlas name (e.g. "allen_mouse_10um")
- The voxel sizes in x,y,z
- The orientation (e.g., "sar")

```
@schema
class BrainRegistration(dj.Computed):
    """Brain registration table. Contains the parameters of brainreg."""

    definition = """ # The map from brainreg
    -> Scan
    ---
    registration_path : varchar(200)
    atlas: varchar(30)
    voxel_size_x = 1.5: double
    voxel_size_y = 1.5: double
    voxel_size_z = 5: double
    orientation = 'sal': char(3)
    """
...
```

```{figure} ./images/atlas.png
---
name: registered-atlas
---
Registered atlas
```

## BrainRegistrationResults

This table inherits both *ROIs* and *BrainRegistration* tables.

```
@schema
class BrainRegistrationResults(dj.Computed):
    """Results of brain registration table. Contains the results of brainreg"""

    definition = """
    -> BrainRegistration
    -> ROIs
    """
...
```

### BrainRegistrationResults.BrainregROI

This table is a subclass of *BrainRegistrationResults* and stores, in the atlas space, the coordinates of the bounding box delimiting the different ROIS defined by the labels given by the user in *ROIs*.

A *BrainRegistrationResults.BrainregROI* table stores:
- The id of a single ROI
- The 3D coordinates (x_min, x_max, y_min, y_max, z_min, z_max) of the bounding box

```
@schema
class BrainRegistrationResults(dj.Computed):
...
    class BrainregROI(dj.Part):
        """Regions of interest in the brainreg labels"""

        definition = """
        -> BrainRegistrationResults
        roi_id : int
        ---
        x_min : int
        x_max : int
        y_min : int
        y_max : int
        z_min : int
        z_max : int
        """
...
```

```{figure} ./images/atlas_roi.png
---
name: registered-atlas-rois
---
Registered atlas cropped with the ROIs determined by the primary motor cortex, the primary visual cortex and the retrosplenial area
```

### BrainRegistrationResults.ContinuousRegion

This table is a subclass of *BrainRegistrationResults* and stores, in the atlas space, the coordinates of the bounding box delimiting the different continuous regions defined by the labels given by the user in *ROIs*. This table has been initially implemented to optimize memory management and some problems encountered with cellseg creating bad predictions on window edges.

A *BrainRegistrationResults.ContinuousRegion* table stores:
- The id of a single continuous region
- The 3D coordinates (x_min, x_max, y_min, y_max, z_min, z_max) of the bounding box

```
@schema
class BrainRegistrationResults(dj.Computed):
...
    class ContinuousRegion(dj.Part):
        """Continuous regions of interest based on brainreg labels"""

        definition = """
        -> BrainRegistrationResults
        cont_region_id : int
        ---
        x_min : int
        x_max : int
        y_min : int
        y_max : int
        z_min : int
        z_max : int
        """
...
```

```{figure} ./images/atlas_cont.png
---
name: registered-atlas-cont
---
Registered atlas cropped with the continuous regions determined by the primary motor cortex, the primary visual cortex and the retrosplenial area. In our case, we have a single continuous region.
```

### Segmentation

This table automatically performes semantic and instance segmentaion on inherited *BrainRegistrationResults.ContinuousRegion* and *PostProcessing* tables. Cropped cFOS images (with background intact) defined by the coordinates of the bounding box are passed to the segmentaion.

An *Inference* table stores:
- The path to semantic labels
- The path to instance labels
- The path to the statistics file
- The path to the statistics file for the resized labels (with anistropy correction)

```{note}
The semantic, instance labels and the statistics files are sored in a directory called "inference_results" in the same folder of the registration output.
```

```
@schema
class Segmentation(dj.Computed):
    """Semantic and Instance image segmentation"""

    definition = """  # semantic image segmentation
    -> BrainRegistrationResults.ContinuousRegion
    -> PostProcessing
    ---
    semantic_labels: varchar(200)
    instance_labels: varchar(200)
    stats: varchar(200)
    stats_resized: varchar(200)
    """
...
```

```{figure} ./images/semantic.png
---
name: inf-semantic
---
Results of the semantic segmentation on the bounding box of the continuous region
```

```{figure} ./images/instance.png
---
name: inf-instance
---
Results of the instance segmentation on the bounding box of the continuous region
```

### Analysis

This table, inheriting *Segmentation*, automatically stores different statistical data from the stats.csv file from *Segmentation*.

An *Analysis* table stores:
- The number of cells segmented in the continuous region
- Number of pixels that are filled
- The density of cells
- The size of the imgage
- The centroids
- The volumes
- The sphericity

```
@schema
class Analysis(dj.Computed):
    """Analysis of the instance segmentation."""

    definition = """
    -> Segmentation
    ---
    cell_counts : int
    filled_pixels: int
    density: float
    image_size: longblob
    centroids: longblob
    volumes: longblob
    sphericity: longblob
    """
...
```

### Report

This last table, inheriting *Analysis* will simply send the summary of the statistical data from *Analysis* at the specified email address.

A *Report* table stores:
- The date
- The instance samples
- The statistics summary

```
@schema
class Report(dj.Computed):
    """Report to be sent to user for review."""

    definition = """
    -> Analysis
    date : date
    ---
    instance_samples : longblob
    stats_summary : longblob
    """
...
```
