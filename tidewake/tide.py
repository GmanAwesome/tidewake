"""The tides of light and dusk that replace day and night.

phase 0.0 = height of the light tide, 0.5 = depth of the dusk tide. Light tides make
things grow; dusk tides make crystals, blooms and glowcaps shine and grow taller.
"""
import math

import numpy as np

# (dusk, zenith, horizon, sun colour, ambient top, ambient bottom, cloud top, cloud deep, glow)
KEYS = [
    (0.00, (0.46, 0.66, 0.94), (0.96, 0.89, 0.86), (1.00, 0.93, 0.82), (0.56, 0.62, 0.76), (0.46, 0.41, 0.44),
     (1.00, 0.97, 0.96), (0.78, 0.76, 0.90), 0.55),
    (0.50, (0.36, 0.40, 0.70), (1.00, 0.66, 0.52), (1.00, 0.66, 0.42), (0.46, 0.42, 0.60), (0.40, 0.30, 0.36),
     (1.00, 0.80, 0.70), (0.66, 0.48, 0.66), 1.0),
    (1.00, (0.07, 0.08, 0.22), (0.38, 0.28, 0.50), (0.30, 0.32, 0.58), (0.24, 0.24, 0.42), (0.20, 0.15, 0.28),
     (0.52, 0.48, 0.74), (0.20, 0.16, 0.34), 1.7),
]


def dusk_amount(phase):
    return 0.5 - 0.5 * math.cos(2 * math.pi * phase)


def name(phase):
    d = dusk_amount(phase)
    rising = (phase % 1.0) > 0.5
    if d < 0.25:
        return 'Lighttide'
    if d > 0.75:
        return 'Dusktide'
    return 'Turning to light' if rising else 'Turning to dusk'


def atmosphere(phase):
    d = dusk_amount(phase)
    for a, b in zip(KEYS, KEYS[1:]):
        if a[0] <= d <= b[0]:
            t = (d - a[0]) / (b[0] - a[0])
            break
    vals = [np.array(x) * (1 - t) + np.array(y) * t for x, y in zip(a[1:8], b[1:8])]
    glow = a[8] * (1 - t) + b[8] * t
    ang = 2 * math.pi * phase
    # the sun swings low across the sky as dusk deepens, but never quite sets
    elev = math.radians(62 - 54 * d)
    az = ang * 0.5 + 0.6
    sun = np.array([math.cos(elev) * math.cos(az), math.sin(elev), math.cos(elev) * math.sin(az)])
    moon = np.array([-math.cos(0.7) * math.cos(az + 0.9), math.sin(0.7), -math.cos(0.7) * math.sin(az + 0.9)])
    z, hzn, sc, at, ab, ct, cd = vals
    light_dir = sun * (1 - d) + moon * d
    light_dir = light_dir / np.linalg.norm(light_dir)
    return {'dusk': d, 'zenith': z, 'horizon': hzn, 'sun_col': sc, 'amb_top': at, 'amb_bot': ab,
            'cloud_top': ct, 'cloud_deep': cd, 'glow': glow, 'sun_dir': sun, 'moon_dir': moon,
            'light_dir': light_dir}
