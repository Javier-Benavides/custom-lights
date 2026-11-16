"""Commands to test the chip by hand, with the service stopped."""
from . import settings as st
from .color import hex_to_rgb, to_linear
from .hardware import ite


def _open_chip():
    try:
        return ite.Controller()
    except PermissionError as e:
        print(f"No permission on the chip ({e.filename}). Run system/grant-chip-access.sh, or if the service is installed,"
              " stop it and use sudo.")
    except ite.NoController as e:
        print(e)
    return None


def diagnose():
    chip = _open_chip()
    if chip is None:
        return 1
    info = chip.read_info()
    print(f"Node: {chip.path}")
    for key in ("product", "device", "strips_detected", "firmware", "support", "name"):
        print(f"{key}: {info[key]}")
    print(f"chip: {info['chip']:#x}")
    for header in (1, 2, 3):
        value = info["calibration"][header - 1]
        order = ite.order_from_calibration(value)
        print(f"header {header}: calibration {value:#08x}, order {order if order else 'no data: using GRB'}")
    chip.close()
    return 0


def test_bytes(color, settings):
    """The same as the service, with gamma and limit. Without gamma, an orange looks almost white."""
    g = settings["general"]
    return tuple(min(255, round(c * g["max_brightness"] / 100 * 255)) for c in to_linear(hex_to_rgb(color), 1.0, g["gamma"]))


def _headers_of(zone, settings):
    zones = settings["zones"]
    if zone == "all":
        return [z["header"] for z in zones.values()]
    if zone in zones:
        return [zones[zone]["header"]]
    return [int(zone)] if zone in ("1", "2", "3") else []


def paint_test(colors_by_header):
    chip = _open_chip()
    if chip is None:
        return 1
    chip.start({h: len(c) for h, c in colors_by_header.items()})
    chip.paint(colors_by_header)
    chip.close()
    return 0


def test_color(args, settings):
    headers = _headers_of(args[0], settings) if len(args) == 2 else []
    if not headers or not st.HEX.fullmatch(args[1]):
        print("Usage: luces test ZONE '#RRGGBB'   (ZONE: case, cooler, all, 1, 2 or 3)")
        return 2
    color = test_bytes(args[1], settings)
    print(f"Bytes sent: red {color[0]}, green {color[1]}, blue {color[2]}")
    return paint_test({h: [color] * 64 for h in headers})


def test_chain(args, settings):
    headers = _headers_of(args[0], settings) if len(args) == 1 and args[0] != "all" else []
    if not headers:
        print("Usage: luces test-chain ZONE   (ZONE: case, cooler, 1, 2 or 3)")
        return 2
    colors = [(255, 0, 0)] * 8 + [(0, 255, 0)] * 8 + [(0, 0, 255)] * 8 + [(255, 255, 255)] * 8
    print("If every fan turns red, they are in parallel. If each one has another color, they are chained.")
    return paint_test({headers[0]: colors + [(0, 0, 0)] * 32})
