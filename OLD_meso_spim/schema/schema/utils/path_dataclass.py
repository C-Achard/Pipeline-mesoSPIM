import json
from dataclasses import dataclass
from pathlib import Path

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class PathConfig:
    file_storage: str = str(Path.home() / Path("Desktop/Code/BRAINREG_DATA/test_data"))

    @classmethod
    def load_from_json(cls, path):
        print(f"Loading json config: {path}")
        f = open(path)
        data = json.load(f)
        return cls.from_dict(data)
