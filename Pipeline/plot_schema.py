import os
import datajoint as dj
import login
from schema import mice, spim, user
from matplotlib import pyplot as plt

# os.getcwd()
# if 'tutorial' in os.getcwd():
#    print('Changing working directory to:')
#    %cd ..
# else:
#    print('Working directory: %s' %os.getcwd())

# Login with credentials from login.py file (create this file from login_TEMPLATE.py)
dj.config["database.host"] = login.getIP()
dj.config["database.user"] = login.getUser()
dj.config["database.password"] = login.getPassword()
dj.conn()

dj.ERD(mice)
dj.ERD(user)

dj.ERD(spim).save("diagram.png")

# dj.ERD(mice)+dj.ERD(spim)+dj.ERD(user)
