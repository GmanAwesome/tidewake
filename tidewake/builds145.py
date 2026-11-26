"""1.4.4 follow-on wonders: rare, unmistakable landmarks that still fit in one chunk.

Registered as family 'wonder' with min_version=5 so older skies never gain them.
"""
from .config import LAYERS, CLOUD_SEA
from .hexgrid import DIRS, hex_distance
from . import materials as MT
from . import structures as ST
from . import builds144 as B

M = MT.ID
INTACT, ABANDONED, RUINED, OVERGROWN = ST.INTACT, ST.ABANDONED, ST.RUINED, ST.OVERGROWN
LOOT_TEMPLE, LOOT_STORE, LOOT_CAMP, LOOT_SKY = ST.LOOT_TEMPLE, ST.LOOT_STORE, ST.LOOT_CAMP, 7


def _reg(*a, **k):
    k.setdefault('min_version', 5)
    return ST.register(*a, **k)


def _pal(st):
    return B._pal(st)


def _clear(st, q, r, y, rad):
    y = B._clear_pad(st, q, r, y, rad)
    return y


@_reg('wonder', 'whale_skeleton', surface=True, aerial=True, sky=True,
      min_thickness=4, max_slope=6, pad=6, rarity=0.6)
def build_whale_skeleton(st, q, r, y):
    """A sky-whale's bones: skull, arched ribcage, spine and a forked fluke."""
    pal = _pal(st)
    y = _clear(st, q, r, y, 6)
    if y is None:
        return
    bone = M['ivory_plaster']
    rib = M['pearl_terrazzo'] if 'pearl_terrazzo' in M else M['pale_stone']
    dark = M['ink_bricks'] if 'ink_bricks' in M else M['basalt']
    cloud = M['shimmer_cloud']
    # thin darker cloud isle under the mid-body only — not a slab that hides the bones
    for dq in range(-4, 5):
        for dr in range(-2, 3):
            if hex_distance(0, 0, dq, dr) <= 4:
                st.put(q + dq, r + dr, y, cloud, force=True)
                st.put(q + dq, r + dr, y - 1, cloud, force=True)
    # spine along +q: 17 vertebrae, arched like a whale's back
    n = 17
    spine = [(q + k - 8, r) for k in range(n)]
    def back_h(i):
        t = i / (n - 1)
        return 3 + int(round(6 * (1 - abs(2 * t - 1) ** 1.15)))
    for i, (aq, ar) in enumerate(spine):
        h = back_h(i)
        st.column(aq, ar, y + 1, h, bone)
        if 3 <= i <= n - 4:
            st.put(aq, ar, y + h + 1, bone, force=True)
    # skull, snout and jaw, with dark eye sockets
    fq, fr = spine[0]
    st.disk(fq, fr, y + 5, 1, bone, force=True)
    st.put(fq, fr, y + 6, bone, force=True)
    st.put(fq - 1, fr, y + 5, bone, force=True)
    st.put(fq - 2, fr, y + 4, bone, force=True)
    st.put(fq - 3, fr, y + 3, bone, force=True)          # snout tip
    st.put(fq - 3, fr, y + 2, bone, force=True)
    st.put(fq - 2, fr, y + 1, bone, force=True)          # lower jaw
    st.put(fq - 1, fr, y + 1, bone, force=True)
    st.put(fq, fr, y + 2, bone, force=True)
    for d in (1, 5):
        dq, dr = DIRS[d]
        st.put(fq + dq, fr + dr, y + 6, dark, force=True)
        st.put(fq + dq, fr + dr, y + 5, dark, force=True)
    # ribcage: six pairs of arches curving out and down
    for i in (4, 6, 7, 8, 10, 12):
        aq, ar = spine[i]
        mid = back_h(i)
        for d in (1, 5):
            dq, dr = DIRS[d]
            st.put(aq + dq, ar + dr, y + mid + 2, rib, force=True)
            st.put(aq + dq * 2, ar + dr * 2, y + mid + 1, rib, force=True)
            st.put(aq + dq * 3, ar + dr * 3, y + max(3, mid - 1), rib, force=True)
            st.put(aq + dq * 4, ar + dr * 4, y + max(2, mid - 3), rib, force=True)
            st.put(aq + dq * 4, ar + dr * 4, y + 1, rib, force=True)
    # pectoral fins just behind the skull
    hq, hr = spine[3]
    for s in (1, -1):
        st.put(hq, hr + 2 * s, y + 3, bone, force=True)
        st.put(hq, hr + 3 * s, y + 2, bone, force=True)
        st.put(hq + 1, hr + 3 * s, y + 2, bone, force=True)
    # broad forked fluke
    tq, tr = spine[-1]
    st.put(tq, tr, y + 4, bone, force=True)
    st.put(tq + 1, tr, y + 3, bone, force=True)
    for dr, dy in ((1, 4), (2, 3), (3, 3), (4, 2), (-1, 4), (-2, 3), (-3, 3), (-4, 2)):
        st.put(tq, tr + dr, y + dy, bone, force=True)
    st.chest(q, r, y + 1, LOOT_SKY)
    st.put(q, r + 1, y + 1, pal['banner'], force=True)



@_reg('wonder', 'clockwork_tower', surface=True, min_thickness=6, max_slope=3, pad=4)
def build_clockwork_tower(st, q, r, y):
    """A tall brass-and-iron tower with cog rings and a clock face."""
    pal = _pal(st)
    y = _clear(st, q, r, y, 3)
    if y is None:
        return
    brass, iron, pew = M['brass'], M['wrought_iron'], M['pewter']
    h = 16
    for i in range(h):
        ring = brass if (i % 5) < 3 else iron
        st.ring(q, r, y + 1 + i, 2, ring, 1)
        st.put(q, r, y + 1 + i, 0, force=True)
        if i % 5 == 4:
            # a cog: fat ring of pewter teeth
            st.ring(q, r, y + 1 + i, 3, pew, 1)
    st.put(q, r, y + 1, M['ladder'], 0, force=True)
    for i in range(1, h):
        st.put(q, r, y + 1 + i, M['ladder'], 0, force=True)
    st.disk(q, r, y + h + 1, 2, pew, force=True)
    # clock face on +q
    st.put(q + 2, r, y + h - 2, M['snow_patterned_tile'] if 'snow_patterned_tile' in M else pew, force=True)
    st.put(q + 2, r, y + h - 1, pal['stain'], force=True)
    st.put(q, r, y + h + 2, pal['clamp'], force=True)
    st.door(q + 2, r, y + 1, 0)
    st.chest(q - 1, r, y + 1, LOOT_STORE)
    st.put(q + 1, r - 1, y + h + 2, pal['banner'], force=True)


@_reg('wonder', 'upside_castle', surface=False, aerial=True, sky=True,
      min_thickness=4, max_slope=6, pad=6)
def build_upside_castle(st, q, r, y):
    """A keep hanging from a cloud isle: towers point down, roofs sit at the bottom."""
    pal = _pal(st)
    if y is None:
        return
    # lift the cloud pad so the inverted roofs hang in open air above the ground
    hang = 18
    top = min(y + hang + 2, LAYERS - 8)
    plaster, stain, tile = pal['plaster'], pal['stain'], pal['tile2']
    brick, metal = pal['brick'], pal['metal']
    # the "ground" of the inverted isle is the underside of a cloud — no turf roof
    B._supported_platform(st, q, r, top, 7, M['shimmer_cloud'], M['shimmer_cloud'])
    st.disk(q, r, top, 7, M['shimmer_cloud'], force=True)
    for dq, dr in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (2, -1), (-2, 1), (3, 0), (-3, 0)):
        st.column(q + dq, r + dr, top - 2, 2, M['shimmer_cloud'])
    def _roof_down(aq, ar, y_tip, rad, mat):
        """A pointed roof whose tip is at y_tip and whose eaves are above it (inverted)."""
        for k in range(rad + 1):
            st.disk(aq, ar, y_tip + k, k, mat, force=True)

    # hanging keep: walls grow downward
    for i in range(1, 12):
        rad = 4 if i < 8 else 3
        mat = plaster if i % 2 == 0 else brick
        st.ring(q, r, top - i, rad, mat, 1)
        if i in (3, 6, 9):
            for d in range(6):
                dq, dr = DIRS[d]
                st.put(q + dq * rad, r + dr * rad, top - i, stain, force=True)
        for dq in range(-3, 4):
            for dr in range(max(-3, -dq - 3), min(3, -dq + 3) + 1):
                if hex_distance(0, 0, dq, dr) < rad:
                    if not (dq == 0 and dr == 0 and i == 11):
                        st.put(q + dq, r + dr, top - i, 0, force=True)
    st.disk(q, r, top - 11, 2, tile, force=True)
    st.chest(q, r, top - 10, LOOT_TEMPLE)
    st.put(q, r, top - 12, pal['banner'], force=True)
    # four corner towers pointing DOWN, with pointed roofs at their lowest tips
    for dq, dr in ((5, 0), (-5, 0), (0, 5), (0, -5)):
        for i in range(0, 12):
            st.ring(q + dq, r + dr, top - 4 - i, 1, brick if i < 8 else metal, 1)
            st.put(q + dq, r + dr, top - 4 - i, 0, force=True)
        _roof_down(q + dq, r + dr, top - 16, 2, tile)
        st.put(q + dq, r + dr, top - 16, pal['clamp'], force=True)
    # central inverted spire at the bottom of the keep
    _roof_down(q, r, top - 15, 3, tile)
    st.put(q, r, top - 15, pal['clamp'], force=True)



@_reg('wonder', 'ring_harbor', surface=True, aerial=True, min_thickness=5, max_slope=4, pad=6)
def build_ring_harbor(st, q, r, y):
    """A ring-shaped harbor: a deep basin, piers, docks, lamps and a few boats."""
    pal = _pal(st)
    y = _clear(st, q, r, y, 6)
    if y is None:
        return
    plank = pal['planks']
    pale = M['pale_planks'] if 'pale_planks' in M else plank
    post, lamp = pal['log'], pal['clamp']
    # deep, wide basin
    for dq in range(-6, 7):
        for dr in range(max(-6, -dq - 6), min(6, -dq + 6) + 1):
            d = hex_distance(0, 0, dq, dr)
            if d <= 6:
                st.put(q + dq, r + dr, y, 0, force=True)
                st.put(q + dq, r + dr, y - 1, M['water'], 7, force=True)
                st.put(q + dq, r + dr, y - 2, M['water'], 7, force=True)
                st.put(q + dq, r + dr, y - 3, M['water'], 7, force=True)
                if d <= 3:
                    st.put(q + dq, r + dr, y - 4, M['water'], 6, force=True)
    # dock rings and an outer quay
    st.ring(q, r, y, 7, plank, 1)
    st.ring(q, r, y, 8, plank, 1)
    st.ring(q, r, y, 9, pal['terra'], 1)
    # piers reaching into the basin, with posts and lamps
    for d, (dq, dr) in enumerate(DIRS):
        for k in (6, 5, 4):
            st.put(q + dq * k, r + dr * k, y, plank, force=True)
        st.put(q + dq * 8, r + dr * 8, y + 1, post, force=True)
        st.put(q + dq * 8, r + dr * 8, y + 2, lamp, force=True)
        if d % 2 == 0:
            st.put(q + dq * 9, r + dr * 9, y + 1, pal['banner'], force=True)
    # a dock warehouse on the +q quay
    for dq, dr in ((9, 0), (9, 1), (9, -1), (10, 0), (10, 1), (10, -1), (11, 0)):
        st.put(q + dq, r + dr, y, pal['terra'], force=True)
        st.column(q + dq, r + dr, y + 1, 3, pal['plaster'])
    st.disk(q + 10, r, y + 4, 2, pal['woven'] if 'woven' in pal else plank, force=True)
    st.door(q + 8, r, y + 1, 3)
    st.chest(q + 10, r, y + 1, LOOT_CAMP)
    st.chest(q - 8, r, y + 1, LOOT_SKY)
    # three boats in the basin: a pointed hull, mast and sail
    def _boat(aq, ar, facing, hull):
        fdq, fdr = DIRS[facing]
        sdq, sdr = DIRS[(facing + 1) % 6]
        for k in range(-2, 3):
            st.put(aq + fdq * k, ar + fdr * k, y, hull, force=True)
        st.put(aq + fdq * 2 + sdq, ar + fdr * 2 + sdr, y, hull, force=True)  # prow flare
        st.put(aq, ar, y + 1, post, force=True)
        st.put(aq, ar, y + 2, post, force=True)
        st.put(aq, ar, y + 3, pal['banner'], force=True)
        # a short sail
        st.put(aq + sdq, ar + sdr, y + 2, pal['woven'] if 'woven' in pal else pal['banner'], force=True)
    _boat(q + 2, r - 2, 0, pale)
    _boat(q - 2, r + 3, 2, plank)
    _boat(q + 3, r + 2, 4, pale)



@_reg('wonder', 'crystal_cathedral', surface=True, min_thickness=6, max_slope=2, pad=6)
def build_crystal_cathedral(st, q, r, y):
    """A tall nave with a stained-glass window wall and a crystal spire."""
    pal = _pal(st)
    y = _clear(st, q, r, y, 6)
    if y is None:
        return
    tile, stain, plaster = pal['tile2'], pal['stain'], pal['plaster']
    lamp = pal['clamp']
    # floor along a long nave (+q) with a short transept
    for dq in range(-4, 6):
        for dr in range(-3, 4):
            if abs(dr) <= 2 or (-1 <= dq <= 2):
                st.put(q + dq, r + dr, y, tile, force=True)
                st.clear_above(q + dq, r + dr, y + 1)
    def _hollow(aq, ar, y0, h, rad):
        for i in range(h):
            st.ring(aq, ar, y0 + i, rad, plaster if i % 3 != 1 else stain, 1)
            for ddq in range(-rad + 1, rad):
                for ddr in range(-rad + 1, rad):
                    if hex_distance(0, 0, ddq, ddr) < rad:
                        st.put(aq + ddq, ar + ddr, y0 + i, 0, force=True)
    # nave: 14 high, rad 3, stretched by also building a second ring toward the facade
    _hollow(q, r, y + 1, 14, 3)
    _hollow(q + 2, r, y + 1, 12, 3)
    # facade window wall at +q (tall stained glass, a rose window near the top)
    for i in range(14):
        for dr in (-2, -1, 0, 1, 2):
            mat = stain if not (i in (0, 13) or abs(dr) == 2 and i < 2) else plaster
            st.put(q + 5, r + dr, y + 1 + i, mat, force=True)
    st.disk(q + 5, r, y + 11, 1, stain, force=True)
    # stepped nave roof in tile/plaster, never turf
    st.disk(q + 1, r, y + 15, 3, plaster, force=True)
    st.disk(q + 1, r, y + 16, 2, tile, force=True)
    # crossing spire
    for i in range(17, 24):
        st.ring(q, r, y + i, 1, plaster if i % 2 == 0 else stain, 1)
        st.put(q, r, y + i, 0, force=True)
    st.put(q, r, y + 24, lamp, force=True)
    st.put(q, r, y + 25, M['cosmic_star'] if 'cosmic_star' in M else lamp, force=True)
    # side buttresses
    for dr in (-3, 3):
        for i in range(1, 9):
            st.put(q, r + dr, y + i, plaster, force=True)
        st.put(q, r + dr, y + 9, tile, force=True)
    # door at the facade, Tidewell and chest inside
    st.door(q + 5, r, y + 1, 0)
    st.put(q, r, y + 1, M['tidewell'], force=True)
    st.put(q, r + 1, y + 1, lamp, force=True)
    st.put(q, r - 1, y + 1, lamp, force=True)
    st.chest(q - 2, r, y + 1, LOOT_TEMPLE)
    st.put(q - 2, r + 1, y + 1, pal['banner'], force=True)


@_reg('wonder', 'waterfall_temple', surface=True, aerial=True, min_thickness=8, max_slope=5, pad=6)
def build_waterfall_temple(st, q, r, y, edge_dir=0):
    """A plaster temple on a high cliff, with a wide cascade falling into a basin."""
    pal = _pal(st)
    y = _clear(st, q, r, y, 6)
    if y is None:
        return
    d = edge_dir if isinstance(edge_dir, int) else 0
    dq, dr = DIRS[d % 6]
    sdq, sdr = DIRS[(d + 1) % 6]
    stone = pal.get('stone', M['stone'])
    tile, plaster = pal['tile2'], pal['plaster']
    rise = 14
    # raised stone cliff so the fall hangs in open air above the terrace
    for a in range(-5, 2):
        for b in range(-4, 5):
            aq, ar = q + a * dq + b * sdq, r + a * dr + b * sdr
            st.column(aq, ar, y, rise, stone)
            top_mat = pal['terra'] if a <= 0 and abs(b) <= 3 else stone
            st.put(aq, ar, y + rise, top_mat, force=True)
            st.clear_above(aq, ar, y + rise + 1)
    lip_y = y + rise
    # taller temple on the mesa, set back from the lip
    tq, tr = q - 2 * dq, r - 2 * dr
    st.disk(tq, tr, lip_y, 3, tile, force=True)
    for i in range(1, 5):
        st.ring(tq, tr, lip_y + i, 3, plaster if i != 3 else pal['stain'], 1)
        for ddq in range(-2, 3):
            for ddr in range(-2, 3):
                if hex_distance(0, 0, ddq, ddr) < 3:
                    st.put(tq + ddq, tr + ddr, lip_y + i, 0, force=True)
    st.disk(tq, tr, lip_y + 5, 3, tile, force=True)
    st.disk(tq, tr, lip_y + 6, 2, tile, force=True)
    st.put(tq, tr, lip_y + 1, pal['clamp'], force=True)
    st.put(tq, tr, lip_y + 7, pal['banner'], force=True)
    st.chest(tq - dq, tr - dr, lip_y + 1, LOOT_TEMPLE)
    st.door(tq - 2 * dq, tr - 2 * dr, lip_y + 1, (d + 3) % 6)
    # source pool at the lip
    for a in (0, 1):
        for b in range(-2, 3):
            aq, ar = q + a * dq + b * sdq, r + a * dr + b * sdr
            st.put(aq, ar, lip_y, M['water'], 7, force=True)
            if a == 1:
                st.put(aq, ar, lip_y - 1, M['water'], 7, force=True)
    # cascade in open air down the cliff face
    for k in range(0, rise + 1):
        for b in range(-2, 3):
            st.put(q + 2 * dq + b * sdq, r + 2 * dr + b * sdr, lip_y - k, M['water'], 7, force=True)
            if abs(b) <= 1:
                st.put(q + 3 * dq + b * sdq, r + 3 * dr + b * sdr, lip_y - k, M['water'], 6, force=True)
    # stone banks framing the fall
    for k in range(0, rise):
        for b in (-3, 3):
            st.put(q + 2 * dq + b * sdq, r + 2 * dr + b * sdr, lip_y - k, stone, force=True)
    # splash basin at the foot of the cliff
    for a in range(2, 8):
        for b in range(-4, 5):
            aq, ar = q + a * dq + b * sdq, r + a * dr + b * sdr
            st.put(aq, ar, y, stone, force=True)
            if abs(b) <= 3 and a <= 6:
                st.put(aq, ar, y + 1, M['water'], 7, force=True)
                if abs(b) <= 2 and 3 <= a <= 5:
                    st.put(aq, ar, y + 2, M['water'], 6, force=True)
