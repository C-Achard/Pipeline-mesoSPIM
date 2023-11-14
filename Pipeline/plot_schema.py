import os
import datajoint as dj
import login

import sys

sys.path.append("./scripts")
sys.path.append("./schema")

login.connectToDatabase()
from schema import mice, spim, user

# os.getcwd()
# if 'tutorial' in os.getcwd():
#    print('Changing working directory to:')
#    %cd ..
# else:
#    print('Working directory: %s' %os.getcwd())

# Login with credentials from login.py file (create this file from login_TEMPLATE.py)

# dj.ERD(mice)
# dj.ERD(user)

d = dj.ERD(spim)
d.save("diagram.png")

# dj.ERD(mice)+dj.ERD(spim)+dj.ERD(user)
