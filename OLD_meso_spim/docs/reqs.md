# Requirements

```{warning}
If you run into a module not found error, please add the missing packages to this list
```

## Init and update git submodules:
```
git submodule init
git submodule update
```
Submodules are:
- cellseg3dmodule *(called cell-segmentation-models on AMCL GitHub)*


## Package requirements:

- Install PyTorch with CUDA manually if applicable. See [PyTorch install page](https://pytorch.org/get-started/locally/)

```
napari[all]
-e git+https://github.com/brainglobe/brainreg-napari.git@f068cb6de319e1c3666ad771bcbbe1882e71cc39#egg=brainreg_napari
PyQt5 # (if not installed)
brainreg>=0.3.3
dataclasses-json>=0.5.7
dask-image>=2021.12.0
datajoint>=0.13.7
GitPython>=3.1.27
```

## Notes:
- Install all requirements of cellseg3d module if not done already. ```monai[all] >= 0.9.1``` is especially important to have einops and SwinUNetR.
- Use the latest version of brainreg-napari on GitHub. Otherwise, you will not have the "Check Orientation" feature

## Docs requirements:

```juypter-book```

- Build docs with ```jupyter-book build ./docs```
