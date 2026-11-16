"""Cloud cover seen from space: GOES infrared imagery through NASA GIBS.

An airport does not report high clouds: CAVOK only speaks of what is under 1500 m or the minimum sector altitude, which is
high near mountains.
"""
import time

from .. import settings
from .fetch import InvalidData, fetch_bytes
from .png import read_png

URL = ("https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?SERVICE=WMS&REQUEST=GetMap&VERSION=1.3.0"
       "&LAYERS=GOES-East_ABI_Band13_Clean_Infrared&CRS=EPSG:4326&BBOX={},{},{},{}"
       "&WIDTH=48&HEIGHT=48&FORMAT=image/png&TIME={}")
DELAYS_MIN = (40, 50, 60, 70, 80)        # the image takes about 40 minutes to be published
GRAY_PER_K, GRAY_ZERO_K = 2.83, 330.0    # estimated from sample images: NASA does not publish this scale


def cloud_fraction(pixels, temperature, adjust):
    """From 0 to 1, the part of the infrared image with clouds, or None if it is not published yet.

    In this image brighter is colder, and the coldest comes out in color. A cloud is colder than the ground, and there
    are two tests because each one fails alone: comparing with the ground sees thin clouds, but with everything covered
    no ground is left; comparing with the air temperature sees an overcast sky.
    """
    grays, cold = [], 0
    for r, g, b, a in pixels:
        if not a:
            continue
        if max(r, g, b) - min(r, g, b) > 8:
            cold += 1
        else:
            grays.append(r)
    total = len(grays) + cold
    if total * 2 < len(pixels):
        return None
    grays.sort()
    ground = grays[len(grays) // 10] if grays else 0
    air = (GRAY_ZERO_K - (temperature + 273.15 - adjust["margin_k"])) * GRAY_PER_K
    threshold = min(ground + adjust["contrast"], air)
    return (cold + sum(1 for x in grays if x > threshold)) / total


def add_satellite(weather, box, now, fetch_image=fetch_bytes):
    """Adds what the satellite sees to the airport's report."""
    adjust = settings.load()["sky"]["satellite"]
    for delay in DELAYS_MIN:
        moment = int((now - delay * 60) // 600) * 600
        image = read_png(fetch_image(URL.format(*box, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(moment)))))
        coverage = cloud_fraction(image, weather["temperature"], adjust)
        if coverage is not None:
            weather.update(airport_coverage=weather["coverage"], satellite_coverage=round(coverage, 3), satellite_time=moment,
                           coverage=max(weather["coverage"], round(coverage, 3)))
            return
    raise InvalidData("the satellite has no recent images")
