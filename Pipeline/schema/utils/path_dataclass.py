import json
from dataclasses import dataclass
from pathlib import Path

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class PathConfig:
    """Config for paths to data and storage."""

    file_storage: str = str(
        Path.home() / Path("Desktop/Code/BRAINREG_DATA/test_data")
    )

    @classmethod
    def load_from_json(cls, path):
        """Load config from json file."""
        print(f"Loading json config: {path}")
        with Path.open(path) as f:
            data = json.load(f)
            return cls.from_dict(data)
