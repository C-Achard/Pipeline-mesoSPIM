import json
import os

dictionary = {
    "output_directory": os.getcwd(),
    "additional_images": [],
    "atlas": "example_mouse_100um",
    "n_free_cpus": 4,
    "brain_geometry": "full",
    "voxel_sizes": [40, 48, 48],
    "orientation": "spl",
    "preprocessing": "default",
    "sort_input_file": False,
    "save_orientation": False,
    "debug": False,
    "affine_n_steps": 1,
    "affine_use_n_steps": 1,
    "freeform_n_steps": 1,
    "freeform_use_n_steps": 1,
    "bending_energy_weight": 0.95,
    "grid_spacing": 5,
    "smoothing_sigma_reference": -1.0,
    "smoothing_sigma_floating": -1.0,
    "histogram_n_bins_floating": 128,
    "histogram_n_bins_reference": 128,
}

json_object = json.dumps(dictionary, indent=21)

# Writing to sample.json
with open("brainreg_config.json", "w") as outfile:
    outfile.write(json_object)
