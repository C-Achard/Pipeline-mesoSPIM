import sys

sys.path.append("")
import datajoint as dj

schema = dj.schema("user", locals(), create_tables=True)


@schema
class User(dj.Manual):
    definition = """
    name:       varchar(128)
    ---
    email:      varchar(128)
    """
