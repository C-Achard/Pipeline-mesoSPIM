import streamlit as st
import numpy as np
import sys
import logging
from pathlib import Path
import login
from bg_atlasapi import BrainGlobeAtlas
from skimage.transform import resize

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
from scripts import brainreg_config, determine_ids, brainreg_utils

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def check_orientation(
    orientation_str, brain_geom, atlas_name, autofluo_scan_path
):
    """
    Function used to check that the input orientation is correct.
    To do so it transforms the input data into the requested atlas
    orientation, compute the average projection and displays it alongside
    the atlas. It is then easier for the user to identify which dimension
    should be swapped and avoid running the pipeline on wrongly aligned
    data.
    """

    brain_geometry = brain_geom

    # Load atlas and gather data
    atlas = BrainGlobeAtlas(atlas_name)
    if brain_geometry == "hemisphere_l":
        atlas.reference[atlas.hemispheres == atlas.left_hemisphere_value] = 0
    elif brain_geometry == "hemisphere_r":
        atlas.reference[atlas.hemispheres == atlas.right_hemisphere_value] = 0
    input_orientation = orientation_str
    try:
        data = imio.load_any(autofluo_scan_path)
    except Exception as e:
        st.error("Error loading the data. Make sure the path exists")
        st.stop()

    # Transform data to atlas orientation from user input
    data_remapped = bg.map_stack_to(input_orientation, atlas.orientation, data)

    # Compute average projection of atlas and remapped data
    u_proj = []
    u_proja = []
    for i in range(3):
        u_proj.append(np.mean(data_remapped, axis=i))
        u_proja.append(np.mean(atlas.reference, axis=i))

    # Display all projections with somewhat consistent scaling
    col1, col2, col3 = st.columns(3)

    with col1:
        st.image(u_proja[0], caption="Ref. proj. 0", use_column_width=True)

    with col2:
        st.image(u_proja[1], caption="Ref. proj. 1", use_column_width=True)

    with col3:
        st.image(u_proja[2], caption="Ref. proj. 2", use_column_width=True)

    col4, col5, col6 = st.columns(3)

    with col4:
        st.image(
            resize(u_proj[0], u_proja[0].shape),
            caption="Input proj. 0",
            use_column_width=True,
        )

    with col5:
        st.image(
            resize(u_proj[1], u_proja[1].shape),
            caption="Input proj. 1",
            use_column_width=True,
        )

    with col6:
        st.image(
            resize(u_proj[2], u_proja[2].shape),
            caption="Input proj. 2",
            use_column_width=True,
        )


def compare_lists(list1, list2):
    l1 = set(list1)
    l2 = set(list2)
    return l1 == l2


def fetch_attempt_scan(name, username):
    query = spim.Scan() & f"mouse_name='{name}'"
    query = query.fetch(as_dict=True)
    attempt = [table["scan_attempt"] for table in query]
    return attempt


def return_all_list(name, username, scan_attempt):
    query = (
        spim.ROIs() & f"mouse_name='{name}'" & f"scan_attempt='{scan_attempt}'"
    )
    query = query.fetch(as_dict=True)
    list_rois = {
        table["ids_key"]: table["regions_of_interest_ids"] for table in query
    }
    return list_rois


def main():
    st.sidebar.write("Connected to DataJoint")
    st.title("DataJoint pipeline for brain registration and segmentation")

    st.header("Parameters of mouse brain scans")

    mouse_name = st.text_input("Mouse name", value="chickadee")
    mouse_id = st.number_input("Mouse ID", value=0, step=1, format="%d")
    date_of_mouse = st.text_input("Date (yyyy-mm-dd)", value="2023-11-11")
    mouse_sex = st.selectbox("Sex", ["M", "F", "U"])
    mouse_strain = st.text_input("Strain", value="WT")

    autofluo_paths = []
    cfos_paths = []

    tr_mouse_names = []
    tr_mouse_ids = []
    tr_date_of_mouses = []
    tr_mouse_sexs = []
    tr_mouse_strains = []

    mouse_names = []
    mouse_ids = []
    date_of_mouses = []
    mouse_sexs = []
    mouse_strains = []

    dir = st.selectbox(
        "Input path",
        [
            "Give single cFOS and autofluo input files",
            "Give whole directory",
        ],
    )

    if dir == "Give single cFOS and autofluo input files":
        autofluo_scan_path = st.text_input(
            "Autofluo scan path",
            value=Path("").resolve() / Path("autofluo.tiff"),
        )
        cfos_scan_path = st.text_input(
            "cFOS scan path", value=Path("").resolve() / Path("cfos.tiff")
        )
        elements = [string.strip() for string in autofluo_paths.split("_")]
        tr_mouse_names.append(elements[0])
        tr_mouse_ids.append(0)
        tr_date_of_mouses.append("2023-11-11")
        tr_mouse_sexs.append("M")
        tr_mouse_strains.append("WT")
        autofluo_paths.append(autofluo_scan_path)
        cfos_paths.append(cfos_scan_path)

    else:
        dir_path = st.text_input("Directory path", value=Path("").resolve())
        files_list = [
            file.name for file in Path(dir_path).glob("*") if file.is_file()
        ]
        for filename in files_list:
            elements = [string.strip() for string in filename.split("_")]
            tr_mouse_names.append(elements[0])
            tr_mouse_ids.append(0)
            tr_date_of_mouses.append("2023-11-11")
            tr_mouse_sexs.append("M")
            tr_mouse_strains.append("WT")
            autofluo_paths.append(
                [string for string in elemnts if string == "Ch488"][0]
            )
            cfos_paths.append(
                [string for string in elemnts if string == "Ch561"][0]
            )

    if tr_mouses_names:
        Col1, Col2, Col3, Col4, Col5 = st.columns(5)
        with Col1:
            for i, mouse_name in enumerate(tr_mouse_names):
                p = st.text_input(
                    "mouse name n°" + str(i), value=mouse_name, key=i
                )
                mouse_names.append(p)
        with Col2:
            for i, mouse_id in enumerate(tr_mouse_ids):
                p = st.text_input(
                    "mouse id n°" + str(i), value=mouse_id, key=i
                )
                mouse_ids.append(p)
        with Col3:
            for i, date in enumerate(tr_date_of_mouses):
                p = st.text_input(
                    "date of birth n°" + str(i), value=date, key=i
                )
                date_of_mouses.append(p)
        with Col4:
            for i, sex in enumerate(tr_mouse_sexs):
                p = st.text_input("mouse sex n°" + str(i), value=sex, key=i)
                mouse_sexs.append(p)
        with Col5:
            for i, strain in enumerate(tr_mouse_strains):
                st.text_input("mouse strain n°" + str(i), value=strain, key=i)
                mouse_strains.append(p)

    show_cfos_image = st.checkbox("show cFOS image", value=False)
    if show_cfos_image:
        if len(cfos_paths) > 1:
            m = st.selectbox("Select the mouse", cfos_paths)
            brain = imio.load_any(m)
            u_proja = []
            for i in range(3):
                u_proja.append(np.mean(brain, axis=i))
            # Display all projections with somewhat consistent scaling
            col_1, col_2, col_3 = st.columns(3)
            with col_1:
                st.image(
                    u_proja[0], caption="Ref. proj. 0", use_column_width=True
                )

            with col_2:
                st.image(
                    u_proja[1], caption="Ref. proj. 1", use_column_width=True
                )

            with col_3:
                st.image(
                    u_proja[2], caption="Ref. proj. 2", use_column_width=True
                )
        else:
            brain = imio.load_any(cfos_paths[0])
            u_proja = []
            for i in range(3):
                u_proja.append(np.mean(brain, axis=i))
            # Display all projections with somewhat consistent scaling
            col_1, col_2, col_3 = st.columns(3)
            with col_1:
                st.image(
                    u_proja[0], caption="Ref. proj. 0", use_column_width=True
                )

            with col_2:
                st.image(
                    u_proja[1], caption="Ref. proj. 1", use_column_width=True
                )

            with col_3:
                st.image(
                    u_proja[2], caption="Ref. proj. 2", use_column_width=True
                )

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
    check_orient = st.checkbox("Check orientation", value=False)
    if check_orient:
        if len(autofluo_paths) > 1:
            c = st.selectbox("Select the mouse", autofluo_paths)
            check_orientation(
                orientation_str, brain_geom, atlas_name, autofluo_paths[0]
            )
        else:
            check_orientation(
                orientation_str, brain_geom, atlas_name, autofluo_paths[0]
            )
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

    st.header("Parameters of the user")
    username = st.text_input("Name", value="cyril")
    useremail = st.text_input("Email", value="cyril.achard@epfl.ch")

    st.header("Determining the ROIs")
    add_new_parameters_brain_scan = st.checkbox("Add new attempt", value=False)
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
        if rois_ids:
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
        attempt = 0

        for (
            mouse_name,
            mouse_id,
            date_of_mouse,
            mouse_sex,
            mouse_strain,
        ) in zip(
            mouse_names, mouse_ids, date_of_mouses, mouse_sexs, mouse_strains
        ):
            scan_attempt = fetch_attempt_scan(mouse_name, username)
            if not scan_attempt:
                scan_attempt = 0
            else:
                if add_new_parameters_brain_scan:
                    scan_attempt = np.max(scan_attempt) + 1
                else:
                    scan_attempt = np.max(scan_attempt)
            list_ids = return_all_list(mouse_name, username, scan_attempt)
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
                    mouse_id,
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

            time_stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            scan.insert1(
                (
                    mouse_name.lower(),
                    scan_attempt,
                    username,
                    autofluo_path,
                    cfos_path,
                    time_stamp,
                ),
                skip_duplicates=True,
            )

            scan_part = spim.ROIs()
            scan_part.insert1(
                (
                    mouse_name.lower(),
                    scan_attempt,
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

            st.sidebar.write("Writing report")
            report = spim.Report()
            report.populate()

            st.sidebar.write("Pipeline completed !")


if __name__ == "__main__":
    main()
