#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Created on Thu May 10 10:40:28 2018.

@author: adrian

Set of functions as a wrapper for gitpython.

"""

try:
    import git
except ImportError as e:
    errorMessage = (
        "The import of gitpython failed!!\n"
        + 'Install gitpython using "pip install gitpython" or use '
        + "a different docker container which contains gitpython"
    )

    raise ImportError(errorMessage) from e


def get_last_commit_date():
    """Returns the date of the last commit in the format 'YYYY-MM-DD'.

    The return value can be saved as a datajoint date value
    """
    repo = git.Repo(search_parent_directories=True)
    datetime = repo.head.commit.committed_datetime

    return "{}".format(datetime.date())


def get_last_commit_hash():
    """Returns the hash value (id) of the last commit as a string.

    This hash code can be used to track the version of the GitHub repository at that
    time (see https://github.com/MMathisLab/DataJoint_mathis/tree/ENTER_HASH_HERE)
    """
    repo = git.Repo(search_parent_directories=True)
    return repo.head.object.hexsha
