import json
import logging
import os
from pathlib import Path

import bg_space as bg
import imio
import numpy as np
from bg_atlasapi import BrainGlobeAtlas
from brainglobe_utils.general.system import (
    delete_directory_contents,
    ensure_directory_exists,
    get_num_processes,
)
from brainglobe_utils.image.scale import scale_and_convert_to_16_bits
from brainreg.backend.niftyreg.parameters import RegistrationParams
from brainreg.backend.niftyreg.paths import NiftyRegPaths
from brainreg.backend.niftyreg.registration import BrainRegistration
from brainreg.backend.niftyreg.utils import save_nii
from brainreg.exceptions import LoadFileException, path_is_folder_with_one_tiff
from brainreg.paths import Paths
from brainreg.utils import preprocess
from tqdm import trange

with open("brainreg_config.json", "r") as openfile:
    json_object = json.load(openfile)

"""
File for automated brain registration based on brainreg
"""


class Brainreg_data:
    """Class storing relevant data resulting from brain registration necessary to datajoint
    output_directory: directory stroring result files form brain registration
    atlas: atlas name
    voxel_size_x: voxel size in x
    voxel_size_y: voxel size in y
    voxel_size_z: voxel size in z
    orientation: orientation of the brain accroding to brainreg sepecification.
    """

    def __init__(self, output_directory, atlas, voxel_sizes, orientation):
        self.output_directory = output_directory
        self.atlas = atlas
        self.voxel_size_x = voxel_sizes[1]
        self.voxel_size_y = voxel_sizes[2]
        self.voxel_size_z = voxel_sizes[0]
        self.orientation = orientation


def crop_atlas(atlas, brain_geometry):
    """Brainreg function."""
    atlas_cropped = BrainGlobeAtlas(atlas.atlas_name)
    if brain_geometry == "hemisphere_l":
        ind = atlas_cropped.right_hemisphere_value
    elif brain_geometry == "hemisphere_r":
        ind = atlas_cropped.left_hemisphere_value

    atlas_cropped.reference[atlas_cropped.hemispheres == ind] = 0
    atlas_cropped.annotation[atlas_cropped.hemispheres == ind] = 0

    return atlas_cropped


def filtering(brain, preprocessing=None):
    """Brainreg function."""
    brain = brain.astype(np.float64, copy=False)
    if preprocessing and preprocessing == "skip":
        pass
    else:
        for i in trange(brain.shape[-1], desc="filtering", unit="plane"):
            brain[..., i] = preprocess.filter_plane(brain[..., i])
    brain = scale_and_convert_to_16_bits(brain)
    return brain


"""
def read_brainreg_json_file():
    with open(BRAINREG_CONFIG_JSON, "r") as openfile:
        json_object = json.load(openfile)
    return json_object
"""


def additional_images_preparation(additional_images):
    """Brainreg function."""
    additional_images_downsample = {}
    if len(additional_images) > 0:
        for _idx, images in enumerate(additional_images):
            name = Path(images).name
            additional_images_downsample[name] = images
    return additional_images_downsample


def registration_preparation(
    input_directory,
    output_directory,
    additional_images,
    atlas,
    orientation,
    voxel_sizes,
    n_free_cpus,
    sort_input_file,
    scaling_rounding_decimals=5,
):
    """Brainreg function."""
    ensure_directory_exists(output_directory)
    additional_images_downsample = additional_images_preparation(
        additional_images
    )
    paths = Paths(output_directory)

    if path_is_folder_with_one_tiff(input_directory):
        raise LoadFileException("single_tiff")

    atlas = BrainGlobeAtlas(atlas)
    source_space = bg.AnatomicalSpace(orientation)

    scaling = []
    for idx, _axis in enumerate(atlas.space.axes_order):
        scaling.append(
            round(
                float(voxel_sizes[idx])
                / atlas.resolution[
                    atlas.space.axes_order.index(source_space.axes_order[idx])
                ],
                scaling_rounding_decimals,
            )
        )

    n_processes = get_num_processes(min_free_cpu_cores=n_free_cpus)
    load_parallel = n_processes > 1

    try:
        target_brain = imio.load_any(
            input_directory,
            scaling[1],
            scaling[2],
            scaling[0],
            load_parallel=load_parallel,
            sort_input_file=sort_input_file,
            n_free_cpus=n_free_cpus,
        )
    except ValueError as error:
        raise LoadFileException(None, error) from None

    target_brain = bg.map_stack_to(
        orientation, atlas.metadata["orientation"], target_brain
    )
    return (
        additional_images_downsample,
        paths,
        atlas,
        n_processes,
        load_parallel,
        target_brain,
        scaling,
    )


def registration(autofluo_scan_path):
    """Brainreg function to perform brain registration on autofluorescence image
    args:
        autfluo_scan_path: path to .tiff autofluorescence file
    returns:
        brg_data (Brainreg_data class).
    """
    input_directory = autofluo_scan_path
    output_directory = json_object["output_directory"]
    additional_images = json_object["additional_images"]
    atlas = json_object["atlas"]
    n_free_cpus = json_object["n_free_cpus"]
    voxel_sizes = json_object["voxel_sizes"]
    brain_geometry = json_object["brain_geometry"]
    orientation = json_object["orientation"]
    preprocessing = json_object["preprocessing"]
    sort_input_file = json_object["sort_input_file"]
    save_orientation = json_object["save_orientation"]
    debug = json_object["debug"]
    affine_n_steps = json_object["affine_n_steps"]
    affine_use_n_steps = json_object["affine_use_n_steps"]
    freeform_n_steps = json_object["freeform_n_steps"]
    freeform_use_n_steps = json_object["freeform_use_n_steps"]
    bending_energy_weight = json_object["bending_energy_weight"]
    grid_spacing = json_object["grid_spacing"]
    smoothing_sigma_reference = json_object["smoothing_sigma_reference"]
    smoothing_sigma_floating = json_object["smoothing_sigma_floating"]
    histogram_n_bins_floating = json_object["histogram_n_bins_floating"]
    histogram_n_bins_reference = json_object["histogram_n_bins_reference"]
    (
        additional_images_downsample,
        paths,
        atlas,
        n_processes,
        load_parallel,
        target_brain,
        scaling,
    ) = registration_preparation(
        input_directory,
        output_directory,
        additional_images,
        atlas,
        orientation,
        voxel_sizes,
        n_free_cpus,
        sort_input_file,
    )
    atlas_orientation = atlas.metadata["orientation"]

    niftyreg_directory = os.path.join(
        paths.registration_output_folder, "niftyreg"
    )

    niftyreg_paths = NiftyRegPaths(niftyreg_directory)

    if brain_geometry != "full":
        atlas_cropped = crop_atlas(atlas, brain_geometry)
        save_nii(
            atlas_cropped.annotation,
            atlas.resolution,
            niftyreg_paths.annotations,
        )
        reference = preprocess.filter_image(atlas_cropped.reference)
    else:
        save_nii(
            atlas.annotation, atlas.resolution, niftyreg_paths.annotations
        )
        reference = preprocess.filter_image(atlas.reference)

    save_nii(atlas.hemispheres, atlas.resolution, niftyreg_paths.hemispheres)
    save_nii(reference, atlas.resolution, niftyreg_paths.brain_filtered)
    save_nii(target_brain, atlas.resolution, niftyreg_paths.downsampled_brain)

    imio.to_tiff(
        scale_and_convert_to_16_bits(target_brain),
        paths.downsampled_brain_path,
    )

    target_brain = filtering(target_brain, preprocessing)
    save_nii(
        target_brain, atlas.resolution, niftyreg_paths.downsampled_filtered
    )

    logging.info("Registering")

    registration_params = RegistrationParams(
        affine_n_steps=affine_n_steps,
        affine_use_n_steps=affine_use_n_steps,
        freeform_n_steps=freeform_n_steps,
        freeform_use_n_steps=freeform_use_n_steps,
        bending_energy_weight=bending_energy_weight,
        grid_spacing=grid_spacing,
        smoothing_sigma_reference=smoothing_sigma_reference,
        smoothing_sigma_floating=smoothing_sigma_floating,
        histogram_n_bins_floating=histogram_n_bins_floating,
        histogram_n_bins_reference=histogram_n_bins_reference,
    )
    brain_reg = BrainRegistration(
        niftyreg_paths, registration_params, n_processes=n_processes
    )

    logging.info("Starting affine registration")
    brain_reg.register_affine()

    logging.info("Starting freeform registration")
    brain_reg.register_freeform()

    logging.info("Starting segmentation")
    brain_reg.segment()

    logging.info("Segmenting hemispheres")
    brain_reg.register_hemispheres()

    logging.info("Generating inverse (sample to atlas) transforms")
    brain_reg.generate_inverse_transforms()

    logging.info("Transforming image to standard space")
    brain_reg.transform_to_standard_space(
        niftyreg_paths.downsampled_brain,
        niftyreg_paths.downsampled_brain_standard_space,
    )

    logging.info("Generating deformation field")
    brain_reg.generate_deformation_field(niftyreg_paths.deformation_field)

    logging.info("Exporting images as tiff")
    imio.to_tiff(
        imio.load_any(niftyreg_paths.registered_atlas_path).astype(
            np.uint32, copy=False
        ),
        paths.registered_atlas,
    )

    if save_orientation:
        registered_atlas = imio.load_any(
            niftyreg_paths.registered_atlas_path
        ).astype(np.uint32, copy=False)
        atlas_remapped = bg.map_stack_to(
            atlas_orientation, orientation, registered_atlas
        ).astype(np.uint32, copy=False)
        imio.to_tiff(
            atlas_remapped, paths.registered_atlas_original_orientation
        )

    imio.to_tiff(
        imio.load_any(niftyreg_paths.registered_hemispheres_img_path).astype(
            np.uint8, copy=False
        ),
        paths.registered_hemispheres,
    )
    imio.to_tiff(
        imio.load_any(niftyreg_paths.downsampled_brain_standard_space).astype(
            np.uint16, copy=False
        ),
        paths.downsampled_brain_standard_space,
    )

    del reference
    del target_brain

    deformation_image = imio.load_any(niftyreg_paths.deformation_field)
    imio.to_tiff(
        deformation_image[..., 0, 0].astype(np.float32, copy=False),
        paths.deformation_field_0,
    )
    imio.to_tiff(
        deformation_image[..., 0, 1].astype(np.float32, copy=False),
        paths.deformation_field_1,
    )
    imio.to_tiff(
        deformation_image[..., 0, 2].astype(np.float32, copy=False),
        paths.deformation_field_2,
    )

    if additional_images_downsample:
        logging.info("Saving additional downsampled images")
        for name, filename in additional_images_downsample.items():
            logging.info(f"Processing: {name}")

            name_to_save = (
                Path(name).stem
                if name.lower().endswith((".tiff", ".tif"))
                else name
            )

            downsampled_brain_path = os.path.join(
                registration_output_folder, f"downsampled_{name_to_save}.tiff"
            )
            tmp_downsampled_brain_path = os.path.join(
                niftyreg_paths.niftyreg_directory,
                f"downsampled_{name_to_save}.nii",
            )
            downsampled_brain_standard_path = os.path.join(
                registration_output_folder,
                f"downsampled_standard_{name_to_save}.tiff",
            )
            tmp_downsampled_brain_standard_path = os.path.join(
                niftyreg_paths.niftyreg_directory,
                f"downsampled_standard_{name_to_save}.nii",
            )

            # do the tiff part at the beginning
            downsampled_brain = imio.load_any(
                filename,
                scaling[1],
                scaling[2],
                scaling[0],
                load_parallel=load_parallel,
                sort_input_file=sort_input_file,
                n_free_cpus=n_free_cpus,
            )

            downsampled_brain = bg.map_stack_to(
                orientation, atlas_orientation, downsampled_brain
            ).astype(np.uint16, copy=False)

            save_nii(
                downsampled_brain, atlas.resolution, tmp_downsampled_brain_path
            )

            imio.to_tiff(downsampled_brain, downsampled_brain_path)

            logging.info("Transforming to standard space")

            brain_reg.transform_to_standard_space(
                tmp_downsampled_brain_path, tmp_downsampled_brain_standard_path
            )

            imio.to_tiff(
                imio.load_any(tmp_downsampled_brain_standard_path).astype(
                    np.uint16, copy=False
                ),
                downsampled_brain_standard_path,
            )
        del atlas

    if not debug:
        logging.info("Deleting intermediate niftyreg files")
        delete_directory_contents(niftyreg_directory)
        os.rmdir(niftyreg_directory)

    brg_data = Brainreg_data(output_directory, atlas, voxel_sizes, orientation)

    return brg_data
