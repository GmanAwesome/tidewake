"""Little 3D models built from hex prisms: item sprites, held items, drops and creatures.

Tools are drawn like pixel-art sprites, but every pixel is a tiny hex column, so they
match the world. All functions return VERT arrays (see mesher.VERT) in local space.
"""
import math

import numpy as np

from .mesher import VERT, _prisms, pack
from . import materials as MT
from . import items as I


def prisms(cx, cz, y0, y1, rad, ctop, cside, emit=0.0, sky=1.0, mat=None, front=None):
    """Arrays (or scalars) of prism params -> VERT array."""
    cx = np.atleast_1d(np.asarray(cx, dtype=np.float64))
    n = len(cx)
    f = lambda v: np.broadcast_to(np.asarray(v, dtype=np.float64), (n,)).copy()
    c = lambda v: np.broadcast_to(np.asarray(v, dtype=np.float64), (n, 3)).copy()
    ct, cs = c(ctop), c(cside)
    fr = None if front is None else np.full(n, front)
    parts = _prisms(cx, f(cz), f(y0), f(y1), f(rad), ct, cs, cs * 0.85, f(pack(emit, sky)),
                    mat=None if mat is None else np.full(n, mat, np.uint8), front=fr)
    parts = [p for p in parts if len(p)]
    return np.concatenate(parts) if parts else np.zeros(0, VERT)


def cat(*arrs):
    arrs = [a for a in arrs if len(a)]
    return np.concatenate(arrs) if arrs else np.zeros(0, VERT)


def transform(v, yaw_deg=0.0, pitch_deg=0.0, roll_deg=0.0, scale=1.0, offset=(0, 0, 0), sy=1.0):
    """Rotate (roll about z, pitch about x, then yaw about y), scale and move a VERT array."""
    out = v.copy()
    P = out['p'].astype(np.float64)
    P[:, 1] *= sy
    N = out['n'][:, :3].astype(np.float64) / 127.5 - 1.0
    R = rot_matrix(yaw_deg, pitch_deg, roll_deg)
    P = P @ R.T * scale + np.asarray(offset, dtype=np.float64)
    N = N @ R.T
    out['p'] = P
    out['n'][:, :3] = np.clip(N * 127.5 + 127.5, 0, 255)
    return out


def rot_matrix(yaw, pitch=0.0, roll=0.0):
    a, b, c = math.radians(-yaw), math.radians(pitch), math.radians(roll)
    Ry = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
    Rx = np.array([[1, 0, 0], [0, math.cos(b), -math.sin(b)], [0, math.sin(b), math.cos(b)]])
    Rz = np.array([[math.cos(c), -math.sin(c), 0], [math.sin(c), math.cos(c), 0], [0, 0, 1]])
    return Ry @ Rx @ Rz


# ------------------------------------------------------------------ sprites
SPRITES = {
    'pick': ['..MMMMM..',
             '.MD.H.DM.',
             'M...H...M',
             '....H....',
             '....H....',
             '....H....',
             '....H....',
             '....H....'],
    'axe': ['.MMH.....',
            'MMMH.....',
            'MMDH.....',
            '.MMH.....',
            '...H.....',
            '...H.....',
            '...H.....',
            '...H.....'],
    'spade': ['...MMM...',
              '...MDM...',
              '...MMM...',
              '....M....',
              '....H....',
              '....H....',
              '....H....',
              '...HHH...'],
    'blade': ['....M....',
              '...MDM...',
              '...MDM...',
              '...MDM...',
              '...MDM...',
              '...MDM...',
              '..HHHHH..',
              '....H....',
              '....H....'],
    'stick': ['......H',
              '.....H.',
              '....H..',
              '...H...',
              '..H....',
              '.H.....',
              'H......'],
    'hoe':   ['...MMMM..',
              '...M..M..',
              '....H....',
              '....H....',
              '....H....',
              '....H....',
              '....H....',
              '...HHH...'],
    'rod':   ['.......M.',
              '......M.L',
              '.....M..L',
              '....H...L',
              '...H.....',
              '..H......',
              '.H.......',
              'H........'],
}


def sprite(rows, colors, px=0.11, depth=0.11):
    """Extrude a pixel sprite (rows top->bottom) into hex columns standing in the x-y plane."""
    h = len(rows)
    w = max(len(r) for r in rows)
    out = []
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch == '.' or ch not in colors:
                continue
            col, emit = colors[ch]
            x = (i - (w - 1) / 2) * px
            y = ((h - 1) / 2 - j) * px
            out.append((x, y, col, emit))
    if not out:
        return np.zeros(0, VERT)
    xs = np.array([o[0] for o in out])
    ys = np.array([o[1] for o in out])
    cols = np.array([o[2] for o in out])
    em = np.array([o[3] for o in out])
    # each pixel is a short hex column lying along z (rotate a vertical prism by 90 degrees)
    v = prisms(xs, -ys, np.full(len(xs), -depth / 2), np.full(len(xs), depth / 2), px * 0.6, cols, cols * 0.85, em)
    return transform(v, pitch_deg=90)


def _icon_front():
    """Which hex side faces the icon camera (yaw 30, pitch -30)."""
    from .hexgrid import DIR_NORMALS
    a = math.radians(30.0)
    fx, fz = math.sin(a), -math.cos(a)
    return max(range(6), key=lambda d: -(DIR_NORMALS[d][0] * fx + DIR_NORMALS[d][1] * fz))


ICON_FRONT = _icon_front()


def item_model(it):
    """VERT model of an item, about one unit across, centred on the origin."""
    if it is None:
        return np.zeros(0, VERT)
    c1 = np.array(it.color)
    c2 = np.array(it.color2)
    hcol = (np.array([0.66, 0.50, 0.34]), 0.0)
    if it.model == 'block':
        m = it.block
        emit = float(MT.EMIT[m])
        front = ICON_FRONT if m in (MT.ID['tinker_bench'], MT.ID['kiln'], MT.ID['chest']) else None
        if m == MT.ID['kiln']:
            emit = 0.6           # show the fire in the icon
        v = prisms(0, 0, -0.35, 0.35, 0.5, MT.TOP[m], MT.SIDE[m], emit, mat=m, front=front)
        if m == MT.ID['kiln']:
            v = cat(v, prisms(0.0, 0.0, 0.35, 0.62, 0.2, (0.70, 0.42, 0.36), (0.70, 0.42, 0.36), mat=MT.ID['bricks']))
        if m == MT.ID['tinker_bench']:
            v = cat(v, prisms(0.18, 0.10, 0.35, 0.47, 0.11, (0.42, 0.44, 0.50), (0.42, 0.44, 0.50)),
                    prisms(-0.2, -0.05, 0.35, 0.39, 0.09, (0.70, 0.52, 0.34), (0.70, 0.52, 0.34)))
        return v
    if it.model == 'deco':
        m = it.block
        parts = MT.PARTS.get(m, [(0.4, 0.0, 0.8, True)])
        out = []
        for rad, a, b, use_top in parts:
            if use_top == 'core':
                col = np.array([1.0, 0.9, 0.55])
            elif use_top == 'berry':
                col = np.array([0.62, 0.36, 0.86])
            else:
                col = MT.TOP[m] if use_top else MT.SIDE[m]
            out.append(prisms(0, 0, a - 0.5, b - 0.5, rad * 0.9, col, col * 0.9, float(MT.EMIT[m]) * (1 if use_top else 0.2), mat=m))
        return cat(*out)
    if it.model in SPRITES:
        dark = c1 * 0.75
        cols = {'M': (c1, 0.25 if it.tool and it.tool[1] == 4 else 0.0), 'D': (dark, 0.0), 'H': hcol}
        if it.model == 'stick':
            cols['H'] = (c1, 0.0)
        if it.model == 'rod':
            cols['M'] = (c1 * 0.85, 0.0)
            cols['L'] = (c2, 0.0)
        return sprite(SPRITES[it.model], cols)
    if it.model == 'ingot':
        return cat(prisms(0, 0, -0.12, 0.08, 0.34, c1, c1 * 0.85), prisms(0, 0, 0.08, 0.14, 0.24, c1 * 1.08, c1 * 0.9))
    if it.model == 'gem':
        return cat(prisms(0, 0, -0.30, 0.10, 0.22, c1, c1 * 0.85, 0.5), prisms(0, 0, 0.10, 0.30, 0.12, c1, c1 * 0.9, 0.5))
    if it.model == 'lump':
        return cat(prisms(0, 0, -0.22, 0.06, 0.28, c1, c1 * 0.85), prisms(0.06, 0.04, 0.06, 0.22, 0.18, c1 * 1.05, c2 * 0.95))
    if it.model == 'berries':
        xs, zs = np.array([-0.12, 0.12, 0.0]), np.array([0.05, 0.05, -0.14])
        return cat(prisms(xs, zs, -0.15, 0.08, 0.13, c1, c1 * 0.8), prisms(0, 0, 0.08, 0.2, 0.04, (0.4, 0.6, 0.35), (0.4, 0.6, 0.35)))
    if it.model == 'pie':
        return cat(prisms(0, 0, -0.15, 0.05, 0.42, c1, c1 * 0.85), prisms(0, 0, 0.05, 0.10, 0.32, c2, c2 * 0.9, 0.1))
    if it.model == 'pail':
        full = it.name.endswith('Water')
        v = cat(prisms(0, 0, -0.3, -0.24, 0.30, c1 * 0.8, c1 * 0.8), prisms(0, 0, -0.24, 0.25, 0.34, c1, c1 * 0.85))
        if full:
            v = cat(v, prisms(0, 0, 0.25, 0.27, 0.28, c2, c2))
        return v
    return prisms(0, 0, -0.3, 0.3, 0.3, c1, c1 * 0.85)


_cache = {}


def cached_item(iid):
    if iid not in _cache:
        _cache[iid] = item_model(I.get(iid))
    return _cache[iid]


# ------------------------------------------------------------------ creatures
_ccache = {}


def creature(kind, t, walking, color_seed=0.0, hurt=0.0):
    """Cached creature model: animation is quantised to 12 frames per cycle."""
    w = bool(walking)
    period = (2 * math.pi / 9.0) if kind != 'gloomling' and kind != 'brute' else (2 * math.pi / 7.0 if w else 2 * math.pi / 2.0)
    fr = int((t % period) / period * 12) % 12
    key = (kind, w, fr, hurt > 0, round(color_seed * 3))
    v = _ccache.get(key)
    if v is None:
        if len(_ccache) > 4000:
            _ccache.clear()
        v = _ccache[key] = _creature(kind, fr / 12 * period, w, key[4] / 3, hurt)
    return v


def _creature(kind, t, walking, color_seed=0.0, hurt=0.0):
    """Model of a creature at animation time t, in local space (feet at y=0, facing -z)."""
    swing = math.sin(t * 9.0) * 0.09 if walking else 0.0
    tint = np.array([1.0, 0.55, 0.55]) if hurt > 0 else np.array([1.0, 1.0, 1.0])
    if kind == 'woolhop':
        fluff = np.array([0.99, 0.95, 0.90]) * (0.94 + 0.06 * color_seed) * tint
        face = np.array([0.40, 0.32, 0.36]) * tint
        legs = cat(*[prisms(x, z, max(0, s), 0.36 + s, 0.08, face, face) for (x, z), s in
                     zip(((-0.22, -0.25), (0.22, -0.25), (-0.22, 0.25), (0.22, 0.25)), (swing, -swing, -swing, swing))])
        body = cat(prisms(0, 0.02, 0.32, 0.86, 0.50, fluff, fluff * 0.92), prisms(0, 0.02, 0.86, 0.96, 0.36, fluff, fluff * 0.92))
        head = cat(prisms(0, -0.52, 0.58, 0.98, 0.22, face, face), prisms(0, -0.48, 0.98, 1.06, 0.18, fluff, fluff),
                   prisms((-0.1, 0.1), (-0.71, -0.71), 0.80, 0.86, 0.035, (0.1, 0.1, 0.1), (0.1, 0.1, 0.1)))
        return cat(legs, body, head)
    if kind == 'pebblebeak':
        c = np.array([0.98, 0.86, 0.70]) * tint
        leg = np.array([0.95, 0.62, 0.30])
        bob = abs(math.sin(t * 9)) * 0.03 if walking else 0.0
        return cat(prisms((-0.08, 0.08), (0, 0), 0, 0.22 + bob, 0.035, leg, leg),
                   prisms(0, 0.04, 0.2 + bob, 0.52 + bob, 0.24, c, c * 0.92),
                   prisms(0, 0.22, 0.42 + bob, 0.60 + bob, 0.12, c * 0.9, c * 0.85),
                   prisms(0, -0.18, 0.50 + bob, 0.76 + bob, 0.13, c, c * 0.95),
                   prisms(0, -0.33, 0.58 + bob, 0.64 + bob, 0.05, leg, leg),
                   prisms(0, -0.16, 0.76 + bob, 0.82 + bob, 0.06, (0.95, 0.45, 0.45), (0.95, 0.45, 0.45)),
                   prisms((-0.07, 0.07), (-0.28, -0.28), 0.66 + bob, 0.70 + bob, 0.025, (0.1, 0.1, 0.1), (0.1, 0.1, 0.1)))
    if kind == 'mossback':
        shell = np.array([0.46, 0.68, 0.42]) * tint
        skin = np.array([0.72, 0.66, 0.50]) * tint
        return cat(*[prisms(x, z, 0, 0.2, 0.09, skin, skin) for x, z in ((-0.3, -0.3), (0.3, -0.3), (-0.3, 0.3), (0.3, 0.3))],
                   prisms(0, 0, 0.14, 0.42, 0.55, shell, shell * 0.8), prisms(0, 0, 0.42, 0.56, 0.38, shell * 1.05, shell * 0.85),
                   prisms(0, -0.58 - swing * 0.5, 0.18, 0.38, 0.16, skin, skin),
                   prisms((-0.07, 0.07), (-0.72, -0.72), 0.30, 0.34, 0.025, (0.1, 0.1, 0.1), (0.1, 0.1, 0.1)))
    if kind in ('gloomling', 'brute'):
        squash = 1.0 + (0.18 * math.sin(t * 7.0) if walking else 0.05 * math.sin(t * 2))
        c = np.array([0.30, 0.22, 0.46]) * tint
        eye = np.array([1.0, 0.86, 0.50])
        v = cat(prisms(0, 0, 0, 0.55, 0.40, c, c * 0.8, 0.1),
                prisms(0, 0, 0.55, 0.68, 0.28, c * 1.1, c * 0.9, 0.1),
                prisms((-0.14, 0.14), (-0.37, -0.37), 0.32, 0.44, 0.07, eye, eye, 1.0),
                prisms((-0.24, 0.24), (0.0, 0.0), 0.68, 0.84, 0.06, c * 1.2, c, 0.2))
        return transform(v, sy=squash)
    if kind == 'skywhale':
        # longer, flatter, whale-like: tapered body, thin pectorals, horizontal fluke
        tail = math.sin(t * 1.4) * 0.16
        flap = math.sin(t * 0.9) * 0.06
        skin = np.array([0.78, 0.88, 0.94]) * tint
        belly = np.array([0.94, 0.96, 0.98]) * tint
        mark = np.array([0.62, 0.74, 0.86]) * tint
        eye = np.array([0.12, 0.16, 0.22])
        return cat(
            prisms(0, -1.35, 0.38, 0.78, 0.18, skin, belly),
            prisms(0, -1.55, 0.48, 0.68, 0.10, skin * 0.96, belly),
            prisms((-0.16, 0.16), (-1.38, -1.38), 0.62, 0.70, 0.035, eye, eye),
            prisms(0, -0.85, 0.32, 0.84, 0.26, skin, belly),
            prisms(0, -0.15, 0.28, 0.86, 0.32, skin, belly),
            prisms(0, -0.20, 0.20, 0.42, 0.22, belly, belly),
            prisms(0, 0.50, 0.34, 0.80, 0.22, skin, mark),
            prisms(0, 0.95 + tail * 0.4, 0.40, 0.72, 0.12, skin, mark),
            prisms((-0.42, 0.42), (1.28 + tail, 1.28 + tail), 0.52, 0.64, 0.10, mark, skin),
            prisms(0, 1.42 + tail, 0.50, 0.66, 0.08, mark, skin),
            prisms((-0.55, 0.55), (-0.15, -0.15), 0.40 + flap, 0.50 + flap, 0.16, mark, skin),
            prisms((-0.78, 0.78), (0.05, 0.05), 0.38 + flap, 0.46 + flap, 0.10, mark, skin),
            prisms(0, -0.10, 0.84, 0.98, 0.06, mark, mark),
        )
    if kind == 'fairy':
        flutter = math.sin(t * 18.0) * 0.06
        glow = np.array([1.0, 0.86, 0.55]) * tint
        wing = np.array([0.85, 0.95, 1.0]) * tint
        core = np.array([1.0, 0.95, 0.80])
        return cat(
            prisms(0, 0, 0.04, 0.22, 0.07, glow, core, 0.6),
            prisms(0, 0, 0.10, 0.18, 0.04, core, core, 1.0),
            prisms((-0.16, 0.16), (0.0, 0.0), 0.10 + flutter, 0.20 + flutter, 0.05, wing, wing, 0.35),
        )
    return prisms(0, 0, 0, 0.5, 0.3, (1, 0, 1), (1, 0, 1))


def set_sky(v, sky):
    """Re-light a model for how open the sky is where it stands (0-1)."""
    out = v.copy()
    a = out['c'][:, 3].astype(np.int32)
    out['c'][:, 3] = (a // 16) * 16 + int(round(max(0.0, min(1.0, sky)) * 15))
    return out


# Cached figure poses. Rebuilding prism meshes every frame for the lesson-island
# guides was the tutorial-world frame hog (~8 NPCs × 8 prisms, several ms each).
_FIGURE_CACHE = {}


def _pose_key(t, period, n=20):
    return int(round((t / period) * n)) % n


def guide(color, t=0.0):
    """A friendly lesson-island person: feet at y=0, about a block and a half tall."""
    ckey = tuple(np.round(np.asarray(color, dtype=np.float64), 4))
    pose = _pose_key(t, 2.0 * math.pi / 2.2, 24)
    key = ('guide', ckey, pose)
    v = _FIGURE_CACHE.get(key)
    if v is not None:
        return v
    t = pose / 24.0 * (2.0 * math.pi / 2.2)
    c = np.array(color, dtype=np.float64)
    cloth = c * 0.92
    skin = np.array([0.90, 0.74, 0.62])
    hair = c * 0.55 + np.array([0.15, 0.10, 0.12])
    bob = math.sin(t * 2.2) * 0.015
    v = cat(
        prisms((-0.09, 0.09), (0.02, 0.02), 0.0, 0.42, 0.07, cloth * 0.8, cloth * 0.8),
        prisms(0, 0.02, 0.40, 1.05 + bob, 0.22, cloth, cloth * 0.9),
        prisms(0, 0.00, 1.05 + bob, 1.32 + bob, 0.16, skin, skin * 0.92),
        prisms(0, 0.08, 1.24 + bob, 1.42 + bob, 0.17, hair, hair),
        prisms((-0.065, 0.065), (-0.145, -0.145), 1.18 + bob, 1.25 + bob, 0.042, (0.95, 0.93, 0.90), (0.95, 0.93, 0.90)),
        prisms((-0.065, 0.065), (-0.16, -0.16), 1.19 + bob, 1.24 + bob, 0.022, (0.10, 0.08, 0.08), (0.10, 0.08, 0.08)),
        prisms(0, -0.16, 1.10 + bob, 1.135 + bob, 0.03, (0.55, 0.32, 0.30), (0.55, 0.32, 0.30)),
        prisms((-0.28, 0.28), (0.02, 0.02), 0.70 + bob, 1.00 + bob, 0.06, cloth, cloth * 0.9),
    )
    _FIGURE_CACHE[key] = v
    return v


def wanderer(t=0.0, walking=False):
    """Plain unclothed base figure. Clothing and gear appear only once equipped."""
    bob_p = _pose_key(t, 2.0 * math.pi / 2.2, 20)
    swing_p = _pose_key(t, 2.0 * math.pi / 8.0, 16) if walking else 0
    key = ('wanderer', bool(walking), bob_p, swing_p)
    v = _FIGURE_CACHE.get(key)
    if v is not None:
        return v
    t_bob = bob_p / 20.0 * (2.0 * math.pi / 2.2)
    t_sw = swing_p / 16.0 * (2.0 * math.pi / 8.0)
    skin = np.array([0.90, 0.74, 0.62])
    hair = np.array([0.28, 0.20, 0.18])
    bob = math.sin(t_bob * 2.2) * 0.015
    swing = math.sin(t_sw * 8.0) * 0.12 if walking else 0.0
    # uniform body tone, no outfit colours or bands; face looks toward -z, back is +z
    v = cat(
        prisms((-0.09, 0.09), (0.02 + swing * 0.15, 0.02 - swing * 0.15), 0.0, 0.48, 0.07, skin, skin * 0.96),
        prisms(0, 0.02, 0.44, 1.10 + bob, 0.22, skin, skin * 0.96),
        prisms(0, 0.00, 1.10 + bob, 1.36 + bob, 0.16, skin, skin * 0.92),
        prisms(0, 0.08, 1.26 + bob, 1.46 + bob, 0.17, hair, hair),
        prisms((-0.065, 0.065), (-0.145, -0.145), 1.235 + bob, 1.305 + bob, 0.042, (0.95, 0.93, 0.90), (0.95, 0.93, 0.90)),
        prisms((-0.065, 0.065), (-0.16, -0.16), 1.245 + bob, 1.295 + bob, 0.022, (0.10, 0.08, 0.08), (0.10, 0.08, 0.08)),
        prisms(0, -0.16, 1.155 + bob, 1.19 + bob, 0.03, (0.55, 0.32, 0.30), (0.55, 0.32, 0.30)),
        prisms((-0.30, 0.30), (0.02 + swing, 0.02 - swing), 0.72 + bob, 1.05 + bob, 0.06, skin, skin * 0.96),
        # two simple cartoony rounded cheeks on the back of the hips, a slight bulge
        prisms((-0.09, 0.09), (0.16, 0.16), 0.42 + bob, 0.62 + bob, 0.085, skin, skin * 0.96),
    )
    _FIGURE_CACHE[key] = v
    return v
