"""The Terncy utils."""


def get_attr_value(attrs, key):
    """Read attr value from terncy attributes."""
    for att in attrs:
        if "attr" in att and att["attr"] == key:
            return att["value"]
    return None
