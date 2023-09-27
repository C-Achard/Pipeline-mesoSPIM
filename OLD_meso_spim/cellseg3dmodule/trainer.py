import logging
import os

import matplotlib.pyplot as plt
import torch
import wandb

# MONAI
from monai.data import (
    CacheDataset,
    DataLoader,
    PatchDataset,
    decollate_batch,
    pad_list_data_collate,
)
from monai.metrics import DiceMetric
from monai.transforms import (
    AsDiscrete,
    Compose,
    EnsureChannelFirstd,
    EnsureTyped,
    LoadImaged,
    Orientationd,
    RandFlipd,
    RandRotate90d,
    RandShiftIntensityd,
    RandSpatialCropSamplesd,
    SpatialPadd,
    ScaleIntensityRanged,
    Zoomd,
    EnsureType,
)
from monai.utils import set_determinism
from torch.optim.lr_scheduler import ReduceLROnPlateau

from utils import get_loss, get_model, create_dataset_dict, get_padding_dim

logger = logging.getLogger(__name__)


class TrainerConfig:
    def __init__(self, **kwargs):
        self.model_name = "Swin"
        self.weights_path = None
        self.validation_percent = None  # 0.8
        self.train_volume_directory = "/home/maximevidal/Documents/cell-segmentation-models/data/train_volumes"
        self.train_label_directory = "/home/maximevidal/Documents/cell-segmentation-models/data/train_labels_semantic"
        self.validation_volume_directory = "/home/maximevidal/Documents/cell-segmentation-models/data/validation_volumes"
        self.validation_label_directory = "/home/maximevidal/Documents/cell-segmentation-models/data/validation_labels_semantic"

        self.max_epochs = 50
        self.learning_rate = 3e-4
        self.val_interval = 1
        self.batch_size = 16
        self.results_path = (
            "/home/maximevidal/Documents/cell-segmentation-models/results"
        )
        self.weights_dir = "/home/maximevidal/Documents/cell-segmentation-models/models/saved_weights"
        self.sampling = True
        self.num_samples = 160
        self.sample_size = [64, 64, 64]
        self.do_augmentation = True
        self.deterministic = True
        self.grad_norm_clip = 1.0
        self.weight_decay = 0.00001
        self.compute_instance_boundaries = False  # Change class loss weights in utils.get_loss TODO: choose in config
        self.loss_function_name = "Dice loss"  # DiceCELoss
        self.plot_training_inputs = False
        for k, v in kwargs.items():
            setattr(self, k, v)


class Trainer:
    def __init__(
        self,
        config,
    ):
        self.config = config
        if self.config.validation_percent is not None:
            self.data_dicts = create_dataset_dict(
                volume_directory=self.config.train_volume_directory,
                label_directory=self.config.train_label_directory,
            )
        else:
            self.train_data_dict = create_dataset_dict(
                volume_directory=self.config.train_volume_directory,
                label_directory=self.config.train_label_directory,
            )

            self.val_data_dict = create_dataset_dict(
                volume_directory=self.config.validation_volume_directory,
                label_directory=self.config.validation_label_directory,
            )
        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        logger.info(f"Using {self.device} device")
        logger.info(f"Using torch : {torch.__version__}")
        self.model_class = get_model(self.config.model_name)
        self.weights_path = self.config.weights_path
        self.validation_percent = self.config.validation_percent
        self.max_epochs = self.config.max_epochs
        self.learning_rate = self.config.learning_rate
        self.val_interval = self.config.val_interval
        self.batch_size = self.config.batch_size
        self.results_path = self.config.results_path
        self.num_samples = self.config.num_samples
        self.sampling = self.config.sampling
        self.sample_size = self.config.sample_size
        self.do_augment = self.config.do_augmentation
        self.seed_dict = self.config.deterministic
        self.weight_decay = self.config.weight_decay
        self.plot_training_inputs = self.config.plot_training_inputs
        self.train_files = []
        self.val_files = []
        self.compute_instance_boundaries = (
            self.config.compute_instance_boundaries
        )
        self.deterministic = self.config.deterministic
        self.loss_function = get_loss(self.config.loss_function_name)

    def log_parameters(self):
        logger.info("Parameters summary: ")
        logger.info("-" * 20)

        if self.validation_percent is not None:
            logger.info(
                f"Percentage of dataset used for validation : {self.validation_percent * 100}%"
            )

        if self.deterministic:
            logger.info(f"Deterministic training is enabled")
            logger.info(f"Seed is 42")

        logger.info(f"Training for {self.max_epochs} epochs")
        logger.info(f"Loss function is : {str(self.loss_function)}")
        logger.info(
            f"Validation is performed every {self.val_interval} epochs"
        )
        logger.info(f"Batch size is {self.batch_size}")
        logger.info(f"Learning rate is {self.learning_rate}")

        if self.sampling:
            logger.info(
                f"Extracting {self.num_samples} patches of size {self.sample_size}"
            )
        else:
            logger.info("Using whole images as dataset")

        if self.do_augment:
            logger.info("Data augmentation is enabled")

        if self.weights_path is not None:
            logger.info(f"Using weights from : {self.weights_path}")

        if self.compute_instance_boundaries:
            logger.info(f"Computing instance boundaries")

        logger.info("-" * 20)

    def train(self):
        if self.config.deterministic:
            set_determinism(seed=42)

        if not self.sampling:
            first_volume = LoadImaged(keys=["image"])(self.train_data_dict[0])
            first_volume_shape = first_volume["image"].shape

        if self.config.model_name == "SegResNet":
            if self.sampling:
                size = self.sample_size
            else:
                size = first_volume_shape
            logger.info(f"The volume size is {size}")
            model = self.model_class.get_net()(
                input_image_size=get_padding_dim(size),
                out_channels=1,
                dropout_prob=0.3,
            )
        elif self.config.model_name == "Swin":
            if self.sampling:
                size = self.sample_size
            else:
                size = first_volume_shape
            logger.info(f"Size of volume : {size}")
            model = self.model_class.get_net()(
                img_size=get_padding_dim(size),
                in_channels=1,
                out_channels=1,
                feature_size=48,
                use_checkpoint=True,
            )
        else:
            model = self.model_class.get_net()

        model = torch.nn.DataParallel(model).to(self.device)

        epoch_loss_values = []
        val_metric_values = []

        if self.validation_percent is not None:
            self.train_files, self.val_files = (
                self.data_dicts[
                    0 : int(len(self.data_dicts) * self.validation_percent)
                ],
                self.data_dicts[
                    int(len(self.data_dicts) * self.validation_percent) :
                ],
            )
        else:
            self.train_files, self.val_files = (
                self.train_data_dict,
                self.val_data_dict,
            )

        if self.sampling:
            sample_loader = Compose(
                [
                    LoadImaged(keys=["image", "label"]),
                    EnsureChannelFirstd(keys=["image", "label"]),
                    RandSpatialCropSamplesd(
                        keys=["image", "label"],
                        roi_size=(self.sample_size),
                        random_size=False,
                        num_samples=self.num_samples,
                    ),
                    Orientationd(keys=["image", "label"], axcodes="PLI"),
                    SpatialPadd(
                        keys=["image", "label"],
                        spatial_size=(get_padding_dim(self.sample_size)),
                    ),
                    EnsureTyped(keys=["image", "label"]),
                ]
            )

        if self.do_augment:
            train_transforms = Compose(
                [
                    ScaleIntensityRanged(
                        keys=["image"],
                        a_min=0,
                        a_max=2000,
                        b_min=0.0,
                        b_max=1.0,
                        clip=True,
                    ),
                    # Zoomd(keys=["image", "label"], zoom=[1, 1, 5], keep_size=True, ),
                    RandShiftIntensityd(keys=["image"], offsets=0.1, prob=0.5),
                    RandFlipd(
                        keys=["image", "label"], spatial_axis=[1], prob=0.5
                    ),
                    RandFlipd(
                        keys=["image", "label"], spatial_axis=[2], prob=0.5
                    ),
                    RandRotate90d(keys=["image", "label"], prob=0.1, max_k=3),
                    EnsureTyped(keys=["image", "label"]),
                ]
            )
            val_transforms = Compose(
                [
                    EnsureTyped(keys=["image", "label"]),
                    # Zoomd(keys=["image", "label"], zoom=[1, 1, 5], keep_size=True, ),
                    ScaleIntensityRanged(
                        keys=["image"],
                        a_min=0,
                        a_max=2000,
                        b_min=0.0,
                        b_max=1.0,
                        clip=True,
                    ),
                ]
            )
        else:
            train_transforms = EnsureTyped(keys=["image", "label"])
            val_transforms = Compose(
                [
                    EnsureTyped(keys=["image", "label"]),
                ]
            )

        if self.sampling:
            logger.info("Create patches for train dataset")
            train_ds = PatchDataset(
                data=self.train_files,
                transform=train_transforms,
                patch_func=sample_loader,
                samples_per_image=self.num_samples,
            )
            logger.info("Create patches for val dataset")
            val_ds = PatchDataset(
                data=self.val_files,
                transform=val_transforms,
                patch_func=sample_loader,
                samples_per_image=self.num_samples,
            )

        else:
            load_single_images = Compose(
                [
                    LoadImaged(keys=["image", "label"]),
                    EnsureChannelFirstd(keys=["image", "label"]),
                    Orientationd(keys=["image", "label"], axcodes="PLI"),
                    SpatialPadd(
                        keys=["image", "label"],
                        spatial_size=(get_padding_dim(first_volume_shape)),
                    ),
                    EnsureTyped(keys=["image", "label"]),
                ]
            )
            logger.info("Cache dataset : train")
            train_ds = CacheDataset(
                data=self.train_files,
                transform=Compose(load_single_images, train_transforms),
            )
            logger.info("Cache dataset : val")
            val_ds = CacheDataset(
                data=self.val_files, transform=load_single_images
            )

        logger.info("Initializing DataLoaders")
        train_loader = DataLoader(
            train_ds,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=4,
            collate_fn=pad_list_data_collate,
        )
        val_loader = DataLoader(
            val_ds, batch_size=self.batch_size, num_workers=4
        )

        if self.plot_training_inputs:
            logger.info("Plotting dataset")
            for check_data in train_loader:
                image, label = (
                    check_data["image"][0][0],
                    check_data["label"][0][0],
                )
                print(
                    f"image shape: {image.shape}, label shape: {label.shape}"
                )
                plt.figure("check", (12, 6))
                plt.subplot(1, 2, 1)
                plt.title("image")
                plt.imshow(image[:, :, 40], cmap="gray")
                plt.subplot(1, 2, 2)
                plt.title("label")
                plt.imshow(label[:, :, 40])
                # plt.savefig('/home/maximevidal/Documents/cell-segmentation-models/results/imageinput.png')
                plt.show()

        logger.info("Creating optimizer")
        optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=self.learning_rate,
            weight_decay=self.weight_decay,
        )
        scheduler = ReduceLROnPlateau(
            optimizer, "max", patience=10, factor=0.5, verbose=True
        )

        dice_metric = DiceMetric(
            include_background=True, reduction="mean", get_not_nans=False
        )
        if self.compute_instance_boundaries:
            dice_metric_only_cells = DiceMetric(
                include_background=True, reduction="mean", get_not_nans=False
            )

        best_metric = -1
        best_metric_epoch = -1

        if self.weights_path is not None:
            logger.info("Loading weights")
            if self.weights_path == "use_pretrained":
                weights_file = self.model_class.get_weights_file()
                weights = os.path.join(self.config.weights_dir, weights_file)
                self.weights_path = weights
            else:
                weights = os.path.join(self.weights_path)

            # # original saved file with DataParallel
            # state_dict = torch.load(weights, map_location=self.device)
            # # create new OrderedDict that does not contain `module.`
            # from collections import OrderedDict
            #
            # new_state_dict = OrderedDict()
            # for k, v in state_dict.items():
            #     name = "module." + k  # add `module.`
            #     new_state_dict[name] = v
            # # load params
            # model.load_state_dict(new_state_dict)
            # TODO(maxime) for DataParallel
            model.load_state_dict(
                torch.load(
                    weights,
                    map_location=self.device,
                )
            )

        if self.device.type == "cuda":
            logger.info(f"Using GPU : {torch.cuda.get_device_name(0)}")
        else:
            logger.info("Using CPU")

        for epoch in range(self.max_epochs):
            # logger.info("\n")
            logger.info("-" * 10)
            logger.info(f"Epoch {epoch + 1}/{self.max_epochs}")
            if self.device.type == "cuda":
                logger.info("Memory Usage:")
                alloc_mem = round(
                    torch.cuda.memory_allocated(0) / 1024**3, 1
                )
                reserved_mem = round(
                    torch.cuda.memory_reserved(0) / 1024**3, 1
                )
                logger.info(f"Allocated: {alloc_mem}GB")
                logger.info(f"Cached: {reserved_mem}GB")

            model.train()
            epoch_loss = 0
            step = 0
            for batch_data in train_loader:
                step += 1
                inputs, labels = (
                    batch_data["image"].to(self.device),
                    batch_data["label"].to(self.device),
                )
                optimizer.zero_grad()
                outputs = self.model_class.get_output(model, inputs)
                loss = self.loss_function(outputs, labels)
                loss.backward()
                optimizer.step()

                epoch_loss += loss.detach().item()
                logger.info(
                    f"* {step - 1}/{len(train_ds) // train_loader.batch_size}, "
                    f"Train loss: {loss.detach().item():.4f}"
                )
                wandb.log({"training loss": loss.detach().item()})
            epoch_loss /= step
            epoch_loss_values.append(epoch_loss)
            logger.info(f"Epoch: {epoch + 1}, Average loss: {epoch_loss:.4f}")

            if (epoch + 1) % self.val_interval == 0:
                model.eval()
                with torch.no_grad():
                    for val_data in val_loader:
                        val_inputs, val_labels = (
                            val_data["image"].to(self.device),
                            val_data["label"].to(self.device),
                        )

                        val_outputs = self.model_class.get_validation(
                            model, val_inputs
                        )

                        val_loss = self.loss_function(val_outputs, val_labels)
                        wandb.log(
                            {"validation loss": val_loss.detach().item()}
                        )
                        logger.info(
                            f"Validation loss: {val_loss.detach().item():.4f}"
                        )

                        pred = decollate_batch(val_outputs)

                        labs = decollate_batch(val_labels)

                        if self.compute_instance_boundaries:
                            post_pred = AsDiscrete(argmax=True, to_onehot=3)
                            post_label = AsDiscrete(to_onehot=3)
                        else:
                            post_pred = Compose(
                                AsDiscrete(threshold=0.6), EnsureType()
                            )
                            post_label = EnsureType()

                        val_outputs = [
                            post_pred(res_tensor) for res_tensor in pred
                        ]
                        val_labels = [
                            post_label(res_tensor) for res_tensor in labs
                        ]

                        dice_metric(y_pred=val_outputs, y=val_labels)

                        if self.compute_instance_boundaries:
                            val_labels = [
                                val_label[1, :, :, :]
                                for val_label in val_labels
                            ]
                            val_outputs = [
                                val_output[1, :, :, :]
                                for val_output in val_outputs
                            ]
                            dice_metric_only_cells(
                                y_pred=val_outputs, y=val_labels
                            )

                    metric = dice_metric.aggregate().detach().item()
                    scheduler.step(metric)
                    wandb.log({"dice metric validation": metric})
                    dice_metric.reset()

                    if self.compute_instance_boundaries:
                        metric_cells = (
                            dice_metric_only_cells.aggregate().detach().item()
                        )
                        scheduler.step(metric_cells)
                        wandb.log(
                            {"dice metric only cells validation": metric_cells}
                        )
                        dice_metric_only_cells.reset()

                    val_metric_values.append(metric)

                    if metric > best_metric:
                        best_metric = metric
                        best_metric_epoch = epoch + 1
                        logger.info("Saving best metric model")

                        weights_filename = f"{self.config.model_name}64_onechannel_best_metric.pth"  # f"_epoch_{epoch + 1}

                        # DataParallel wrappers keep raw model object in .module attribute
                        raw_model = (
                            model.module if hasattr(model, "module") else model
                        )
                        torch.save(
                            raw_model.state_dict(),
                            os.path.join(self.results_path, weights_filename),
                        )
                        logger.info("Saving complete")

                    logger.info(
                        f"Current epoch: {epoch + 1}, Current mean dice: {metric:.4f}"
                        f"\nBest mean dice: {best_metric:.4f} "
                        f"at epoch: {best_metric_epoch}"
                    )
        logger.info("=" * 10)
        logger.info(
            f"Train completed, best_metric: {best_metric:.4f} at epoch: {best_metric_epoch}"
        )


tconf = TrainerConfig()
wandb.init(project="cell-segmentation", entity="amg", config=tconf.__dict__)
trainer = Trainer(tconf)
trainer.log_parameters()
trainer.train()
