"""Where everything lives. Tests move these folders with environment variables."""
import os

CONTROL = os.environ.get("LUCES_CONTROL", "/var/lib/luces/control")   # the user's: mode, settings, place
DATA = os.environ.get("LUCES_DATA", "/var/lib/luces/data")            # weather and solar activity
RUN = os.environ.get("LUCES_RUN", "/run/luces")                       # service status, in RAM
DEFAULT_SETTINGS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.toml")


def control(name):
    return os.path.join(CONTROL, name)


def data(name):
    return os.path.join(DATA, name)


def run(name):
    return os.path.join(RUN, name)
