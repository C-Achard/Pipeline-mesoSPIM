# Pipeline-mesoSPIM
 Datajoint pipeline for automated brain registration and cell segmentation

---

# Setup

## Install Datajoint
See DataJoint docs [here](https://datajoint.com/docs/core/datajoint-python/0.14/quick-start/)

## Setup dev tools

* Install pre-commit hooks
```pip install pre-commit```

* In the root directory of the repo, run
```pre-commit install```

---

## TODO:
Titouan:
- [ ] Read existing code, discuss parts in need of replacement, ask questions about unclear parts
- [ ] Replace brainreg code with new, updated version without napari
- [ ] Add config files loaded to/from json for database storage (see schema/utils/path_dataclass.py)
- [ ] Create/use brainreg utils to:
  - [ ] Load brainreg data
  - [ ] Go from one anatomical space to another (sample <-> atlas) using transformation matrices
  - [ ] Re-orient the data
  - [ ] Crop ROIs from brainreg results for cell segmentation
- [ ] Write a new test populate script for brainreg

Cyril:
- [ ] Add cell segmentation code
