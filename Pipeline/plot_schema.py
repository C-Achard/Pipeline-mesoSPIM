import os
import login
import datajoint as dj
import matplotlib.pyplot as plt
import sys

sys.path.append("schema")
sys.path.append("scripts")

login.connectToDatabase()
from schema import mice, spim, user

my_erd = dj.ERD(spim)
fig = my_erd.draw()

# Save the figure
fig.savefig("diagram.png")
