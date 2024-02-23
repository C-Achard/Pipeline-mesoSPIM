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
