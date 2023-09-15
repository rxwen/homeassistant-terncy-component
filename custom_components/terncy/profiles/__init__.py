from homeassistant.const import MAJOR_VERSION, MINOR_VERSION


if MAJOR_VERSION > 2023 or (MAJOR_VERSION == 2023 and MINOR_VERSION >= 7):
    from .profiles import PROFILES
else:
    from .before_2023_7 import PROFILES
