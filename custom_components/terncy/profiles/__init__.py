from homeassistant.const import MAJOR_VERSION, MINOR_VERSION


if (MAJOR_VERSION, MINOR_VERSION) >= (2023, 7):
    from .profiles import PROFILES
else:
    from .before_2023_7 import PROFILES
