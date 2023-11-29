import os
import datajoint as dj
import login
import matplotlib.pyplot as plt
import sys

sys.path.append("./scripts")
sys.path.append("./schema")

login.connectToDatabase()
from schema import mice, spim, user

my_erd = dj.ERD(spim)
fig = my_erd.draw()

# Save the figure
fig.savefig("diagram.png")
