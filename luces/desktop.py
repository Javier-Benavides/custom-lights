"""Desktop niceties on GNOME: notifications, a keyboard shortcut and a dock icon."""
import ast
import shutil
import subprocess

KEYS_SCHEMA = "org.gnome.settings-daemon.plugins.media-keys"
SHORTCUT_PATH = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/luces/"
ICON = "luces.desktop"
DEFAULT_KEY = "<Super>F12"


def notify(text):
    """For the click and the shortcut, where there is no terminal. Each notice replaces the last."""
    if shutil.which("notify-send"):
        subprocess.run(["notify-send", "-a", "Luces", "-i", "weather-clear", "-t", "2500",
                        "-h", "string:x-canonical-private-synchronous:luces", text],
                       check=False, timeout=5, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _gsettings(*args):
    return subprocess.run(["gsettings", *args], capture_output=True, text=True, check=True).stdout.strip()


def _as_list(text):
    return ast.literal_eval(text.removeprefix("@as ").strip())


def shortcut(args, gsettings=_gsettings):
    """Shortcut and dock icon. They belong to the user's session, so no sudo."""
    remove = args[:1] == ["remove"]
    key = args[0] if args and not remove else DEFAULT_KEY
    shortcuts = _as_list(gsettings("get", KEYS_SCHEMA, "custom-keybindings"))
    icons = _as_list(gsettings("get", "org.gnome.shell", "favorite-apps"))
    if remove:
        shortcuts = [s for s in shortcuts if s != SHORTCUT_PATH]
        icons = [i for i in icons if i != ICON]
    else:
        schema = f"{KEYS_SCHEMA}.custom-keybinding:{SHORTCUT_PATH}"
        gsettings("set", schema, "name", "Luces: next mode")
        gsettings("set", schema, "command", "/usr/local/bin/luces next")
        gsettings("set", schema, "binding", key)
        shortcuts = shortcuts if SHORTCUT_PATH in shortcuts else [*shortcuts, SHORTCUT_PATH]
        icons = icons if ICON in icons else [*icons, ICON]
    gsettings("set", KEYS_SCHEMA, "custom-keybindings", str(shortcuts))
    gsettings("set", "org.gnome.shell", "favorite-apps", str(icons))
    print("Shortcut and icon removed." if remove else f"Done: {key} goes to the next mode, and the Luces icon is in the dock.")
    return 0
