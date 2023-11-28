import streamlit as st
import numpy as np
import sys
import logging
from pathlib import Path
import login
import determine_ids

sys.path.append("scripts")
sys.path.append("schema")

try:
    login.connectToDatabase()
except Exception as e:
    st.error(
        "Could not connect to the database.\n Troubleshoothing steps:\n"
        + "- Make sure the datajoint docker container is running.\n"
        + "\t - If not, run `docker-compose up` where the database compose file is located.\n"
        + "- Check your credentials in login.py.\n"
        + "\t - Check that the IP and password are correct.\n"
        + "- Contact your network administrator."
    )
    st.stop()

from schema import mice, spim, user
from scripts import brainreg_config

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def compare_lists(list1, list2):
    l1 = set(list1)
    l2 = set(list2)
    return l1 == l2


def fetch_attempt_mouse(name):
    query = mice.Mouse() & f"mouse_name='{name}'"
    query = query.fetch(as_dict=True)
    attempt = [table["mouse_id"] for table in query]
    return attempt


def fetch_attempt_scan(name, mouse_id):
    query = spim.Scan() & f"mouse_name='{name}'" & f"mouse_id='{mouse_id}'"
    query = query.fetch(as_dict=True)
    attempt = [table["scan_attempt"] for table in query]
    return attempt


def return_all_list(name, mouse_id, scan_attempt):
    query = (
        spim.ROIs()
        & f"mouse_name='{name}'"
        & f"mouse_id='{mouse_id}'"
        & f"scan_attempt='{scan_attempt}'"
    )
    query = query.fetch(as_dict=True)
    list_rois = {
        table["ids_key"]: table["regions_of_interest_ids"] for table in query
    }
    return list_rois


def main():
    st.sidebar.write("Connected to DataJoint")
    st.title("DataJoint pipeline for brain registration and segmentation")

    st.header("Parameters of the brain registration")
    brainreg_result_path = st.text_input(
        "Path to output directory for brain registration",
        value=Path("").resolve(),
    )
    additional_files_paths = (
        []
    )  # used to list all additional files, asks to user to input all of them depending on the number of files
    atlas_name = st.selectbox(
        "atlas name",
        ["allen_mouse_50um", "allen_mouse_25um", "allen_mouse_10um"],
    )
    cpus_number = st.number_input(
        "number of free CPUs", value=4, min_value=0, step=1, format="%d"
    )
    brain_geom = st.selectbox(
        "Brain geometry", ["full", "hemisphere_l", "hemisphere_r"]
    )
    voxel_size_x = st.number_input("Voxel size x", step=0.01, format="%f")
    voxel_size_y = st.number_input("Voxel size y", step=0.01, format="%f")
    voxel_size_z = st.number_input("Voxel size z", step=0.01, format="%f")
    orientation_str = st.text_input("Orientation", value="sar")
    preprocessing_params = st.text_input("Preprocessing", value="default")
    sort_input_bool = st.checkbox("Sort input file", value=False)
    save_orientation = st.checkbox("Save orientation", value=False)
    st.header("Advanced parameters of the brain registration")
    debug = st.checkbox("Debug", value=False)
    affine_downsampling_steps = st.number_input(
        "Affine downsampling steps", value=6, min_value=0, step=1, format="%d"
    )
    affine_sampling_steps = st.number_input(
        "Number of ownsampling steps to use for affine registration",
        value=5,
        min_value=0,
        step=1,
        format="%d",
    )
    num_freeform_downsample = st.number_input(
        "Number of freeform downsampling steps",
        value=6,
        min_value=0,
        step=1,
        format="%d",
    )
    number_freeform_downsample_to_use = st.number_input(
        "Number of downsampling steps to use for freeform registration",
        value=4,
        min_value=0,
        step=1,
        format="%d",
    )
    bending_energy_weight = st.number_input(
        "Bending energy weight", value=0.95, step=0.01, format="%f"
    )
    grid_spacing = st.number_input(
        "Grid spacing", value=-10.00, step=0.01, format="%f"
    )
    smoothing_sigma_ref = st.number_input(
        "Smoothing sigma reference", value=1.0, step=0.1, format="%f"
    )
    smoothing_sigma_floating = st.number_input(
        "Smoothing sigma floating", value=1.0, step=0.1, format="%f"
    )
    num_hist_bins = st.number_input(
        "Number histogram bins floating", value=128, step=1, format="%d"
    )
    num_hist_bins_ref = st.number_input(
        "Number histogram bins reference", value=128, step=1, format="%d"
    )

    st.header("Parameters of the mouse")
    add_new_attempt = st.checkbox("Add new attempt", value=False, key=1)
    mouse_name = st.text_input("Mouse name", value="chickadee")
    date_of_mouse = st.text_input("Date (yyyy-mm-dd)", value="2023-11-11")
    mouse_sex = st.selectbox("Sex", ["M", "F", "U"])
    mouse_strain = st.text_input("Strain", value="WT")

    st.header("Parameters of the user")
    username = st.text_input("Name", value="cyril")
    useremail = st.text_input("Email", value="cyril.achard@epfl.ch")

    st.header("Parameters of the brain scan")
    add_new_parameters_brain_scan = st.checkbox(
        "Add new attempt", value=False, key=2
    )
    autofluo_scan_path = st.text_input(
        "Autofluo scan path", value=Path("").resolve() / Path("autofluo.tiff")
    )
    cfos_scan_path = st.text_input(
        "cFOS scan path", value=Path("").resolve() / Path("cfos.tiff")
    )
    scan_time_stamp = st.text_input(
        "Time (yyyy-mm-dd h:m:sec)", value="2023-11-11 16:16:16"
    )
    rois_choice = st.selectbox(
        "ROIs",
        [
            "Give ROI ids",
            "Give ROI exact names",
            "Give ROI global names (ex, retrosplenial)",
        ],
    )
    rois_ids = []
    if rois_choice == "Give ROI ids":
        numbers_input = st.text_input("ROIs", value="656 - 962 - 767")
        if numbers_input:
            try:
                rois_ids = [
                    int(num.strip()) for num in numbers_input.split("-")
                ]
            except ValueError:
                st.error(
                    "Please enter a valid list of numbers separated by -."
                )
    if rois_choice == "Give ROI exact names":
        strings_input = st.text_input(
            "ROIs",
            value="Primary motor area, Layer 6a - Primary motor area, Layer 6b",
        )
        gn = []
        if strings_input:
            try:
                gn = [string.strip() for string in strings_input.split("-")]
            except ValueError:
                st.error("Please enter a valid list of ROIs separated by -.")
        rois_ids = determine_ids.extract_ids_of_selected_areas(
            atlas_name=atlas_name, list_atlas_names=gn
        )
    if rois_choice == "Give ROI global names (ex, retrosplenial)":
        strings_input = st.text_input("ROIs", value="Primary motor area")
        gn = []
        if strings_input:
            try:
                gn = [string.strip() for string in strings_input.split("-")]
            except ValueError:
                st.error("Please enter a valid list of ROIs separated by -.")
        rois_ids = determine_ids.extract_ids_of_selected_areas(
            atlas_name=atlas_name, list_global_names=gn
        )
        bg_atlas = BrainGlobeAtlas(atlas_name, check_latest=False)
        df = bg_atlas.lookup_df
        df["name"] = df["name"].str.lower()
        filtered_df = df[df["id"].isin(rois_ids)]
        st.write("The following areas have been selected")
        st.dataframe(filtered_df)

    if st.sidebar.button("RUN PIPELINE"):
        st.sidebar.write("Starting pipeline")
        params = {
            "output_directory": Path(brainreg_result_path).resolve(),
            "additional_images": additional_files_paths,
            "atlas": atlas_name,
            "n_free_cpus": cpus_number,
            "brain_geometry": brain_geom,
            "voxel_sizes": [voxel_size_x, voxel_size_y, voxel_size_z],
            "orientation": orientation_str,
            "preprocessing": preprocessing_params,
            "sort_input_file": sort_input_bool,
            "save_orientation": save_orientation,
            "debug": debug,
            "affine_n_steps": affine_downsampling_steps,
            "affine_use_n_steps": affine_sampling_steps,
            "freeform_n_steps": num_freeform_downsample,
            "freeform_use_n_steps": number_freeform_downsample_to_use,
            "bending_energy_weight": bending_energy_weight,
            "grid_spacing": grid_spacing,
            "smoothing_sigma_reference": smoothing_sigma_ref,
            "smoothing_sigma_floating": smoothing_sigma_floating,
            "histogram_n_bins_floating": num_hist_bins,
            "histogram_n_bins_reference": num_hist_bins_ref,
        }
        attempt = fetch_attempt_mouse(mouse_name)
        if not attempt:
            attempt = 0
        else:
            if add_new_attempt:
                attempt = np.max(attempt) + 1
            else:
                attempt = np.max(attempt)
        scan_attempt = fetch_attempt_scan(mouse_name, attempt)
        if not scan_attempt:
            scan_attempt = 0
        else:
            if add_new_parameters_brain_scan:
                scan_attempt = np.max(scan_attempt) + 1
            else:
                scan_attempt = np.max(scan_attempt)
        list_ids = return_all_list(mouse_name, attempt, scan_attempt)
        attempt_roi = 0
        for key in list_ids:
            if compare_lists(list_ids[key], rois_ids):
                attempt_roi = key
                break

        st.sidebar.write("Writing brainreg parameters into JSON file")
        brainreg_config.write_json_file_brainreg(dictionary=params)

        st.sidebar.write("Populating Mouse table")
        mice.Mouse().insert1(
            (
                mouse_name.lower(),
                attempt,
                date_of_mouse,
                mouse_sex,
                mouse_strain,
            ),
            skip_duplicates=True,
        )

        st.sidebar.write("Populating User table")
        user.User().insert1((username, useremail), skip_duplicates=True)

        st.sidebar.write("Populating Scan table")
        scan = spim.Scan()

        cfos_path = Path(cfos_scan_path)
        autofluo_path = Path(autofluo_scan_path)

        logger.info(f"File for cFOS : {cfos_path}")
        logger.info(f"File for autofluo : {autofluo_path}")

        scan.insert1(
            (
                mouse_name.lower(),
                scan_attempt,
                username,
                autofluo_path,
                cfos_path,
                scan_time_stamp,
            ),
            skip_duplicates=True,
        )

        scan_part = spim.ROIs()
        scan_part.insert1(
            (
                mouse_name.lower(),
                scan_attempt,
                username,
                autofluo_path,
                cfos_path,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                attempt_roi,
                rois_ids,
            ),
            skip_duplicates=True,
        )

        logger.info(scan)

        st.sidebar.write("Starting brain registration")
        brainreg = spim.BrainRegistration()
        brainreg.populate()

        logger.info(brainreg)

        st.sidebar.write("Extracting coordinates of ROIs")
        brg_results = spim.BrainRegistrationResults()
        brg_results.populate()

        logger.info(brg_results)

        st.sidebar.write("Starting segmentation")
        inference = spim.Inference()
        inference.populate()

        logger.info(inference)

        analysis = spim.Analysis()
        analysis.populate()

        report = spim.Report()
        report.populate()

        st.sidebar.write("Pipeline completed !")


if __name__ == "__main__":
    main()
