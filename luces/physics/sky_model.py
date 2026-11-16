"""The color of a clear sky from first principles. The scenes do not use it: it is a tool to understand and compare.

Spherical atmosphere with Rayleigh scattering, aerosol and ozone (Chappuis band), single scattering with the correction
of SKYCOLOR for multiple scattering. Solar spectrum and ozone cross section: Eric Bruneton,
precomputed_atmospheric_scattering (2017, BSD-3-Clause), see NOTICE.md. Color matching: Wyman, Sloan and Shirley (2013).
Theory, results and limits: docs/physics/sky-color.md.
"""
import math

SOLAR_IRRADIANCE = [
    1.11776, 1.14259, 1.01249, 1.14716, 1.72765, 1.73054, 1.6887, 1.61253, 1.91198, 2.03474, 2.02042, 2.02212, 1.93377,
    1.95809, 1.91686, 1.8298, 1.8685, 1.8931, 1.85149, 1.8504, 1.8341, 1.8345, 1.8147, 1.78158, 1.7533, 1.6965, 1.68194,
    1.64654, 1.6048, 1.52143, 1.55622, 1.5113, 1.474, 1.4482, 1.41018, 1.36775, 1.34188, 1.31429, 1.28303, 1.26758, 1.2367,
    1.2082, 1.18737, 1.14683, 1.12362, 1.1058, 1.07124, 1.04992]
OZONE_CROSS_SECTION = [
    1.18e-27, 2.182e-28, 2.818e-28, 6.636e-28, 1.527e-27, 2.763e-27, 5.52e-27, 8.451e-27, 1.582e-26, 2.316e-26, 3.669e-26,
    4.924e-26, 7.752e-26, 9.016e-26, 1.48e-25, 1.602e-25, 2.139e-25, 2.755e-25, 3.091e-25, 3.5e-25, 4.266e-25, 4.672e-25,
    4.398e-25, 4.701e-25, 5.019e-25, 4.305e-25, 3.74e-25, 3.215e-25, 2.662e-25, 2.238e-25, 1.852e-25, 1.473e-25, 1.209e-25,
    9.423e-26, 7.455e-26, 6.566e-26, 5.105e-26, 4.15e-26, 4.228e-26, 3.237e-26, 2.451e-26, 2.801e-26, 2.534e-26, 1.624e-26,
    1.465e-26, 2.078e-26, 1.383e-26, 7.105e-27]   # both tables: every 10 nm from 360 nm
EARTH_RADIUS_KM, TOP_KM = 6371.0, 90.0
WAVELENGTHS_NM = list(range(400, 701, 20))
AIR_SCALE_KM = 8.0
OZONE_PEAK_KM, OZONE_HALF_WIDTH_KM = 25, 15
PHASE_RAYLEIGH = 3 / (16 * math.pi)


def _gaussian(x, mean, below, above):
    width = below if x < mean else above
    return math.exp(-0.5 * ((x - mean) / width) ** 2)


def color_matching(nm):
    """CIE XYZ color matching functions, as fitted by Wyman, Sloan and Shirley (2013)."""
    return (1.056 * _gaussian(nm, 599.8, 37.9, 31.0) + 0.362 * _gaussian(nm, 442.0, 16.0, 26.7)
            - 0.065 * _gaussian(nm, 501.1, 20.4, 26.2),
            0.821 * _gaussian(nm, 568.8, 46.9, 40.5) + 0.286 * _gaussian(nm, 530.9, 16.3, 31.1),
            1.217 * _gaussian(nm, 437.0, 11.8, 36.0) + 0.681 * _gaussian(nm, 459.0, 26.0, 13.8))


def rayleigh(nm):
    """Scattering per km at sea level. The λ⁻⁴ law is why the sky is blue."""
    return 1.24062e-3 / (nm / 1000) ** 4


def to_hex(rgb, gamma=2.2):
    """A color scaled so its largest channel is full: it keeps the hue and drops the brightness."""
    top = max(max(rgb), 1e-12)
    channels = [max(0.0, x / top) ** (1 / gamma) for x in rgb]
    return "#" + "".join("%02X" % round(255 * x) for x in channels)


class Atmosphere:
    def __init__(self, aerosol_depth=0.15, angstrom=1.3, aerosol_height_km=1.5, ozone_du=300, asymmetry=0.75, albedo=0.92,
                 multiple=0.7, observer_km=0.6):
        self.aerosol_depth, self.angstrom, self.aerosol_height_km = aerosol_depth, angstrom, aerosol_height_km
        self.asymmetry, self.albedo, self.multiple, self.observer_km = asymmetry, albedo, multiple, observer_km
        ozone_peak = ozone_du * 2.687e20 / 15000.0 * 1000   # molecules per m² per km of column, at the peak
        self.bands = []
        for nm in WAVELENGTHS_NM:
            i = (nm - 360) // 10
            self.bands.append((nm, SOLAR_IRRADIANCE[i], rayleigh(nm),
                               aerosol_depth / aerosol_height_km * (nm / 550) ** -angstrom, OZONE_CROSS_SECTION[i] * ozone_peak))

    def densities(self, height_km):
        ozone = max(0.0, 1 - abs(height_km - OZONE_PEAK_KM) / OZONE_HALF_WIDTH_KM)
        return math.exp(-height_km / AIR_SCALE_KM), math.exp(-height_km / self.aerosol_height_km), ozone

    def column(self, point, direction, steps=40):
        """(air, aerosol, ozone) from a point to the top of the atmosphere, or None if the Earth is in the way."""
        totals = [0.0, 0.0, 0.0]
        x, y, z = point
        b = x * direction[0] + y * direction[1] + z * direction[2]
        c = x * x + y * y + z * z
        if b < 0 and c - b * b < EARTH_RADIUS_KM ** 2:
            return None
        length = -b + math.sqrt(max(0.0, b * b - c + (EARTH_RADIUS_KM + TOP_KM) ** 2))
        travelled = 0.0
        step = length * (1.08 - 1) / (1.08 ** steps - 1)   # growing steps: the air is thickest near the start
        for _ in range(steps):
            m = travelled + step / 2
            height = math.sqrt((x + direction[0] * m) ** 2 + (y + direction[1] * m) ** 2 + (z + direction[2] * m) ** 2) - EARTH_RADIUS_KM
            air, aerosol, ozone = self.densities(max(height, 0.0))
            totals[0] += air * step
            totals[1] += aerosol * step
            totals[2] += ozone * step
            travelled += step
            step *= 1.08
        return totals

    def optical_depth(self, column, band):
        _, _, air, aerosol, ozone = band
        return (self.multiple * air * column[0] + aerosol * column[1] * (1 - (1 - self.multiple) * self.albedo)
                + ozone * column[2])

    def sky_spectrum(self, sun_altitude, elevation, azimuth):
        """Spectrum towards a direction: `elevation` in degrees, and `azimuth` from the Sun (0 towards it, 180 opposite)."""
        sun_rad, elevation_rad, azimuth_rad = math.radians(sun_altitude), math.radians(elevation), math.radians(azimuth)
        sun = (math.cos(sun_rad), 0.0, math.sin(sun_rad))
        view = (math.cos(elevation_rad) * math.cos(azimuth_rad), math.cos(elevation_rad) * math.sin(azimuth_rad), math.sin(elevation_rad))
        cosine = sun[0] * view[0] + sun[1] * view[1] + sun[2] * view[2]
        rayleigh_phase = PHASE_RAYLEIGH * (1 + cosine ** 2)
        g = self.asymmetry
        aerosol_phase = (1 - g * g) / (4 * math.pi * (1 + g * g - 2 * g * cosine) ** 1.5)
        observer = EARTH_RADIUS_KM + self.observer_km
        b = observer * view[2]
        length = -b + math.sqrt(b * b - observer ** 2 + (EARTH_RADIUS_KM + TOP_KM) ** 2)
        steps, growth = 60, 1.06
        step = length * (growth - 1) / (growth ** steps - 1)
        travelled = 0.0
        seen = [0.0, 0.0, 0.0]
        spectrum = [0.0] * len(self.bands)
        for _ in range(steps):
            m = travelled + step / 2
            point = (view[0] * m, view[1] * m, observer + view[2] * m)
            height = math.sqrt(point[0] ** 2 + point[1] ** 2 + point[2] ** 2) - EARTH_RADIUS_KM
            air, aerosol, ozone = self.densities(max(height, 0.0))
            seen[0] += air * step / 2
            seen[1] += aerosol * step / 2
            seen[2] += ozone * step / 2
            to_sun = self.column(point, sun)
            if to_sun is not None:
                for i, band in enumerate(self.bands):
                    _, irradiance, air_scatter, aerosol_scatter, _ = band
                    source = air_scatter * air * rayleigh_phase + aerosol_scatter * aerosol * self.albedo * aerosol_phase
                    spectrum[i] += irradiance * source * math.exp(-self.optical_depth(seen, band) - self.optical_depth(to_sun, band)) * step
            seen[0] += air * step / 2
            seen[1] += aerosol * step / 2
            seen[2] += ozone * step / 2
            travelled += step
            step *= growth
        return spectrum

    def direct_spectrum(self, sun_altitude, height_km):
        """Spectrum of direct sunlight at a height: what lights a cloud from the side."""
        sun_rad = math.radians(sun_altitude)
        sun = (math.cos(sun_rad), 0.0, math.sin(sun_rad))
        to_sun = self.column((0.0, 0.0, EARTH_RADIUS_KM + height_km), sun, 60)
        if to_sun is None:
            return [0.0] * len(self.bands)
        return [band[1] * math.exp(-self.optical_depth(to_sun, band)) for band in self.bands]

    def to_xyz(self, spectrum):
        x = y = z = 0.0
        for value, band in zip(spectrum, self.bands):
            cx, cy, cz = color_matching(band[0])
            x += value * cx
            y += value * cy
            z += value * cz
        return x, y, z

    def to_rgb(self, spectrum):
        """Linear RGB and luminance, with the unattenuated Sun as white."""
        x, y, z = self.to_xyz(spectrum)
        white_x, white_y, white_z = self.to_xyz([band[1] for band in self.bands])
        x, y, z = x / white_x * 0.9505, y / white_y, z / white_z * 1.089
        return (3.2406 * x - 1.5372 * y - 0.4986 * z, -0.9689 * x + 1.8758 * y + 0.0415 * z, 0.0557 * x - 0.2040 * y + 1.0570 * z), y
