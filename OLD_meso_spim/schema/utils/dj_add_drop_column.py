"""The following is provided as a convenience utility to be able to add/drop non primary key attributes to an existing DataJoint table.

Both function should work as is - you can simply copy and paste them and start using it without worrying about importing dependencies.
WARNING! These functions are NOT officially supported by DataJoint and make use of DataJoint internal logic
that is considered to be NOT part of the public API. These functions may cease to work or worse yet result
in unexpected results without any prior notice, and therefore should be used with atmost care.
We are working to add such "ALTER" method to DataJoint Python officially, and you can track the discussion/progress
at https://github.com/datajoint/datajoint-python/issues/110.

https://gist.github.com/eywalker/dd836149c3a1d2a03b32a50bbd88b7e4

See usage example below
"""


def add_column(table, name, dtype, default_value=None, comment=None):
    """A (hacky) convenience function to add a new column into an existing table.

    Args:
        table (DataJoint table class/instance): table to add new column (attribute) to
        name (str): name of the new column
        dtype (str): data type of the new column
        default_value (str, optional): default value for the new column. If 'null' or None, then the attribute
            is considered non-required. Defaults to None.
        comment (str, optional): comment for the new column
    """
    full_table_name = table.full_table_name
    if (
        default_value is None
    ):  # (bugfix Adrian to avoid error with int values) or default_value.strip().lower() == 'null':
        query = "ALTER TABLE {} ADD {} {}".format(full_table_name, name, dtype)
    else:
        query = "ALTER TABLE {} ADD {} {} NOT NULL DEFAULT {}".format(
            full_table_name, name, dtype, repr(default_value)
        )
    if comment is not None:
        query += ' COMMENT "{}"'.format(comment)
    table.connection.query(query)
    print("Be sure to add following entry to your table definition")
    definition = "{}={}: {}".format(name, repr(default_value), dtype)
    if comment is not None:
        definition += " # {}".format(comment)
    print(definition)
    table.__class__._heading = None


def drop_column(table, name):
    """Convenience function to drop specified column with name from the table.

    A primary key attribute may not be dropped. If name specifies a primary
    key attribute, this function raises a `ValueError`.

    Args:
        table (DataJoint table class/instance): table to drop an attribute from
        name (str): name of the attribute to be dropped. Cannot be a primary key attribute.
    """
    from datajoint.utils import user_choice

    if name in table.primary_key:
        raise ValueError("You cannot drop a primary key attribute")
    if name not in table.heading.attributes:
        raise AttributeError("column {} not found in the table".format(name))
    choice = user_choice(
        'You are about to drop the column "{}". Proceed?'.format(name),
        default="no",
    )
    if choice == "yes":
        query = "ALTER TABLE {} DROP COLUMN {}".format(
            table.full_table_name, name
        )
        table.connection.query(query)
        table.__class__._heading = None
        print('Dropeed column "{}"'.format(name))
    else:
        print("Aborting column drop")


#
#
## Let User be a DataJoint table with the following table definition
#
# @schema
# class User(dj.Manual):
#  definition = """
#  user_id :  int            # unique user identifier
#  ---
#  user_name: varchar(128)   # name of the user
#  """
#
#
#
## To add a new column that would have corresponded to the following DataJoint definition entry
## email="info@example.com": varchar(128)    # email address
# add_column(User, 'email', 'varchar(128)', 'info@example.com', 'email address')
#
## To drop a non primary-key column from the table
# drop_column(User, 'user_name')
#
