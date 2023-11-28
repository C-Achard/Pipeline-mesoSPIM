import os
import datajoint as dj
import login

import sys

sys.path.append("./scripts")
sys.path.append("./schema")

login.connectToDatabase()
from schema import mice, spim, user

d = dj.ERD(spim)
d.save("diagram.png")
