# Pipeline-mesoSPIM
 Datajoint pipeline for automated brain registration and cell segmentation

---

# Setup

## Install Datajoint
See DataJoint docs [here](https://datajoint.com/docs/core/datajoint-python/0.14/quick-start/)

## Read the docs
* To build docs locally, install jupyter-book
```pip install jupyter-book```
* Then build the docs
```jupyter-book build ./OLD_meso_spim/docs```

## Setup dev tools

* Install pre-commit hooks
```pip install pre-commit```

* In the root directory of the repo, run
```pre-commit install```

## To contribute new code:
* Create a new branch from the `main` branch
* Open a pull request to merge your branch into `main` as draft
* Make your changes, ensure they pass pre-commit checks, and commit them to your branch
* When ready, mark the pull request as ready for review

---

## TODO:
Titouan:
- [ ] Read the docs
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
