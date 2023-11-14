import json
from pathlib import Path

op = Path().resolve() / Path("output_brainreg_chickadee")
if not (op.is_dir()):
    op.mkdir()

dictionary = {
    "output_directory": str(op),
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
    "grid_spacing": 10,
    "smoothing_sigma_reference": 1.0,
    "smoothing_sigma_floating": 1.0,
    "histogram_n_bins_floating": 128,
    "histogram_n_bins_reference": 128,
}

json_object = json.dumps(dictionary, indent=21)

# Writing to sample.json
with open("brainreg_config.json", "w") as outfile:
    outfile.write(json_object)
