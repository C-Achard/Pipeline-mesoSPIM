from cellseg3dmodule.config import InferenceWorkerConfig
import json

NAME = ...  # enter name of config file here

if __name__ == "__main__":
    f = open(f"./{NAME}.json", "a")
    conf = InferenceWorkerConfig().to_json(indent=2)
    print(conf)
    f.write(conf)
    f.close()
