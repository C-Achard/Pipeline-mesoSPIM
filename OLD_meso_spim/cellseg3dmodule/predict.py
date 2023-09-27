import logging
from pathlib import Path
from pathlib import PurePath
from datetime import datetime

import numpy as np
import torch
import torch.nn.functional as F
from monai.inferers import sliding_window_inference
from monai.transforms import (
    AsDiscrete,
    AddChannel,
    Compose,
    EnsureChannelFirst,
    EnsureType,
    ToTensor,
    Zoom,
    ScaleIntensityRange,
)
from tifffile import imwrite

from cellseg3dmodule.config import InferenceWorkerConfig
from cellseg3dmodule.config import WEIGHTS_PATH
from cellseg3dmodule.post_processing import binary_watershed, binary_connected
from cellseg3dmodule.scripts.weights_download import WeightsDownloader

logger = logging.getLogger(__name__)

SWIN = "SwinUNetR"

CONFIG_PATH = Path().absolute() / "cellseg3dmodule/inference_config.json"


class Inference:
    def __init__(
        self,
        config: InferenceWorkerConfig = InferenceWorkerConfig().load_from_json(
            CONFIG_PATH
        ),
    ):
        self.config = config
        # print(self.config)
        logger.debug(CONFIG_PATH)

        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        logger.info(f"Using {self.device} device")
        logger.info("Using torch :")
        logger.info(torch.__version__)

    def log(self, message):
        logger.info(message)

    @staticmethod
    def create_inference_dict(images_filepaths):
        data_dicts = [{"image": image_name} for image_name in images_filepaths]
        return data_dicts

    def log_parameters(self):
        config = self.config

        self.log("\nParameters summary :")

        self.log(f"Model is : {config.model_info.name}")
        if config.post_process_config.thresholding.enabled:
            self.log(
                f"Thresholding is enabled at {config.post_process_config.thresholding.threshold_value}"
            )

        self.log(f"Window size is {config.sliding_window_config.window_size}")
        self.log(
            f"Window overlap is {config.sliding_window_config.window_overlap}\n"
        )

        if config.keep_on_cpu:
            self.log(f"Dataset loaded to CPU")
        else:
            self.log(f"Dataset loaded on {config.device}")

        if config.post_process_config.zoom.enabled:
            self.log(
                f"Scaling factor : {config.post_process_config.zoom.zoom_values} (x,y,z)"
            )

        instance_config = config.post_process_config.instance
        if instance_config.enabled:
            self.log(
                f"Instance segmentation enabled, method : {instance_config.method}\n"
                f"Probability threshold is {instance_config.threshold.threshold_value:.2f}\n"
                f"Objects smaller than {instance_config.small_object_removal_threshold.threshold_value} pixels will be removed\n"
            )

    def instance_seg(self, to_instance, image_id: int = 0):
        if image_id is not None:
            self.log(f"\nRunning instance segmentation for image n°{image_id}")

        threshold = (
            self.config.post_process_config.instance.threshold.threshold_value
        )
        size_small = (
            self.config.post_process_config.instance.small_object_removal_threshold.threshold_value
        )
        method_name = self.config.post_process_config.instance.method

        if method_name == "Watershed":

            def method(image):
                return binary_watershed(image, threshold, size_small)

        elif method_name == "Connected components":

            def method(image):
                return binary_connected(image, threshold, size_small)

        else:
            raise NotImplementedError(
                "Selected instance segmentation method is not defined"
            )

        instance_labels = method(to_instance)

        instance_filepath = self.save_image(
            name=f"Instance_labels_{image_id}",
            image=instance_labels,
            folder="instance_labels",
        )

        self.log(
            f"Instance segmentation results for image n°{image_id} have been saved as:"
        )
        self.log(PurePath(instance_filepath).name)
        return instance_filepath

    def load_layer(self, volume):
        # data = np.squeeze(self.config.layer.data)

        volume = np.array(volume, dtype=np.int16)

        volume_dims = len(volume.shape)
        if volume_dims != 3:
            raise ValueError(
                f"Data array is not 3-dimensional but {volume_dims}-dimensional,"
                f" please check for extra channel/batch dimensions"
            )

        print("Loading layer\n")

        load_transforms = Compose(
            [
                ToTensor(),
                # anisotropic_transform,
                AddChannel(),
                # SpatialPad(spatial_size=pad),
                AddChannel(),
                # ScaleIntensityRange(
                #     a_min=0,
                #     a_max=2000,
                #     b_min=0.0,
                #     b_max=1.0,
                #     clip=True,
                # ),
                # EnsureType(),
            ],
            # map_items=False,
            # log_stats=True,
        )

        self.log("\nLoading dataset...")
        input_image = load_transforms(volume)
        self.log("Done")
        return input_image

    def model_output(
        self,
        inputs,
        model,
        post_process_transforms,
        post_process=True,
        aniso_transform=None,
    ):
        inputs = inputs.to("cpu")
        # print(f"Input size: {inputs.shape}")
        model_output = lambda inputs: post_process_transforms(
            self.config.model_info.get_model().get_output(model, inputs)
        )

        if self.config.keep_on_cpu:
            dataset_device = "cpu"
        else:
            dataset_device = self.config.device

        window_size = self.config.sliding_window_config.window_size
        window_overlap = self.config.sliding_window_config.window_overlap

        outputs = sliding_window_inference(
            inputs,
            roi_size=window_size,
            sw_batch_size=1,
            predictor=model_output,
            sw_device=self.config.device,
            device=dataset_device,
            overlap=window_overlap,
            progress=True,
        )

        out = outputs.detach().cpu()

        if aniso_transform is not None:
            out = aniso_transform(out)

        if post_process:
            out = np.array(out).astype(np.float32)
            out = np.squeeze(out)
            return out
        else:
            return out

    def save_image(self, name, image, folder: str = None):
        time = "{:%Y_%m_%d_%H_%M_%S}".format(datetime.now())

        result_folder = ""
        if folder is not None:
            result_folder = folder

        folder_path = Path(self.config.results_path) / Path(result_folder)

        folder_path.mkdir(exist_ok=True)

        file_path = folder_path / Path(
            f"{name}_" + f"{time}_" + self.config.filetype
        )
        imwrite(file_path, image)
        filename = PurePath(file_path).name

        self.log(f"\nPrediction saved as : {filename}")
        return file_path

    def aniso_transform(self, image):
        zoom = self.config.post_process_config.zoom.zoom_values
        if zoom is None:
            zoom = [1, 1, 1]
        anisotropic_transform = Zoom(
            zoom=zoom,
            keep_size=False,
            padding_mode="empty",
        )
        return anisotropic_transform(image[0])

    def inference(self, image_id: int = 0):
        try:
            dims = self.config.model_info.model_input_size
            # self.log(f"MODEL DIMS : {dims}")
            model_name = self.config.model_info.name
            model_class = self.config.model_info.get_model()
            self.log(model_name)

            weights_config = self.config.weights_config
            post_process_config = self.config.post_process_config

            if model_name == "SegResNet":
                model = model_class.get_net(
                    input_image_size=[
                        dims,
                        dims,
                        dims,
                    ],
                )
            elif model_name == "SwinUNetR":
                out_channels = 1
                if self.config.compute_instance_boundaries:
                    out_channels = 3
                model = model_class.get_net(
                    img_size=[dims, dims, dims],
                    use_checkpoint=False,
                    out_channels=out_channels,
                )
            else:
                model = model_class.get_net()
            model = model.to(self.config.device)

            self.log_parameters()

            model.to(self.config.device)

            if not post_process_config.thresholding.enabled:
                post_process_transforms = EnsureType()
            else:
                t = post_process_config.thresholding.threshold_value
                post_process_transforms = Compose(
                    [AsDiscrete(threshold=t), EnsureType()]
                )

            self.log("\nLoading weights...")
            if weights_config.path is not None:
                weights_path = weights_config.path
            else:
                downloader = WeightsDownloader()
                downloader.download_weights(
                    model_name, model_class.get_weights_file()
                )
                weights_path = str(
                    Path(WEIGHTS_PATH) / model_class.get_weights_file()
                )
            logger.info(f"Trying to load weights : {weights_path}")
            model.load_state_dict(
                torch.load(
                    weights_path,
                    map_location=self.config.device,
                )
            )
            self.log("Done")

            input_image = self.load_layer(self.config.image)
            model.eval()
            with torch.no_grad():
                self.log(f"Inference started on layer...")

                image = input_image.type(torch.FloatTensor)

                out = self.model_output(
                    image,
                    model,
                    post_process_transforms,
                    aniso_transform=self.aniso_transform,
                )

                file_path = self.save_image(
                    name=f"Semantic_labels_{image_id}",
                    image=out,
                    folder="semantic_labels",
                )

            if self.config.compute_instance_boundaries:
                out = F.softmax(out, dim=1)
                out = np.array(out)  # .astype(np.float32)
                logger.info(
                    f" Output max {out.max()}, output min {out.min()},"
                    f" output mean {out.mean()}, output median {np.median(out)}"
                )
                logger.info(f" Output shape: {out.shape}")
                if self.config.keep_boundary_predictions:
                    out = out[:, 1:, :, :, :]
                else:
                    out = out[:, 1, :, :, :]
                if self.config.post_process_config.threshold.enabled:
                    out = (
                        out
                        > self.config.post_process_config.threshold.threshold_value
                    )
                logger.info(f" Output shape: {out.shape}")
                out = np.squeeze(out)
                logger.info(f" Output shape: {out.shape}")
                if self.config.keep_boundary_predictions:
                    out = np.transpose(out, (0, 3, 2, 1))
                else:
                    out = np.transpose(out, (2, 1, 0))
            else:
                out = np.array(out)
                logger.info(
                    f" Output max {out.max()}, output min {out.min()},"
                    f" output mean {out.mean()}, output median {np.median(out)}"
                )

                # if self.transforms["thresh"][0]:
                #     out = out > self.transforms["thresh"][1]
                logger.info(f" Output shape: {out.shape}")
                out = np.squeeze(out)
                logger.info(f" Output shape: {out.shape}")
                out = np.transpose(out, (2, 1, 0))

            if self.config.run_semantic_evaluation:
                from evaluate_semantic import run_evaluation

                run_evaluation(out)

            model.to("cpu")
            return file_path

        except Exception as e:
            raise e
