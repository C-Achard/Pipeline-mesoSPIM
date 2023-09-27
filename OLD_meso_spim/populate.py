from schema import mice, user


def prepare_database():
    """Populate some example entries into the manual tables."""
    mice.Mouse.insert1(dict(mouse_name="test_mouse"))
    user.User.insert1(dict(name="John Doe", email="john@doe.org"))
