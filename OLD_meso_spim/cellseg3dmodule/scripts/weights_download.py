import logging
from pathlib import Path
from tqdm import tqdm


WEIGHTS_DIR = Path(__file__).parent.resolve() / Path("../models/pretrained")
logger = logging.getLogger(__name__)


class WeightsDownloader:
    """A utility class the downloads the weights of a model when needed."""

    def __init__(self):
        """
        Creates a WeightsDownloader
        """

    def download_weights(self, model_name: str, model_weights_filename: str):
        """
        Downloads a specific pretrained model.
        This code is adapted from DeepLabCut with permission from MWMathis.

        Args:
            model_name (str): name of the model to download
            model_weights_filename (str): name of the .pth file expected for the model
        """
        import json
        import tarfile
        import urllib.request

        def show_progress(count, block_size, total_size):
            pbar.update(block_size)

        pretrained_folder_path = WEIGHTS_DIR
        json_path = pretrained_folder_path / Path("pretrained_model_urls.json")

        check_path = pretrained_folder_path / Path(model_weights_filename)

        if Path(check_path).is_file():
            message = f"Weight file {model_weights_filename} already exists, skipping download"
            logger.info(message)
            return

        with open(json_path) as f:
            neturls = json.load(f)
        if model_name in neturls.keys():
            url = neturls[model_name]
            response = urllib.request.urlopen(url)

            start_message = f"Downloading the model from the M.W. Mathis Lab server {url}...."
            total_size = int(response.getheader("Content-Length"))
            logger.info(start_message)
            pbar = tqdm(unit="B", total=total_size, position=0)

            filename, _ = urllib.request.urlretrieve(
                url, reporthook=show_progress
            )
            with tarfile.open(filename, mode="r:gz") as tar:
                tar.extractall(pretrained_folder_path)
        else:
            raise ValueError(
                f"Unknown model: {model_name}. Should be one of {', '.join(neturls)}"
            )
