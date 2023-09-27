# mesoSPIM-pipeline

Datajoint pipeline for cataloging mesoSPIM data (2 channel), running BrainReg, and running CellSeg3D + downstream stats on 3D cell volumes collected on the mesoSPIM system at the Wyss Center.

- More information on DataJoint: https://www.datajoint.org/

- API docs: https://docs-api.datajoint.org/

WIP:

The repo is designed to (1) integrate with our **Main DJ database on server 1** & **MausHaus DJ on server 3**, and be shared with the Wyss for their own deployment.

## Docs

The docs are in the docs/ folder. Please build with
``jupyter-book build ./docs``
