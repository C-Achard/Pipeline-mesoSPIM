import os

import numpy as np

from utils import read_tiff_stack_labels
import matplotlib.pyplot as plt
from skimage import io


# Run metrics
def precision(y_true, y_pred):
    mask_true = np.array(y_true, dtype="bool")
    mask_pred = np.array(y_pred, dtype="bool")
    true_positives = np.sum(np.round(np.clip(mask_true * mask_pred, 0, 1)))
    predicted_positives = np.sum(np.round(np.clip(mask_pred, 0, 1)))
    precision = (true_positives + np.finfo(float).eps) / (
        predicted_positives + np.finfo(float).eps
    )
    return precision


def recall(y_true, y_pred):
    mask_true = np.array(y_true, dtype="bool")
    mask_pred = np.array(y_pred, dtype="bool")
    true_positives = np.sum(np.round(np.clip(mask_true * mask_pred, 0, 1)))
    actual_positives = np.sum(np.round(np.clip(mask_true, 0, 1)))
    recall = (true_positives + np.finfo(float).eps) / (
        actual_positives + np.finfo(float).eps
    )
    return recall


def f1_score(y_true, y_pred):
    f1_precision = precision(y_true, y_pred)
    f1_recall = recall(y_true, y_pred)
    return 2 * (
        (f1_precision * f1_recall)
        / (f1_precision + f1_recall + np.finfo(float).eps)
    )


def iou(f1):
    return f1 / (2 - f1)


def iou_vs_threshold(prediction, target, threshold_range):
    threshold_list = []
    IoU_scores_list = []

    for threshold in threshold_range:
        mask = prediction > threshold

        intersection = np.logical_and(target, mask)
        union = np.logical_or(target, mask)
        iou_score = np.sum(intersection) / np.sum(union)

        threshold_list.append(threshold)
        IoU_scores_list.append(iou_score)

    return threshold_list, IoU_scores_list


def plot_threshold(threshold_list, IoU_scores_list):
    plt.title("Threshold vs. IoU", fontsize=15)
    plt.plot(threshold_list, IoU_scores_list)
    plt.ylabel("IoU score")
    plt.xlabel("Threshold")
    # plt.savefig(os.path.join(base_path,"results/QC_IoU_analysis.png"))
    plt.show()


def run_evaluation(y_pred):
    threshold_range = np.arange(0.1, 0.3, 0.002)
    threshold_list, IoU_scores_list = iou_vs_threshold(
        y_pred, y_true, threshold_range
    )
    print(IoU_scores_list)
    thresh_arr = np.array(list(zip(threshold_list, IoU_scores_list)))
    best_thresh = int(np.where(thresh_arr == np.max(thresh_arr[:, 1]))[0][0])
    best_iou = IoU_scores_list[best_thresh]
    print(
        "Highest IoU is {:.4f} with a threshold of {}".format(
            best_iou, threshold_range[best_thresh]
        )
    )
    plot_threshold(threshold_list, IoU_scores_list)

    y_pred = y_pred >= threshold_range[best_thresh]
    cell_precision = precision(y_true, y_pred)
    cell_recall = recall(y_true, y_pred)
    cell_f1 = f1_score(y_true, y_pred)
    cell_iou = iou(cell_f1)
    print("IoU score is " + str(cell_iou))
    print("F1 score is " + str(cell_f1))
    print("Precision is " + str(cell_precision))
    print("Recall is " + str(cell_recall))


base_path = "/home/maximevidal/Documents/cell-segmentation-models"
label_path = os.path.join(
    base_path, "data/validation_labels_semantic/c5labels.tif"
)
y_true = read_tiff_stack_labels(label_path)

if __name__ == "__main__":
    # Load segmentation
    # seg_path = base_path + "/results/predicted-images/Prediction_1_c5images_Swin_2022_06_17_12_34_52_.tif"
    seg_path = os.path.join(
        base_path,
        "results/predicted-images/Prediction_1_c5images_SegResNet_2022_06_27_20_30_26_.tif",
    )
    y_pred = read_tiff_stack_labels(seg_path)
    run_evaluation(y_pred)
