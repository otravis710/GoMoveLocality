# GoMoveLocality
Codebase for Owen Travis's undergraduate senior thesis on move locality in the game of Go.

Contains the following files:

1. `distance.py` for reading SGF files, identifying suspected robots, and calculating the distance between successive moves. (∼ 150 lines)
2. `accuracy.py` for reading SGF files, identifying suspected robots, spawning sub-processes running KataGo, and determining the optimal move in each position. The core logic of this code is rooted in files written for our previous work (see Travis et al. 2023). (∼ 300 lines)
3. `run.slurm` for launching a Slurm job on the Della cluster at Princeton Research
Computing. This file is heavily based on materials published by [Princeton
Research Computing](https://researchcomputing.princeton.edu/support/knowledge-base/slurm) (∼ 20 lines)
4. `sgfmillplus.py` for modularization through the isolation of helper functions built on top of the Sgfmill Python library. This is an April 2024 version of a library in development [here](https://github.com/otravis710/sgfmillplus) (∼ 150 lines)
5. `distanceanalysis.rmd` for processing the output of distance.py, aggregating statistics, and generating figures. (∼ 450 lines)
6. `accuracyanalysis.rmd` for processing the output of accuracy.py, aggregating statistics, and generating figures. (∼ 400 lines)
