#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Created on Wed Mar 28 10:52:49 2018.

@author: adrian.

Functions that return the password, user name and ip address for the local user
Rename this file to login.py after changing your name and password.

"""


def getIP():
    """Return ip address of the server."""  # points to DataJoint tutorial database in Docker
    return "127.0.0.1"


def getUser():
    """Return user name."""
    return "root"


def getPassword():
    """Return password."""
    return "tutorial"


def connectToDatabase():
    """Connects to the database using the credentials in the login.py file."""
    import datajoint as dj

    dj.config["database.host"] = getIP()
    dj.config["database.user"] = getUser()
    dj.config["database.password"] = getPassword()
    dj.config["enable_python_native_blobs"] = True
    dj.conn()
