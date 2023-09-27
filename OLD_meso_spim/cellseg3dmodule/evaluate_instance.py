import os
from collections import defaultdict

import numpy as np
from matplotlib import pyplot as plt
from skimage import io
from tifffile import imwrite
from tqdm import tqdm

from matching import matching
from post_processing import (
    binary_watershed,
    binary_connected,
    bc_connected,
    bc_watershed,
)
from utils import read_tiff_stack_labels, define_matplotlib_defaults

define_matplotlib_defaults()


def run_instance_evaluation(y_pred, method_name):
    accuracy_list_all_thresh = []
    params_list_all_thresh = []
    for thresh in [0.2, 0.4, 0.6]:
        if method_name == "Watershed":

            def method(image, threshold_seed, size_small, threshold_object):
                return binary_watershed(
                    image, threshold_seed, size_small, threshold_object
                )

        elif method_name == "Connected components":

            def method(image, threshold_seed, size_small):
                return binary_connected(image, threshold_seed, size_small)

        elif method_name == "bcwatershed":

            def method(image, thresh1, thresh2, thresh3, size_small):
                return bc_watershed(
                    image, thresh1, thresh2, thresh3, size_small
                )

        elif method_name == "bcconnected":

            def method(image, thresh1, thresh2, size_small):
                return bc_connected(image, thresh1, thresh2, size_small)

        else:
            raise NotImplementedError(
                "Selected instance segmentation method is not defined"
            )
        if method_name == "Watershed":
            accuracy_list = []
            params_list = []
            for threshold_seed in tqdm(np.arange(0.85, 0.99, 0.01)):
                for size_small in np.arange(12, 30, 5):
                    for threshold_object in np.arange(0.2, 0.55, 0.1):
                        instance_labels = method(
                            y_pred,
                            threshold_seed,
                            size_small,
                            threshold_object,
                        )
                        metrics = matching(
                            y_true, instance_labels, thresh=thresh
                        )
                        accuracy_list.append(metrics.accuracy)
                        params_list.append(
                            {
                                "threshold_seed": threshold_seed,
                                "threshold_object": threshold_object,
                                "size_small": size_small,
                            }
                        )
        if method_name == "Connected components":
            accuracy_list = []
            params_list = []
            for threshold_seed in tqdm(np.arange(0.4, 0.99, 0.02)):
                for size_small in np.arange(3, 50, 2):
                    instance_labels = method(
                        y_pred, threshold_seed, size_small
                    )
                    metrics = matching(y_true, instance_labels, thresh=thresh)
                    accuracy_list.append(metrics.accuracy)
                    params_list.append(
                        {
                            "threshold_seed": threshold_seed,
                            "size_small": size_small,
                        }
                    )
        if method_name == "bcwatershed":
            accuracy_list = []
            params_list = []
            for thresh1 in tqdm(np.arange(0.2, 0.99, 0.1)):
                for thresh2 in np.arange(0.01, 0.6, 0.1):
                    for thresh3 in np.arange(0.01, 0.6, 0.1):
                        for size_small in np.arange(5, 25, 7):
                            instance_labels = method(
                                y_pred, thresh1, thresh2, thresh3, size_small
                            )
                            metrics = matching(
                                y_true, instance_labels, thresh=thresh
                            )
                            accuracy_list.append(metrics.accuracy)
                            params_list.append(
                                {
                                    "thresh1": thresh1,
                                    "thresh2": thresh2,
                                    "thresh3": thresh3,
                                    "size_small": size_small,
                                }
                            )
        if method_name == "bcconnected":
            accuracy_list = []
            params_list = []
            for thresh1 in tqdm(np.arange(0.01, 0.99, 0.05)):
                for thresh2 in np.arange(0.01, 0.99, 0.05):
                    for size_small in np.arange(3, 25, 5):
                        instance_labels = method(
                            y_pred, thresh1, thresh2, size_small
                        )
                        metrics = matching(
                            y_true, instance_labels, thresh=thresh
                        )
                        accuracy_list.append(metrics.accuracy)
                        params_list.append(
                            {
                                "thresh1": thresh1,
                                "thresh2": thresh2,
                                "size_small": size_small,
                            }
                        )
        accuracy_list_all_thresh.append(accuracy_list)
        params_list_all_thresh.append(params_list)

    average_accuracies = np.mean(accuracy_list_all_thresh, axis=0)
    print(
        f"Max accuracy per threshold is {np.max(accuracy_list_all_thresh, axis=1)}"
    )
    best_params = params_list_all_thresh[0][np.argmax(average_accuracies)]
    print(f"Best params are {best_params}")
    return best_params


# Load instance segmentation ground truth
base_path = "/home/maximevidal/Documents/cell-segmentation-models"
label_path = os.path.join(base_path, "data/validation_new_labels/c5labels.tif")
y_true = read_tiff_stack_labels(label_path)

if __name__ == "__main__":
    find_best_params = True
    run_with_best_params = False
    plot_segmentation_performance = False
    plot_cell_count = False
    save_matched_pairs = False

    seg_path = os.path.join(
        base_path,
        "results/predicted-images/Prediction_1_c5images_Swin_2022_06_24_21_57_37_.tif",
    )
    y_pred = io.imread(seg_path)
    if find_best_params:
        best_params = defaultdict(dict)
        for method in [
            "Watershed",
            "Connected components",
            "bcwatershed",
            "bcconnected",
        ]:  # TODO(maxime) //ize this
            print(f"Current method is {method}")
            best_params[method] = run_instance_evaluation(y_pred, method)
        print(
            best_params
        )  # TODO(maxime) save as JSON so we don't have it as a dict of dicts

    if run_with_best_params:  # TODO(maxime) add other post-processing methods
        best_params = {
            "thresh1": 0.7,
            "thresh2": 0.01,
            "thresh3": 0.21,
            "size_small": 22,
        }  # TODO(maxime) load from saved JSON
        instance_labels = bc_watershed(
            y_pred,
            best_params["thresh1"],
            best_params["thresh2"],
            best_params["thresh3"],
            best_params["size_small"],
        )
        imwrite(
            base_path + "results/predicted-images/instance_swinedge.tif",
            instance_labels,
        )
        if save_matched_pairs:
            metrics = matching(y_true, instance_labels, thresh=0.5)
            matched_pairs = np.array([m[1] for m in metrics.matched_pairs])
            matched_labels = np.isin(instance_labels, matched_pairs) * 1
            cell_labels = (instance_labels > 0) * 1
            matched_cell_labels = matched_labels + cell_labels
            instance_filepath = os.path.join(
                base_path, "results/predicted-images/instance_cells.tif"
            )
            imwrite(instance_filepath, instance_labels)
            matched_cell_filepath = os.path.join(
                base_path, "results/predicted-images/matched_cells.tif"
            )
            imwrite(matched_cell_filepath, matched_cell_labels)

    if plot_segmentation_performance:
        method_metrics = {}
        method_names = ["Watershed", "Connected components", "bcwatershed"]
        threshold_range = np.arange(0.05, 1, 0.05)
        for method_name in method_names:
            metrics_list_all_thresh = []
            if method_name == "Watershed":
                best_params = {
                    "threshold_seed": 0.99,
                    "threshold_object": 0.4,
                    "size_small": 27,
                }
                instance_labels = binary_watershed(
                    y_pred,
                    best_params["threshold_seed"],
                    best_params["size_small"],
                    best_params["threshold_object"],
                )
            elif method_name == "Connected components":
                best_params = {"threshold_seed": 0.4, "size_small": 41}
                instance_labels = binary_connected(
                    y_pred,
                    best_params["threshold_seed"],
                    best_params["size_small"],
                )
            elif method_name == "bcwatershed":
                best_params = {
                    "thresh1": 0.7,
                    "thresh2": 0.01,
                    "thresh3": 0.21,
                    "size_small": 22,
                }
                instance_labels = bc_watershed(
                    y_pred,
                    best_params["thresh1"],
                    best_params["thresh2"],
                    best_params["thresh3"],
                    best_params["size_small"],
                )

            for thresh in tqdm(threshold_range):
                metrics = matching(y_true, instance_labels, thresh=thresh)
                metrics_list_all_thresh.append(metrics)
            method_metrics[method_name] = metrics_list_all_thresh
        fig, axs = plt.subplots(2, 2)
        x = threshold_range

        colors = plt.cm.cool(np.linspace(0, 1, 3))
        color = {
            "Watershed": colors[0],
            "Connected components": colors[1],
            "bcwatershed": colors[2],
        }
        for method in method_names:
            y = [metrics.accuracy for metrics in method_metrics[method]]
            axs[0, 0].plot(x, y, label=method, c=color[method])
        axs[0, 0].set_title("Accuracy")
        axs[0, 0].set(xlabel="IoU threshold τ", ylabel="Accuracy")
        axs[0, 0].set_ylim(bottom=0, top=1)
        axs[0, 0].set_xlim(left=0, right=1)

        for method in method_names:
            y = [metrics.precision for metrics in method_metrics[method]]
            axs[0, 1].plot(x, y, label=method, c=color[method])
        # axs[0, 1].plot(x, y, 'tab:orange')
        axs[0, 1].set_title("Precision")
        axs[0, 1].set(xlabel="IoU threshold τ", ylabel="Precision")
        axs[0, 1].set_ylim(bottom=0, top=1)
        axs[0, 1].set_xlim(left=0, right=1)

        for method in method_names:
            y = [metrics.recall for metrics in method_metrics[method]]
            axs[1, 0].plot(x, y, label=method, c=color[method])
        axs[1, 0].set_title("Recall")
        axs[1, 0].set(xlabel="IoU threshold τ", ylabel="Recall")
        axs[1, 0].set_ylim(bottom=0, top=1)
        axs[1, 0].set_xlim(left=0, right=1)

        for method in method_names:
            y = [metrics.f1 for metrics in method_metrics[method]]
            axs[1, 1].plot(x, y, label=method, c=color[method])
        axs[1, 1].set_title("F1")
        axs[1, 1].set(xlabel="IoU threshold τ", ylabel="F1")
        axs[1, 1].set_ylim(bottom=0, top=1)
        axs[1, 1].set_xlim(left=0, right=1)

        plt.subplots_adjust(
            left=0.16, bottom=0.1, right=0.9, top=0.77, wspace=0.4, hspace=0.6
        )
        axs[0, 0].legend(loc="upper left", bbox_to_anchor=(0.65, 1.8))
        plt.show()

        if plot_cell_count:
            method_metrics = {}
            method_name = "bcwatershed"
            threshold_range = np.arange(0.05, 1, 0.05)
            metrics_list_all_thresh = []
            best_params = {
                "thresh1": 0.7,
                "thresh2": 0.01,
                "thresh3": 0.21,
                "size_small": 22,
            }
            instance_labels = bc_watershed(
                y_pred,
                best_params["thresh1"],
                best_params["thresh2"],
                best_params["thresh3"],
                best_params["size_small"],
            )
            for thresh in tqdm(threshold_range):
                metrics = matching(y_true, instance_labels, thresh=thresh)
                metrics_list_all_thresh.append(metrics)
                print(metrics)
            method_metrics = metrics_list_all_thresh
            fig, axs = plt.subplots(1, 1)
            x = threshold_range
            colors = plt.cm.cool(np.linspace(0, 1, 3))

            y = [metrics.tp for metrics in method_metrics]
            axs.plot(x, y, label="TP", c=colors[0])
            y = [metrics.fp for metrics in method_metrics]
            axs.plot(x, y, label="FP", c=colors[1])
            y = [metrics.fn for metrics in method_metrics]
            axs.plot(x, y, label="FN", c=colors[2])
            y = [metrics.n_pred for metrics in method_metrics]
            axs.plot(x, y, label="predicted # of cells", c="red")
            y = [metrics.n_true for metrics in method_metrics]
            axs.plot(x, y, label="true # of cells", c="green")
            axs.set_title("Cell count evaluation")
            axs.set(xlabel="IoU threshold τ", ylabel="Number of cells")
            plt.subplots_adjust(
                left=0.16,
                bottom=0.1,
                right=0.75,
                top=0.9,
                wspace=0.4,
                hspace=0.6,
            )
            axs.legend(loc="upper left", bbox_to_anchor=(0.85, 0.6))
            axs.set_ylim(bottom=0)
            plt.show()

        # TODO(maxime) plot mean_true_score and mean_matched_score
        # y = [metrics.mean_true_score for metrics in metrics_list_all_thresh]
        # y = [metrics.mean_matched_score for metrics in metrics_list_all_thresh]
