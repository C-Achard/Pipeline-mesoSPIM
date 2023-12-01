import sys
import numpy as np
import logging
from pathlib import Path
import login
import napari
import imio

sys.path.append("scripts")
sys.path.append("schema")

login.connectToDatabase()

from schema import mice, spim, user
from scripts import brainreg_config, determine_ids


def display_cropped_continuous_cfos_napari(
    name, username, scan_attempt, ids_key
):
    query_reg = (
        spim.BrainRegistrationResults.ContinuousRegion()
        & f"mouse_name='{name}'"
        & f"name='{username}'"
        & f"scan_attempt='{scan_attempt}'"
        & f"ids_key='{ids_key}'"
    )
    query_reg = query_reg.fetch(as_dict=True)
    Masks = {
        table["cont_region_id"]: [
            np.load(table["mask"]),
            table["x_min"],
            table["x_xmax"],
            table["y_min"],
            table["y_max"],
            table["z_min"],
            table["z_max"],
        ]
        for table in query_reg
    }

    query_instance = (
        spim.Inference()
        & f"mouse_name='{name}'"
        & f"name='{username}'"
        & f"scan_attempt='{scan_attempt}'"
        & f"ids_key='{ids_key}'"
    )
    query_instance = query_instance.fetch(as_dict=True)
    Instance_labels = {
        table["cont_region_id"]: imio.load_any(table["instance_labels"])
        for table in query_instance
    }


if __name__ == "__main__":
    login.connectToDatabase()
    display_cropped_continuous_cfos_napari(
        "mouse_chickadee", "cyril_tit", 0, 0
    )
