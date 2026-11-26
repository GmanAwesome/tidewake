"""Cheap distant landmark for the lesson island: a floating citadel and glowing spire.

Drawn as a static VERT mesh (a few hundred large prisms), not voxels, so it
costs almost nothing at draw time and has no collision or chunk cost. It sits
on the -Z horizon from spawn, inside tutorial fog, and is not reachable from
the lesson island.
"""
import numpy as np

from . import models as MD
from . import materials as MT
from .config import LAYER

# World-space anchor (centre of the citadel keep). Visible looking yaw 0 from spawn.
POS = (0.0, 88.0, -310.0)
# Tip of the glowing spire, used for a single point light.
SPIRE_TIP = (0.0, 168.0, -310.0)

# Stone / roof / glow palettes (linear-ish mid tones, not atlas samples).
STONE_T = (0.62, 0.58, 0.70)
STONE_S = (0.42, 0.38, 0.52)
KEEP_T = (0.72, 0.68, 0.78)
KEEP_S = (0.48, 0.42, 0.58)
ROOF_T = (0.28, 0.22, 0.46)
ROOF_S = (0.18, 0.14, 0.32)
CLOUD_T = (0.92, 0.90, 0.98)
CLOUD_S = (0.74, 0.76, 0.88)
GOLD_T = (0.86, 0.70, 0.38)
GOLD_S = (0.62, 0.46, 0.22)
SPIRE_T = (0.86, 0.78, 1.00)
SPIRE_S = (0.52, 0.40, 0.92)
ORB_T = (0.95, 0.90, 1.00)
ORB_S = (0.70, 0.55, 1.00)
TREE_T = (0.45, 0.62, 0.48)
TREE_S = (0.22, 0.36, 0.28)

_MESH = None


def _prism(cx, cz, y0, y1, rad, ctop, cside, emit=0.0, sky=1.0):
    return MD.prisms(cx, cz, y0, y1, rad, ctop, cside, emit=emit, sky=sky)


def mesh():
    """World-space VERT mesh, built once."""
    global _MESH
    if _MESH is not None:
        return _MESH
    x0, y0, z0 = POS
    parts = []

    def add(*args, **kw):
        parts.append(_prism(*args, **kw))

    # Floating cloud terrace under the citadel (a few large soft disks).
    for i, (dx, dz, rad, yb, yh) in enumerate((
        (0, 0, 28, y0 - 22, y0 - 14),
        (10, 8, 16, y0 - 18, y0 - 12),
        (-12, -6, 18, y0 - 20, y0 - 13),
        (16, -10, 12, y0 - 16, y0 - 11),
        (-8, 14, 14, y0 - 17, y0 - 12),
        (0, -16, 15, y0 - 19, y0 - 13),
        (22, 4, 9, y0 - 15, y0 - 10),
        (-20, 2, 10, y0 - 16, y0 - 11),
    )):
        add(x0 + dx, z0 + dz, yb, yh, rad, CLOUD_T, CLOUD_S, emit=0.08, sky=1.0)

    # Lower bailey / wall ring (hex-ish plan of large prisms).
    wall_y0, wall_y1 = y0 - 10, y0 + 10
    for ang in range(6):
        a = np.radians(ang * 60)
        wx, wz = x0 + 16 * np.cos(a), z0 + 16 * np.sin(a)
        add(wx, wz, wall_y0, wall_y1, 7.2, STONE_T, STONE_S)
        # merlons
        add(wx, wz, wall_y1, wall_y1 + 3.2, 5.4, STONE_T, STONE_S)
        # corner towers
        tx, tz = x0 + 20 * np.cos(a + np.radians(30)), z0 + 20 * np.sin(a + np.radians(30))
        add(tx, tz, y0 - 12, y0 + 18, 5.0, KEEP_T, KEEP_S)
        add(tx, tz, y0 + 18, y0 + 24, 6.2, ROOF_T, ROOF_S, emit=0.04)
        add(tx, tz, y0 + 24, y0 + 28, 2.4, GOLD_T, GOLD_S, emit=0.35)

    # Keep / hall
    add(x0, z0, y0 - 8, y0 + 22, 11.0, KEEP_T, KEEP_S)
    add(x0, z0, y0 + 22, y0 + 30, 13.0, ROOF_T, ROOF_S, emit=0.05)
    add(x0 + 6, z0 + 4, y0 - 6, y0 + 14, 6.0, STONE_T, STONE_S)
    add(x0 - 5, z0 - 3, y0 - 6, y0 + 16, 5.4, STONE_T, STONE_S)

    # Foregate facing spawn (+Z toward the lesson island)
    add(x0, z0 + 22, y0 - 8, y0 + 8, 6.5, STONE_T, STONE_S)
    add(x0, z0 + 22, y0 + 8, y0 + 14, 4.0, GOLD_T, GOLD_S, emit=0.2)
    add(x0 - 7, z0 + 20, y0 - 8, y0 + 16, 3.6, KEEP_T, KEEP_S)
    add(x0 + 7, z0 + 20, y0 - 8, y0 + 16, 3.6, KEEP_T, KEEP_S)

    # Giant glowing spire
    sy0 = y0 + 28
    for i, (rad, h) in enumerate(((5.5, 10), (4.4, 12), (3.2, 14), (2.2, 16), (1.4, 18), (0.8, 16))):
        add(x0, z0, sy0, sy0 + h, rad, SPIRE_T, SPIRE_S, emit=0.85, sky=1.0)
        sy0 += h
    # Orb at the tip
    tip_y = sy0
    add(x0, z0, tip_y, tip_y + 8, 3.6, ORB_T, ORB_S, emit=1.0)
    add(x0, z0, tip_y + 8, tip_y + 12, 2.0, ORB_T, ORB_S, emit=1.0)

    # A couple of hanging lanterns under the bailey
    for dx, dz in ((-14, 8), (14, 6), (4, -14), (-8, -10)):
        add(x0 + dx, z0 + dz, y0 - 8, y0 - 4, 1.6, GOLD_T, GOLD_S, emit=0.7)

    # A hint of a sky-tree off to one side of the citadel, for silhouette
    add(x0 - 26, z0 - 8, y0 - 10, y0 + 20, 3.2, (0.46, 0.32, 0.22), (0.32, 0.20, 0.14))
    add(x0 - 26, z0 - 8, y0 + 16, y0 + 34, 10.0, TREE_T, TREE_S, emit=0.06)
    add(x0 - 22, z0 - 12, y0 + 22, y0 + 38, 7.0, TREE_T, TREE_S, emit=0.06)

    _MESH = MD.cat(*parts)
    return _MESH


def mesh_rel(cam):
    """Camera-relative VERT mesh for session.dynamic_models."""
    v = mesh().copy()
    if len(v):
        v['p'] = v['p'] - np.asarray(cam, dtype=np.float32)
    return v


def lights(cam):
    """One extra point light at the spire tip, camera-relative."""
    lamp = MT.ID.get('violet_crystal_lamp', MT.ID.get('cosmic_star', MT.ID['lantern']))
    tx, ty, tz = SPIRE_TIP
    return (tx - cam[0], ty - cam[1], tz - cam[2], lamp)


def visible_from_spawn(yaw=0.0, pitch=4.0, fov=70.0):
    """Whether the citadel centre sits in the default spawn view (tests / docs)."""
    # Spawn camera looks yaw 0 down -Z, slightly up. Landmark is on -Z.
    # Horizontal bearing from spawn (0,0,0-ish) to POS is 180° from +Z = yaw 0.
    dx, dy, dz = POS[0] - 0.0, POS[1] - 48.0, POS[2] - 0.0
    bearing = np.degrees(np.arctan2(dx, -dz))  # 0 when on -Z
    elev = np.degrees(np.arctan2(dy, np.hypot(dx, dz)))
    half = 0.5 * fov
    return abs(bearing - yaw) < half and abs(elev - pitch) < half
