"""1.4.4 landscape and sky structures. Registered with min_version=5 so 1.4 / 1.4.1
skies keep the structures they already have. v3/v4 skies stay empty of them too.
"""
import random

from .config import CHUNK, LAYERS, CLOUD_SEA
from .hexgrid import DIRS, hex_distance
from . import materials as MT
from . import structures as ST

M = MT.ID
INTACT, ABANDONED, RUINED, OVERGROWN = ST.INTACT, ST.ABANDONED, ST.RUINED, ST.OVERGROWN
LOOT_CAMP, LOOT_STORE, LOOT_TEMPLE = ST.LOOT_CAMP, ST.LOOT_STORE, ST.LOOT_TEMPLE
LOOT_CHAMBER, LOOT_STONES, LOOT_BOAT = ST.LOOT_CHAMBER, ST.LOOT_STONES, ST.LOOT_BOAT
LOOT_SKY = 7


def _reg(*a, **k):
    k.setdefault('min_version', 5)
    return ST.register(*a, **k)


def _dye_mat(stem, realm, rng):
    """A dyed decorative block that suits this landscape."""
    keys = ('snow', 'pearl', 'ash', 'ink', 'rose', 'ember', 'honey', 'leaf',
            'moss', 'tide', 'sky', 'indigo', 'violet', 'orchid', 'blush', 'cocoa')
    by_realm = {
        0: ('leaf', 'honey', 'blush'), 1: ('ember', 'honey', 'cocoa'),
        2: ('rose', 'blush', 'orchid'), 3: ('snow', 'sky', 'pearl'),
        4: ('ash', 'ink', 'tide'), 5: ('moss', 'leaf', 'tide'),
        6: ('honey', 'ember', 'cocoa'), 7: ('violet', 'orchid', 'indigo'),
        8: ('pearl', 'honey', 'ash'), 9: ('moss', 'cocoa', 'leaf'),
        10: ('orchid', 'violet', 'blush'), 11: ('ember', 'ink', 'cocoa'),
        12: ('pearl', 'snow', 'ash'), 13: ('indigo', 'violet', 'ink'),
        14: ('sky', 'snow', 'pearl'), 15: ('tide', 'moss', 'leaf'),
    }
    choice = rng.choice(by_realm.get(int(realm) % 16, keys))
    from . import palette as PAL
    return M[PAL.id_key(PAL.dyed_name(stem, choice))]


def _pal(st):
    pal = dict(st.pal)
    rng = st.rng
    rm = 0
    try:
        # a representative realm from the site
        if st.realm is not None and hasattr(st.realm, 'shape'):
            rm = int(st.realm[CHUNK // 2, CHUNK // 2])
    except Exception:
        rm = 0
    pal['plaster'] = rng.choice([M['ivory_plaster'], M['blush_plaster'], M['sage_plaster'], M['dusk_plaster']])
    pal['metal'] = rng.choice([M['pewter'], M['brass'], M['copper'], M['wrought_iron']])
    pal['stain'] = _dye_mat('Stained Glass', rm, rng)
    pal['tile2'] = _dye_mat('Patterned Tile', rm, rng)
    pal['terra'] = _dye_mat('Terrazzo', rm, rng)
    pal['woven'] = _dye_mat('Woven Panel', rm, rng)
    pal['banner'] = _dye_mat('Banner', rm, rng)
    pal['clamp'] = _dye_mat('Crystal Lamp', rm, rng)
    pal['lattice'] = M['pale_lattice'] if rm in (3, 8, 12, 14) else M['wood_lattice']
    return pal


def _clear_pad(st, q, r, y, rad):
    y = st.flatten(q, r, rad, y)
    return y


def _supported_platform(st, q, r, y, rad, mat, stem=None):
    """A complete floating pad with a short stem, so corners are not hanging in air."""
    stem = stem or M['shimmer_cloud']
    for dq in range(-rad, rad + 1):
        for dr in range(max(-rad, -dq - rad), min(rad, -dq + rad) + 1):
            st.column(q + dq, r + dr, y - 2, 2, stem)
            st.put(q + dq, r + dr, y, mat, force=True)
            st.clear_above(q + dq, r + dr, y + 1)
    return y


# ---------------------------------------------------------------------------
# island
# ---------------------------------------------------------------------------
@_reg('settlement', 'hamlet', surface=True, min_thickness=6, max_slope=2, pad=6)
def build_hamlet(st, q, r, y, door_dir=0):
    pal = _pal(st)
    y = _clear_pad(st, q, r, y, 6)
    if y is None:
        return
    st.disk(q, r, y, 6, pal['terra'], force=True)
    ST._house_walls(st, q - 3, r, y, 2, 3, door_dir)
    ST._house_walls(st, q + 3, r - 1, y, 2, 3, (door_dir + 2) % 6)
    st.put(q, r, y, pal['tile2'], force=True)
    st.lamp(q, r, y + 1)
    st.put(q, r + 2, y + 1, pal['banner'], force=True)
    st.chest(q - 3, r, y + 1, LOOT_STORE, door_dir)
    st.chest(q + 3, r - 1, y + 1, LOOT_CAMP, door_dir)
    if st.cond == INTACT:
        st.put(q + 1, r - 2, y + 1, M['tinker_bench'], force=True)


@_reg('settlement', 'watchtower', surface=True, min_thickness=6, max_slope=3, pad=4)
def build_watchtower(st, q, r, y):
    pal = _pal(st)
    y = _clear_pad(st, q, r, y, 3)
    if y is None:
        return
    h = 8 + st.rng.randrange(4)
    ST._house_walls = ST._house_walls  # keep
    for i in range(h):
        st.ring(q, r, y + 1 + i, 2, pal['brick'] if i < h - 2 else pal['metal'], 1)
        st.put(q, r, y + 1 + i, 0, force=True)
    st.put(q, r, y, pal['terra'], force=True)
    st.put(q, r, y + 1, M['ladder'], 0, force=True)
    for i in range(1, h):
        st.put(q, r, y + 1 + i, M['ladder'], 0, force=True)
    st.disk(q, r, y + h + 1, 2, pal['metal'], force=True)
    st.lamp(q, r, y + h + 2)
    st.put(q + 1, r, y + h + 2, pal['banner'], force=True)
    st.chest(q - 1, r, y + 1, LOOT_CAMP)


@_reg('settlement', 'shrine', surface=True, min_thickness=5, max_slope=3, pad=4)
def build_shrine(st, q, r, y):
    pal = _pal(st)
    y = _clear_pad(st, q, r, y, 4)
    if y is None:
        return
    st.disk(q, r, y, 3, pal['terra'], force=True)
    st.ring(q, r, y + 1, 3, pal['plaster'], 2)
    # open four doorways
    for dq, dr in DIRS[::2]:
        st.put(q + dq * 3, r + dr * 3, y + 1, 0, force=True)
        st.put(q + dq * 3, r + dr * 3, y + 2, pal['stain'], force=True)
    st.disk(q, r, y + 3, 3, pal['tile2'])
    st.put(q, r, y + 1, pal['clamp'], force=True)
    st.chest(q, r + 1, y + 1, LOOT_TEMPLE)
    st.put(q, r - 1, y + 1, pal['banner'], force=True)


@_reg('settlement', 'windmill', surface=True, min_thickness=6, max_slope=2, pad=5)
def build_windmill(st, q, r, y):
    pal = _pal(st)
    y = _clear_pad(st, q, r, y, 4)
    if y is None:
        return
    h = 7
    for i in range(h):
        st.ring(q, r, y + 1 + i, 2, pal['planks'] if i < 2 else pal['plaster'], 1)
        st.put(q, r, y + 1 + i, 0, force=True)
    st.disk(q, r, y + h + 1, 2, pal['woven'])
    st.door(q + 2, r, y + 1, 0)
    # four sails
    arms = ((3, 0), (-3, 0), (0, 3), (0, -3), (2, 2), (-2, -2))
    for dq, dr in arms:
        for k in range(1, 4):
            st.put(q + dq * k // 2, r + dr * k // 2, y + h, pal['woven'], force=True)
            st.put(q + dq * k // 2, r + dr * k // 2, y + h + 1, pal['woven'], force=True)
    st.chest(q, r, y + 1, LOOT_STORE)
    st.lamp(q, r, y + h - 1)


@_reg('aerial', 'lighthouse', surface=True, aerial=True, min_thickness=5, max_slope=6, pad=4)
def build_lighthouse(st, q, r, y, edge_dir=0):
    pal = _pal(st)
    y = _clear_pad(st, q, r, y, 3)
    if y is None:
        return
    h = 10
    stripe_a, stripe_b = M['ivory_plaster'], pal['brick']
    for i in range(h):
        mat = stripe_a if (i // 2) % 2 == 0 else stripe_b
        st.ring(q, r, y + 1 + i, 2, mat, 1)
        st.put(q, r, y + 1 + i, 0, force=True)
    st.disk(q, r, y + h + 1, 2, pal['metal'])
    st.put(q, r, y + h + 2, pal['clamp'], force=True)
    st.put(q, r, y + h + 3, M['cosmic_star'] if 'cosmic_star' in M else pal['clamp'], force=True)
    st.door(q + DIRS[edge_dir][0] * 2, r + DIRS[edge_dir][1] * 2, y + 1, edge_dir)
    st.chest(q, r, y + 1, LOOT_CAMP)
    st.put(q + 1, r - 1, y + h + 2, pal['banner'], force=True)


@_reg('settlement', 'market', surface=True, min_thickness=5, max_slope=2, pad=5)
def build_market(st, q, r, y):
    pal = _pal(st)
    y = _clear_pad(st, q, r, y, 5)
    if y is None:
        return
    st.disk(q, r, y, 5, pal['terra'], force=True)
    # three stalls
    spots = ((-3, 1), (2, 2), (1, -3))
    for i, (dq, dr) in enumerate(spots):
        st.disk(q + dq, r + dr, y, 1, pal['planks'], force=True)
        st.put(q + dq, r + dr, y + 1, pal['woven'], force=True)
        st.put(q + dq, r + dr, y + 2, pal['banner'], force=True)
        for a, b in ((1, 0), (0, 1), (-1, 0)):
            st.put(q + dq + a, r + dr + b, y + 2, pal['banner'], force=True)
        st.chest(q + dq, r + dr, y + 1, LOOT_STORE if i else LOOT_CAMP)
    st.lamp(q, r, y + 1)
    st.put(q, r, y, pal['tile2'], force=True)


@_reg('settlement', 'garden', surface=True, min_thickness=4, max_slope=2, pad=5)
def build_garden(st, q, r, y):
    pal = _pal(st)
    y = _clear_pad(st, q, r, y, 5)
    if y is None:
        return
    st.ring(q, r, y, 5, pal['plaster'], 1)
    st.disk(q, r, y, 4, M['turf'], force=True)
    st.path(q - 3, r, q + 3, r, pal['terra'])
    st.path(q, r - 3, q, r + 3, pal['terra'])
    # fountain
    st.disk(q, r, y, 1, pal['stone'], force=True)
    st.put(q, r, y + 1, pal['plaster'], force=True)
    st.put(q, r, y, M['water'], 7, force=True)
    flowers = [M['bloom'], M['petals'], M['wildflower'], M['heather'], pal['banner']]
    for _ in range(10):
        dq, dr = st.rng.randint(-4, 4), st.rng.randint(-4, 4)
        if hex_distance(0, 0, dq, dr) in (2, 3, 4) and st.ground(q + dq, r + dr):
            st.put(q + dq, r + dr, y + 1, st.rng.choice(flowers), force=True)
    st.lamp(q + 2, r + 2, y + 1)


@_reg('settlement', 'observatory', surface=True, min_thickness=6, max_slope=2, pad=5)
def build_observatory(st, q, r, y):
    pal = _pal(st)
    y = _clear_pad(st, q, r, y, 4)
    if y is None:
        return
    for i in range(4):
        st.ring(q, r, y + 1 + i, 3, pal['stone'] if i < 2 else pal['metal'], 1)
        st.put(q, r, y + 1 + i, 0, force=True)
    # glass dome
    st.disk(q, r, y + 5, 3, pal['stain'])
    st.disk(q, r, y + 6, 2, pal['stain'])
    st.disk(q, r, y + 7, 1, pal['stain'])
    st.put(q, r, y + 8, M['cosmic_star'], force=True)
    st.door(q + 3, r, y + 1, 0)
    st.chest(q, r, y + 1, LOOT_TEMPLE)
    st.lamp(q, r, y + 4)


@_reg('ruin', 'ruin_tower', surface=True, min_thickness=6, max_slope=3, pad=4)
def build_ruin_tower(st, q, r, y):
    pal = _pal(st)
    y = _clear_pad(st, q, r, y, 3)
    if y is None:
        return
    h = 6
    for i in range(h):
        st.ring(q, r, y + 1 + i, 2, pal['brick'], 1)
    st.debris(q, r, 4, 10)
    st.chest(q, r, y + 1, LOOT_CHAMBER)
    st.vines_on(q + 2, r, y + 1, h)


# ---------------------------------------------------------------------------
# bridges (placed specially)
# ---------------------------------------------------------------------------
def build_bridge(st, q0, r0, q1, r1, y0, y1):
    pal = _pal(st)
    cells = st.hex_line(q0, r0, q1, r1)
    if len(cells) < 3:
        return False
    for i, (q, r) in enumerate(cells):
        t = i / max(1, len(cells) - 1)
        y = int(round(y0 + (y1 - y0) * t))
        st.put(q, r, y, pal['planks'], force=True)
        # railings
        if 0 < i < len(cells) - 1:
            prev = cells[i - 1]
            dq, dr = q - prev[0], r - prev[1]
            # a perpendicular neighbour
            side = (-dr, dq + dr) if (dq, dr) else (1, 0)
            if hex_distance(0, 0, *side) == 0:
                side = (1, 0)
            st.put(q + side[0], r + side[1], y + 1, pal['lattice'], force=True)
        if i in (0, len(cells) - 1):
            st.fill_to(q, r, y, pal['stone'])
    return True


# ---------------------------------------------------------------------------
# sky
# ---------------------------------------------------------------------------
def _sky_pad(st, q, r, y, rad, floor):
    return _supported_platform(st, q, r, y, rad, floor, M['shimmer_cloud'])


@_reg('sky', 'sky_temple', surface=False, sky=True, pad=5, rarity=0.8)
def build_sky_temple(st, q, r, y):
    pal = _pal(st)
    y = _sky_pad(st, q, r, y, 4, pal['terra'])
    st.ring(q, r, y + 1, 4, pal['plaster'], 3)
    for dq, dr in DIRS[::2]:
        st.put(q + dq * 4, r + dr * 4, y + 1, 0, force=True)
        st.put(q + dq * 4, r + dr * 4, y + 2, pal['stain'], force=True)
        st.put(q + dq * 4, r + dr * 4, y + 3, pal['stain'], force=True)
    st.disk(q, r, y + 4, 4, pal['tile2'])
    st.disk(q, r, y + 5, 2, pal['stain'])
    st.put(q, r, y + 1, pal['clamp'], force=True)
    st.put(q, r, y + 6, M['cosmic_star'], force=True)
    st.chest(q, r + 1, y + 1, LOOT_TEMPLE)
    for dq, dr in DIRS:
        st.put(q + dq * 3, r + dr * 3, y + 4, pal['banner'], force=True)


@_reg('sky', 'airship_wreck', surface=False, sky=True, pad=4, rarity=0.9)
def build_airship_wreck(st, q, r, y):
    """A pointed wooden hull with a broken mast and a torn, striped envelope."""
    pal = _pal(st)
    hull = pal['planks']
    rib = M.get('wrought_iron', pal['metal'])
    stripe_a = M.get('rose_stripe', pal['banner'])
    stripe_b = M.get('sky_stripe', pal['woven'])
    y = _sky_pad(st, q, r, y, 1, hull)
    # Pointed hull along +q (bow) / -q (stern), 7 cells long
    for dq in range(-3, 4):
        rad = 0 if abs(dq) == 3 else (1 if abs(dq) == 2 else 2)
        if dq == 3:
            rad = 0  # sharp bow
        for dr in range(-rad, rad + 1):
            st.put(q + dq, r + dr, y, hull, force=True)
            st.put(q + dq, r + dr, y - 1, M['shimmer_cloud'], force=True)
            # gunwales
            if abs(dr) == rad and rad > 0:
                st.put(q + dq, r + dr, y + 1, hull, force=True)
    # stern castle
    st.put(q - 3, r, y + 1, hull, force=True)
    st.put(q - 3, r, y + 2, rib, force=True)
    # broken mast, snapped mid-air
    st.put(q, r, y + 1, pal.get('heartwood', M.get('heartwood', hull)), force=True)
    st.put(q, r, y + 2, pal.get('heartwood', M.get('heartwood', hull)), force=True)
    st.put(q, r, y + 3, pal.get('heartwood', M.get('heartwood', hull)), force=True)
    st.put(q + 1, r, y + 4, pal.get('heartwood', M.get('heartwood', hull)), force=True)
    # torn striped envelope hanging off the starboard side and mast
    for k, (dq, dr, yy, mat) in enumerate((
        (1, 1, y + 3, stripe_a), (1, 2, y + 3, stripe_b), (2, 2, y + 4, stripe_a),
        (2, 1, y + 4, stripe_b), (3, 1, y + 5, stripe_a), (1, 2, y + 5, stripe_b),
        (0, 2, y + 4, stripe_a), (2, 2, y + 3, stripe_b), (3, 0, y + 4, stripe_a),
        (1, 1, y + 5, stripe_b),
    )):
        st.put(q + dq, r + dr, yy, mat, force=True)
    st.put(q - 1, r + 1, y + 1, pal['banner'], force=True)
    st.put(q - 2, r, y + 1, pal['banner'], force=True)
    st.chest(q - 1, r, y + 1, LOOT_BOAT)
    st.lamp(q + 1, r, y + 2)
    if st.cond in (RUINED, ABANDONED, OVERGROWN):
        st.debris(q, r, 4, 6)


@_reg('sky', 'chain_fort', surface=False, sky=True, pad=5, rarity=0.7)
def build_chain_fort(st, q, r, y):
    pal = _pal(st)
    y = _sky_pad(st, q, r, y, 3, pal['brick'])
    for i in range(4):
        st.ring(q, r, y + 1 + i, 3, pal['brick'], 1)
    st.disk(q, r, y + 5, 3, pal['metal'])
    st.put(q, r, y + 1, M['ladder'], 0, force=True)
    for i in range(1, 5):
        st.put(q, r, y + 1 + i, M['ladder'], 0, force=True)
    st.chest(q, r, y + 1, LOOT_CHAMBER)
    st.put(q + 2, r, y + 6, pal['banner'], force=True)
    # hanging chain down into the open
    for k in range(1, 6):
        st.put(q + 3, r, y - k, M['wrought_iron'], force=True)
    # a second tiny pad at the chain end
    _supported_platform(st, q + 5, r + 1, y - 5, 2, pal['brick'], M['wrought_iron'])
    st.ring(q + 5, r + 1, y - 4, 2, pal['brick'], 2)
    st.chest(q + 5, r + 1, y - 4, LOOT_CAMP)


@_reg('sky', 'balloon_platform', surface=False, sky=True, pad=4, rarity=1.0)
def build_balloon(st, q, r, y):
    """A hanging basket under a round, candy-striped envelope — not a tree."""
    pal = _pal(st)
    stripe_a = M.get('rose_stripe', pal['banner'])
    stripe_b = M.get('honey_patterned_tile', pal['plaster'] if 'plaster' in pal else pal['planks'])
    # if honey tile missing, fall back through dye families
    if 'honey_patterned_tile' not in M:
        stripe_b = M.get('sky_stripe', pal['woven'])
    basket = pal['planks']
    y = _sky_pad(st, q, r, y, 2, basket)
    # basket floor + rails
    st.disk(q, r, y, 2, basket, force=True)
    st.ring(q, r, y + 1, 2, basket, 1)
    # ropes / stays up to the envelope
    rope = M.get('pale_lattice', pal['lattice'] if 'lattice' in pal else pal['planks'])
    for dq, dr in DIRS[::2]:
        st.put(q + dq, r + dr, y + 2, rope, force=True)
        st.put(q + dq, r + dr, y + 3, rope, force=True)
        st.put(q + dq, r + dr, y + 4, rope, force=True)
    # round candy-striped envelope (alternating rings, clearly a balloon)
    for rad, yy in ((2, y + 5), (3, y + 6), (3, y + 7), (3, y + 8), (2, y + 9), (1, y + 10)):
        mat = stripe_a if ((yy - y) % 2 == 0) else stripe_b
        st.disk(q, r, yy, rad, mat, force=True)
    st.put(q, r, y + 11, M.get('rose_banner', pal['banner']), force=True)
    st.chest(q, r, y + 1, LOOT_CAMP)
    st.lamp(q, r, y + 2)


@_reg('sky', 'crystal_pinnacle', surface=False, sky=True, pad=4, rarity=0.8)
def build_crystal_pinnacle(st, q, r, y):
    pal = _pal(st)
    y = _sky_pad(st, q, r, y, 3, M['starstone'] if 'starstone' in M else pal['stone'])
    for i, rad in enumerate((3, 2, 2, 1, 1, 0, 0)):
        st.disk(q, r, y + 1 + i, rad, pal['clamp'] if i % 2 else pal['stain'])
    st.put(q, r, y + 8, M['cosmic_star'], force=True)
    st.chest(q + 1, r, y + 1, LOOT_TEMPLE)
    for dq, dr in DIRS:
        st.put(q + dq * 2, r + dr * 2, y + 1, pal['clamp'], force=True)


@_reg('sky', 'lantern_cluster', surface=False, sky=True, pad=4, rarity=1.1)
def build_lantern_cluster(st, q, r, y):
    pal = _pal(st)
    y = _sky_pad(st, q, r, y, 2, M['shimmer_cloud'])
    st.put(q, r, y + 1, pal['clamp'], force=True)
    for dq, dr, dy in ((2, 0, 2), (-2, 1, 3), (1, -2, 1), (0, 2, 4), (-1, -1, 2)):
        st.put(q + dq, r + dr, y - 1, M['shimmer_cloud'], force=True)
        st.put(q + dq, r + dr, y, M['shimmer_cloud'], force=True)
        st.put(q + dq, r + dr, y + dy, pal['clamp'], force=True)
        st.put(q + dq, r + dr, y + dy + 1, pal['banner'], force=True)
    st.chest(q, r, y + 1, LOOT_STONES)


def fill_sky_loot(inv, seed, q, r, y):
    ST.fill_chest(inv, LOOT_TEMPLE, seed, q, r, y)
