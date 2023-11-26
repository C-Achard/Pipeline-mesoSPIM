import streamlit as st
import sys
import logging
from pathlib import Path
import login
import determine_ids

sys.path.append("scripts")
sys.path.append("schema")

login.connectToDatabase()

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
    attempt = [table["attempt"] for table in query]
    return attempt


def fetch_attempt_scan(name):
    query = spim.Scan() & f"mouse_name='{name}'"
    query = query.fetch(as_dict=True)
    attempt = [table["scan_attempt"] for table in query]
    return attempt


def return_all_list(name, scan_attempt):
    query = (
        spim.Scan.ROIs()
        & f"mouse_name='{name}'"
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
    param1 = st.text_input(
        "path to output directory for brain registration",
        value=Path("").resolve(),
    )
    param2 = []
    param3 = st.selectbox(
        "atlas name",
        ["allen_mouse_50um", "allen_mouse_25um", "allen_mouse_10um"],
    )
    param3_1 = st.number_input(
        "number of free CPUs", value=4, min_value=0, step=1, format="%d"
    )
    param4 = st.selectbox(
        "brain geometry", ["full", "hemisphere_l", "hemisphere_r"]
    )
    param5 = st.number_input("voxel size x", step=0.01, format="%f")
    param6 = st.number_input("voxel size y", step=0.01, format="%f")
    param7 = st.number_input("voxel size z", step=0.01, format="%f")
    param8 = st.text_input("orientation", value="sar")
    param8_1 = st.text_input("preprocessing", value="default")
    param9 = st.checkbox("sort input file", value=False)
    param10 = st.checkbox("save orientation", value=False)
    param11 = st.checkbox("debug", value=False)
    param12 = st.number_input(
        "affine downsampling steps", value=6, min_value=0, step=1, format="%d"
    )
    param13 = st.number_input(
        "affine downsampling steps to use",
        value=5,
        min_value=0,
        step=1,
        format="%d",
    )
    param14 = st.number_input(
        "freeform downsampling steps",
        value=6,
        min_value=0,
        step=1,
        format="%d",
    )
    param15 = st.number_input(
        "freeform downsampling steps to use",
        value=4,
        min_value=0,
        step=1,
        format="%d",
    )
    param16 = st.number_input(
        "bending energy weight", value=0.95, step=0.01, format="%f"
    )
    param17 = st.number_input(
        "grid spacing", value=-10.00, step=0.01, format="%f"
    )
    param18 = st.number_input(
        "smoothing sigma reference", value=1.0, step=0.1, format="%f"
    )
    param19 = st.number_input(
        "smoothing sigma floating", value=1.0, step=0.1, format="%f"
    )
    param20 = st.number_input(
        "number histogram bins floating", value=128, step=1, format="%d"
    )
    param21 = st.number_input(
        "number histogram bins reference", value=128, step=1, format="%d"
    )

    st.header("Parameters of the mouse")
    param23 = st.checkbox("add new attempt", value=False, key=1)
    param22 = st.text_input("mouse name", value="chickadee")
    param24 = st.text_input("date (yyyy-mm-dd)", value="2023-11-11")
    param25 = st.selectbox("sex", ["M", "F", "U"])
    param26 = st.text_input("strain", value="WT")

    st.header("Parameters of the user")
    param27 = st.text_input("name", value="cyril")
    param28 = st.text_input("email", value="cyril.achard@epfl.ch")

    st.header("Parameters of the brain scan")
    param29 = st.checkbox("add new attempt", value=False, key=2)
    param30 = st.text_input(
        "autofluo scan path", value=Path("").resolve() / Path("autofluo.tiff")
    )
    param31 = st.text_input(
        "cFOS scan path", value=Path("").resolve() / Path("cfos.tiff")
    )
    param32 = st.text_input(
        "time (yyyy-mm-dd h:m:sec)", value="2023-11-11 16:16:16"
    )
    param33 = st.selectbox(
        "ROIs",
        [
            "directly give ROI ids",
            "give ROI exact names",
            "give ROI global names (ex, retrosplenial)",
        ],
    )
    rois_ids = []
    if param33 == "directly give ROI ids":
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
    if param33 == "give ROI exact names":
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
            atlas_name=param3, list_atlas_names=gn
        )
    if param33 == "give ROI global names (ex, retrosplenial)":
        strings_input = st.text_input("ROIs", value="Primary motor area")
        gn = []
        if strings_input:
            try:
                gn = [string.strip() for string in strings_input.split("-")]
            except ValueError:
                st.error("Please enter a valid list of ROIs separated by -.")
        rois_ids = determine_ids.extract_ids_of_selected_areas(
            atlas_name=param3, list_global_names=gn
        )

    if st.sidebar.button("RUN PIPELINE"):
        st.sidebar.write("Starting pipeline")
        params = {
            "output_directory": Path(param1).resolve(),
            "additional_images": param2,
            "atlas": param3,
            "n_free_cpus": param3_1,
            "brain_geometry": param4,
            "voxel_sizes": [param5, param6, param7],
            "orientation": param8,
            "preprocessing": param8_1,
            "sort_input_file": param9,
            "save_orientation": param10,
            "debug": param11,
            "affine_n_steps": param12,
            "affine_use_n_steps": param13,
            "freeform_n_steps": param14,
            "freeform_use_n_steps": param15,
            "bending_energy_weight": param16,
            "grid_spacing": param17,
            "smoothing_sigma_reference": param18,
            "smoothing_sigma_floating": param19,
            "histogram_n_bins_floating": param20,
            "histogram_n_bins_reference": param21,
        }
        attempt = fetch_attempt_mouse(param22)
        if not attempt:
            attempt = 0
        else:
            if param23:
                attempt = np.max(attempt) + 1
            else:
                attempt = np.max(attempt)
        scan_attempt = fetch_attempt_scan(param22)
        if not scan_attempt:
            scan_attempt = 0
        else:
            if param29:
                scan_attempt = np.max(scan_attempt) + 1
            else:
                scan_attempt = np.max(scan_attempt)
        list_ids = return_all_list(param22, scan_attempt)
        attempt_roi = 0
        for key in list_ids:
            if compare_lists(list_ids[key], rois_ids):
                attempt_roi = key
                break

        st.sidebar.write("Writing brainreg parameters into JSON file")
        brainreg_config.write_json_file_brainreg(dictionary=params)

        st.sidebar.write("Populating Mouse table")
        mice.Mouse().insert1(
            (param22, attempt, param24, param25, param26), skip_duplicates=True
        )

        st.sidebar.write("Populating User table")
        user.User().insert1((param27, param28), skip_duplicates=True)

        st.sidebar.write("Populating Scan table")
        scan = spim.Scan()

        cfos_path = Path(param31)
        autofluo_path = Path(param30)

        logger.info(f"File for cFOS : {cfos_path}")
        logger.info(f"File for autofluo : {autofluo_path}")

        scan.insert1(
            (
                param22,
                scan_attempt,
                param27,
                autofluo_path,
                cfos_path,
                param32,
            ),
            skip_duplicates=True,
        )

        scan_part = spim.Scan.ROIs()
        scan_part.insert1((attempt_roi, rois_ids), skip_duplicates=True)

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
        st.sidebar.write("Pipeline completed !")


if __name__ == "__main__":
    main()
