"""Hex lattice maths (pointy-top hexagons, axial coordinates q, r; layers y).

    world x = HEX * sqrt(3) * (q + r / 2)
    world z = HEX * 1.5 * r
    world y = y * LAYER          (bottom of the cell)
"""
import math

import numpy as np

from .config import HEX, LAYER, SQ3, CHUNK

# the six neighbours, in counter-clockwise order of their direction angle
DIRS = [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]


def center(q, r):
    return HEX * SQ3 * (q + r * 0.5), HEX * 1.5 * r


def _dir_angle(d):
    x, z = center(*d)
    return math.atan2(z, x)


DIR_ANGLES = [_dir_angle(d) for d in DIRS]
# corner k sits between direction k and direction k+1
CORNER_ANGLES = [a + math.radians(30) for a in DIR_ANGLES]
CORNERS = np.array([[HEX * math.cos(a), HEX * math.sin(a)] for a in CORNER_ANGLES])   # (6, 2) x, z
DIR_NORMALS = np.array([[math.cos(a), math.sin(a)] for a in DIR_ANGLES])
INRADIUS = HEX * SQ3 / 2


def cell_at(x, z):
    """World (x, z) -> axial (q, r) of the hex containing it."""
    qf = (SQ3 / 3 * x - z / 3) / HEX
    rf = (2 / 3 * z) / HEX
    return cube_round(qf, rf)


def cube_round(qf, rf):
    sf = -qf - rf
    q, r, s = round(qf), round(rf), round(sf)
    dq, dr, ds = abs(q - qf), abs(r - rf), abs(s - sf)
    if dq > dr and dq > ds:
        q = -r - s
    elif dr > ds:
        r = -q - s
    return int(q), int(r)


def layer_at(y):
    return math.floor(y / LAYER)


def hex_distance(q1, r1, q2, r2):
    dq, dr = q1 - q2, r1 - r2
    return (abs(dq) + abs(dr) + abs(dq + dr)) // 2


def ring(q, r, radius):
    if radius == 0:
        return [(q, r)]
    out = []
    cq, cr = q + DIRS[4][0] * radius, r + DIRS[4][1] * radius
    for i in range(6):
        for _ in range(radius):
            out.append((cq, cr))
            d = DIRS[i]
            cq, cr = cq + d[0], cr + d[1]
    return out


def spiral(q, r, radius):
    out = []
    for k in range(radius + 1):
        out += ring(q, r, k)
    return out


def chunk_of(q, r):
    return q // CHUNK, r // CHUNK


def chunk_origin(cq, cr):
    return center(cq * CHUNK, cr * CHUNK)


def chunk_center(cq, cr):
    return center(cq * CHUNK + CHUNK / 2 - 0.5, cr * CHUNK + CHUNK / 2 - 0.5)


def hex_sdf(px, pz):
    """Signed distance from local point (relative to a cell centre) to the hexagon's outline."""
    # pointy-top: flat edges at x = +-INRADIUS. Rotate into iq's layout (flat edges at y = +-r).
    kx, ky, kz = -0.866025404, 0.5, 0.577350269
    x, y = abs(pz), abs(px)
    d = 2.0 * min(kx * x + ky * y, 0.0)
    x -= d * kx
    y -= d * ky
    r = INRADIUS
    x -= max(-kz * r, min(kz * r, x))
    y -= r
    return math.hypot(x, y) * (1 if y > 0 else -1)
