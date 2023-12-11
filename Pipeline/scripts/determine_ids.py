import pandas as pd
import numpy as np
from bg_atlasapi import BrainGlobeAtlas
from pprint import pprint


def select_areas_containing_specified_name(dataframe, bg_atlas, global_name):
    """This function allows to extract all the names of sub-areas (ROIs) listed by the atlas
    from the name of the global area (global_name). For example, global_name is primary visual area, it will
    retrieve primary visual area - layer 1, primary visual area - layer 2&3, etc.

    Args:
        dataframe (pandas.Dataframe): atlas dataframe containing all ROIs.
        bg_atlas: Brainglobe atlas
        global_name (string): name of the global area.
    Returns:
        descendants_list (List): list of ROI names corresponding to given keyword.
    """
    rslt_df_1 = dataframe.loc[
        dataframe["name"].str.contains(global_name.lower())
    ]
    # For the name of the global area, the dataframe contains a special ID
    # However, we are only interested in the sub-sections
    descendants_list = [
        rslt_df_1.loc[rslt_df_1["acronym"] == acronym]["name"].values[0]
        for acronym in np.unique(rslt_df_1["acronym"]).tolist()
        if not bg_atlas.get_structure_descendants(acronym)
    ]
    if not descendants_list:
        print(global_name + ": global name not part of the atlas nomenclature")
    return descendants_list


def extract_ids_of_selected_areas(
    atlas_name="allen_mouse_10um",
    list_atlas_names=None,
    list_global_names=None,
):
    """This function allows to extract IDs of selected brain areas from given atlas. The brain areas can
    be passed in 2 ways: exact names of specific brain areas or global names.

    Args:
        atlas_name (string): name of the atlas
        list_atlas_names (list[string]): list of exact names of brain areas (must follow the
        nomenclature of the atals)
        list_global_names (list[string]): list of global names to extract atlas names of their sub-areas
    Returns:
        list_of_ids (list[int]): list of ROI IDs
    """
    bg_atlas = BrainGlobeAtlas(atlas_name, check_latest=False)
    df = bg_atlas.lookup_df
    df["name"] = df["name"].str.lower()
    dict_of_ids = {}
    list_of_ids = []
    if not list_atlas_names and not list_global_names:
        raise Exception(
            "No list of brain areas was selected for cell segmentation"
        )
    else:
        if list_global_names:
            for global_name in list_global_names:
                list_specific_names = select_areas_containing_specified_name(
                    df, bg_atlas, global_name
                )
                for specific_name in list_specific_names:
                    rslt_df = df.loc[df["name"] == specific_name.lower()]
                    if rslt_df["id"].values[0] != 545:
                        dict_of_ids[specific_name.lower()] = rslt_df[
                            "id"
                        ].values[0]

        if list_atlas_names:
            for atlas_name in list_atlas_names:
                rslt_df = df.loc[df["name"] == atlas_name.lower()]
                if rslt_df.empty:
                    print(atlas_name + ": not part of the atlas nomenclature")
                else:
                    dict_of_ids[atlas_name.lower()] = rslt_df["id"].values[0]

    if not (dict_of_ids):
        raise Exception(
            "The list of given names did not align with the atlas nomenclature"
        )

    else:
        for key in dict_of_ids:
            list_of_ids.append(dict_of_ids[key])

    return list_of_ids
