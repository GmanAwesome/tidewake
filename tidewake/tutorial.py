"""A hand-built lesson island, launched from the title screen.

The grounds are a spread of themed stations around a starting plaza, with a
packed path and a plank bridge to the shrine knoll. A cheap distant citadel
(see landmark.py) sits on the -Z horizon as a teaser for the wider world.
The layout is pinned and deterministic.
"""
import numpy as np

from .config import CHUNK, LAYERS, LAYER
from .hexgrid import center, hex_distance, DIRS
from . import materials as MT
from . import items as I

M = MT.ID
SURF = 48
BOT = 42
# Bounding hex radius of the lesson grounds (plaza through shrine knoll).
RADIUS = 80
SPAWN = (0, 0, SURF)

# (q, r, name, colour, lines) — each guide stands in the open beside their station
NPCS = [
    (6, 2, 'Willow', (0.86, 0.72, 0.58),
     ('Welcome to the lesson island. That citadel on the horizon is still out of reach — for now. Walk with W A S D, look with the mouse, and jump with Space.',
      'Follow the tiled path and the signposts from the plaza. Talk to everyone. Press E for your backpack, J for the journal, P for the Path.')),
    (34, -8, 'Bram', (0.55, 0.62, 0.48),
     ('Hold left click on a tree to gather wood. Heartwood becomes planks at the bench.',
      'Stone needs a pick. Craft one from sticks and cobble once you have a Tinker Bench.')),
    (58, 8, 'Tess', (0.78, 0.58, 0.62),
     ('Press E. Turn Heartwood into Planks, then Planks into Sticks and a Tinker Bench.',
      'Right-click a placed bench for the full 3×3 grid. Click a recipe in the book to fill it.')),
    (60, 32, 'Cole', (0.70, 0.50, 0.40),
     ('Right-click the kiln. Fuel goes underneath, and what you cook or smelt goes on the left.',
      'There is Emberite and some hopmeat in the chest if you want to try it now.')),
    (38, 52, 'Mira', (0.62, 0.70, 0.78),
     ('Right-click to place a block. A door needs two empty cells, one above the other — then right-click to open it.',
      'Ladders hang on a wall. Walk into the rungs to climb. There are extras in the chest.')),
    (6, 54, 'Finn', (0.50, 0.68, 0.72),
     ('Take the fishing rod from the chest. Right-click the pool to cast, and wait.',
      'When the bobber dips, right-click again to reel. Pull too early and the fish gets away.')),
    (-26, 38, 'Sela', (0.62, 0.58, 0.40),
     ('A hoe tills turf or loam into a bed. Plant the seeds from the chest, then wait — they grow faster by a pool.',
      'When a crop is tall and ripe, break it to harvest. Three ears of skywheat bake into a loaf.')),
    (6, -32, 'Lumen', (0.92, 0.78, 0.48),
     ('Glimmer is scarce in the wild, but a few motes practice here. Walk into a golden mote to catch one.',
      'Spend 1 Glimmer on the waystone so it remembers you, then travel to the shrine on the far knoll. The Font spends Glimmer for lasting gifts.')),
]

CHESTS = {
    # actual chest cell (q, r, y): list of (iid, count) — beside the station, not under an NPC
    (33, -10, SURF + 1): [(I.STICK.id, 8), (MT.ID['heartwood'], 8)],
    (59, 31, SURF + 1): [(I.EMBERITE.id, 6), (I.HOPMEAT.id, 2), (MT.ID['stone'], 16)],
    (37, 51, SURF + 1): [(MT.ID['planks'], 16), (MT.ID['door'], 2), (MT.ID['ladder'], 6)],
    (7, 55, SURF + 1): [(I.ROD.id, 1), (I.BERRIES.id, 4)],
    (-25, 39, SURF + 1): [(I.HOE.id, 1), (I.GRAIN_SEEDS.id, 6), (I.ROOT_SEEDS.id, 4), (I.BERRY_SEEDS.id, 4)],
    (5, -31, SURF + 1): [(I.GLIMMER.id, 4), (MT.ID['waystone'], 1)],
}

# second waystone for travel practice, on the shrine knoll across the bridge
WAY_B = (10, -58)


def _local(cq, cr, q, r):
    lq, lr = q - cq * CHUNK, r - cr * CHUNK
    if 0 <= lq < CHUNK and 0 <= lr < CHUNK:
        return lq, lr
    return None


def _put(cells, meta, cq, cr, q, r, y, mat, mt=0):
    loc = _local(cq, cr, q, r)
    if loc is None or not (0 <= y < LAYERS):
        return
    lq, lr = loc
    cells[lq, y, lr] = mat
    meta[lq, y, lr] = mt


def _column(cells, meta, cq, cr, q, r, bot, top, fill, cap):
    for y in range(bot, top):
        _put(cells, meta, cq, cr, q, r, y, fill)
    _put(cells, meta, cq, cr, q, r, top, cap)


def _tree(cells, meta, cq, cr, q, r, h=7):
    for i in range(h):
        _put(cells, meta, cq, cr, q, r, SURF + 1 + i, M['heartwood'])
    for dq, dr in [(0, 0)] + DIRS:
        for dy in range(h - 2, h + 2):
            if dq == 0 and dr == 0 and dy < h:
                continue
            _put(cells, meta, cq, cr, q + dq, r + dr, SURF + 1 + dy, M['canopy'])


def _cube_round(q, r, s):
    rq, rr, rs = int(round(q)), int(round(r)), int(round(s))
    dq, dr, ds = abs(rq - q), abs(rr - r), abs(rs - s)
    if dq > dr and dq > ds:
        rq = -rr - rs
    elif dr > ds:
        rr = -rq - rs
    return rq, rr


def hex_line(q0, r0, q1, r1):
    n = hex_distance(q0, r0, q1, r1)
    if n == 0:
        return [(q0, r0)]
    pts = []
    s0, s1 = -q0 - r0, -q1 - r1
    for i in range(n + 1):
        t = i / n
        q, r = _cube_round(q0 + (q1 - q0) * t, r0 + (r1 - r0) * t, s0 + (s1 - s0) * t)
        pts.append((q, r))
    return pts


def in_land(q, r):
    """The spread lesson grounds: plaza, lobes, and a shrine knoll across a gap."""
    if hex_distance(q, r, 10, -58) <= 10:
        return True
    # cloud-sea cut between the south shore and the knoll (the bridge crosses it)
    if -48 <= r <= -39:
        return False
    if hex_distance(q, r, 0, 0) <= 18:
        return True
    if hex_distance(q, r, 38, 12) <= 32:
        return True
    if hex_distance(q, r, 56, 28) <= 14:
        return True
    if hex_distance(q, r, 20, 48) <= 26:
        return True
    if hex_distance(q, r, -22, 36) <= 18:
        return True
    if hex_distance(q, r, 6, -28) <= 14:
        return True
    if hex_distance(q, r, 16, 30) <= 20:
        return True
    if hex_distance(q, r, 0, 24) <= 14:
        return True
    if hex_distance(q, r, 20, -10) <= 16:
        return True
    if hex_distance(q, r, -4, 42) <= 16:
        return True
    if hex_distance(q, r, 28, 22) <= 12:
        return True
    return False


def _rim(q, r):
    """Coast cells get a slightly raised edge."""
    if not in_land(q, r):
        return False
    for dq, dr in DIRS:
        if not in_land(q + dq, r + dr):
            return True
    return False


def _mat(name, fallback='stone'):
    return M[name] if name in M else M[fallback]


def generate_chunk(cq, cr):
    """Themed lesson grounds at the origin; everywhere else is empty sky."""
    cells = np.zeros((CHUNK, LAYERS, CHUNK), np.uint8)
    meta = np.zeros((CHUNK, LAYERS, CHUNK), np.uint8)
    realm = np.zeros((CHUNK, CHUNK), np.uint8)
    q0, r0 = cq * CHUNK, cr * CHUNK
    # cheap reject: the grounds live near the origin (knoll included)
    if q0 > 80 or q0 + CHUNK < -50 or r0 > 80 or r0 + CHUNK < -76:
        return cells, meta, realm

    ivory = _mat('ivory_plaster', 'pale_planks')
    blush = _mat('blush_plaster', 'pale_planks')
    sage = _mat('sage_plaster', 'pale_planks')
    dusk = _mat('dusk_plaster', 'carved_stone')
    ochre = _mat('ochre_bricks', 'bricks')
    terra = _mat('pearl_terrazzo', 'packed_earth')
    tile = _mat('honey_patterned_tile', 'terracotta')
    ink_tile = _mat('ink_patterned_tile', 'stone_bricks')
    woven = _mat('leaf_woven_panel', 'planks')
    lattice = _mat('wood_lattice', 'glass')
    pale_lat = _mat('pale_lattice', 'glass')
    stain_tide = _mat('tide_stained_glass', 'glass')
    stain_rose = _mat('rose_stained_glass', 'glass')
    stain_sky = _mat('sky_stained_glass', 'glass')
    clamp_honey = _mat('honey_crystal_lamp', 'ember_lamp')
    clamp_sky = _mat('sky_crystal_lamp', 'glowstick')
    clamp_violet = _mat('violet_crystal_lamp', 'lantern')
    banner_rose = _mat('rose_banner', 'petals')
    banner_leaf = _mat('leaf_banner', 'petals')
    banner_sky = _mat('sky_banner', 'petals')
    banner_honey = _mat('honey_banner', 'petals')
    cosmic = _mat('cosmic_star', 'glimmer_font')
    brass = _mat('brass', 'copper_block' if 'copper_block' in M else 'stone')
    iron = _mat('wrought_iron', 'stone')
    pewter = _mat('pewter', 'stone')

    for lq in range(CHUNK):
        for lr in range(CHUNK):
            q, r = q0 + lq, r0 + lr
            if not in_land(q, r):
                continue
            realm[lq, lr] = 0
            knoll = hex_distance(q, r, 10, -58) <= 10
            top = SURF + (1 if _rim(q, r) else 0) + (2 if knoll else 0)
            fill = M['carved_stone'] if knoll else M['stone']
            cap_dirt = M['loam']
            _column(cells, meta, cq, cr, q, r, BOT, top - 1, fill, cap_dirt)
            cap = M['turf']
            if knoll:
                cap = M['carved_stone'] if hex_distance(q, r, 10, -58) >= 8 else M['turf']
            elif hex_distance(q, r, 0, 0) <= 8:
                cap = terra
            _put(cells, meta, cq, cr, q, r, top, cap)
            # keep a record of the actual surface height in a simple way: most of the
            # island is SURF; rim is SURF+1; knoll is SURF+2 or +3. Stations sit at SURF
            # on flattened pads painted below.

    def _paint_path(pts, mat, wide=True):
        seen = set()
        for q, r in pts:
            ring = [(q, r)]
            if wide:
                ring += [(q + dq, r + dr) for dq, dr in DIRS]
            for qq, rr in ring:
                if (qq, rr) in seen:
                    continue
                seen.add((qq, rr))
                if not in_land(qq, rr) and not (-50 <= rr <= -37):
                    continue
                loc = _local(cq, cr, qq, rr)
                if loc is None:
                    continue
                # flatten a walkable pad at SURF even if the rim was raised
                if cells[loc[0], SURF, loc[1]] == 0:
                    _column(cells, meta, cq, cr, qq, rr, BOT, SURF - 1, M['stone'], M['loam'])
                _put(cells, meta, cq, cr, qq, rr, SURF, mat)
                for y in range(SURF + 1, SURF + 4):
                    # don't wipe buildings; the path is stamped before stations
                    _put(cells, meta, cq, cr, qq, rr, y, 0)

    # Path from the plaza through every lesson, then over the bridge to the knoll.
    waypoints = [
        (0, 0), (6, 2), (16, -4), (34, -8), (48, 0), (58, 8),
        (60, 20), (60, 32), (50, 42), (38, 52), (20, 54), (6, 54),
        (-10, 48), (-26, 38), (-8, 20), (0, 8), (0, 0),
        (4, -16), (6, -32), (8, -38), (8, -48), (10, -58),
    ]
    pts = []
    for i in range(len(waypoints) - 1):
        pts.extend(hex_line(*waypoints[i], *waypoints[i + 1]))
    _paint_path(pts, tile, wide=True)

    # Signposts at the turns, pointing along the path
    for q, r in ((14, -4), (46, 2), (60, 20), (50, 42), (20, 54),
                 (-10, 48), (-8, 20), (4, -16), (8, -38)):
        _put(cells, meta, cq, cr, q, r, SURF, tile)
        _put(cells, meta, cq, cr, q, r, SURF + 1, M['signpost'])

    # ----- Plaza -----
    for dq in range(-7, 8):
        for dr in range(-7, 8):
            if hex_distance(0, 0, dq, dr) <= 7:
                q, r = dq, dr
                if not in_land(q, r):
                    continue
                ring = hex_distance(0, 0, dq, dr)
                mat = ink_tile if ring in (5, 6) else (tile if ring >= 3 else terra)
                _put(cells, meta, cq, cr, q, r, SURF, mat)
                for y in range(SURF + 1, SURF + 3):
                    _put(cells, meta, cq, cr, q, r, y, 0)
    # Low fountain (does not hide the horizon)
    for dq, dr in [(0, 0)] + DIRS:
        _put(cells, meta, cq, cr, dq, dr, SURF, ivory)
    _put(cells, meta, cq, cr, 0, 0, SURF, pewter)
    _put(cells, meta, cq, cr, 0, 0, SURF + 1, M['water'], 7)
    for dq, dr in DIRS:
        _put(cells, meta, cq, cr, dq, dr, SURF + 1, stain_tide)
        _put(cells, meta, cq, cr, dq, dr, SURF + 2, 0)
    # Banners and lamps at the plaza rim, kept off the -Z view corridor
    for q, r, b in ((7, 3, banner_rose), (7, 5, banner_honey), (-6, 5, banner_sky),
                    (8, 1, banner_leaf), (-7, 3, banner_rose)):
        _put(cells, meta, cq, cr, q, r, SURF + 1, b)
    for q, r in ((7, 4), (-6, 4)):
        _put(cells, meta, cq, cr, q, r, SURF + 1, ivory)
    _put(cells, meta, cq, cr, 7, 4, SURF + 2, clamp_honey)
    # Welcome bedroll, off the spawn cell and off the view corridor
    _put(cells, meta, cq, cr, 3, 2, SURF + 1, M['bedroll'])
    _put(cells, meta, cq, cr, 2, 3, SURF + 1, M['glowstick'])
    # Low plaster benches
    for q, r in ((-3, 5), (4, 5), (5, 4)):
        _put(cells, meta, cq, cr, q, r, SURF + 1, ivory)

    # ----- Bram's grove -----
    for q, r, h in ((32, -12, 8), (36, -12, 7), (37, -9, 8), (31, -6, 7),
                    (38, -6, 6), (30, -11, 7)):
        _tree(cells, meta, cq, cr, q, r, h)
    # Small quarry outcrop
    for q, r in ((35, -5), (36, -5), (36, -4), (37, -5)):
        _put(cells, meta, cq, cr, q, r, SURF, M['stone'])
        _put(cells, meta, cq, cr, q, r, SURF + 1, M['cobble'] if 'cobble' in M else M['stone'])
        _put(cells, meta, cq, cr, q, r, SURF + 2, M['stone'])

    # ----- Tess's workshop -----
    _workshop(cells, meta, cq, cr, 58, 4, blush, pale_lat, stain_rose, clamp_sky, banner_rose)

    # ----- Cole's kiln hall -----
    _kiln_hall(cells, meta, cq, cr, 60, 28, ochre, iron, brass, clamp_honey)

    # ----- Mira's practice house -----
    _practice_house(cells, meta, cq, cr, 38, 48, sage, stain_sky, pale_lat, lattice)

    # ----- Finn's pond and pier -----
    _pond(cells, meta, cq, cr, 10, 60, 5)
    for q, r in ((6, 54), (6, 55), (7, 54), (7, 56), (8, 56), (8, 57)):
        _put(cells, meta, cq, cr, q, r, SURF, M['planks'])
        _put(cells, meta, cq, cr, q, r, SURF + 1, 0)
    _put(cells, meta, cq, cr, 6, 56, SURF + 1, lattice)
    _put(cells, meta, cq, cr, 9, 57, SURF + 1, banner_sky)
    _put(cells, meta, cq, cr, 5, 54, SURF + 1, banner_sky)

    # ----- Sela's terraces -----
    beds = [(-28, 40), (-27, 40), (-26, 40), (-25, 40),
            (-28, 41), (-27, 41), (-26, 41), (-25, 41),
            (-27, 42), (-26, 42), (-25, 42),
            (-24, 40), (-24, 41)]
    for q, r in beds:
        _put(cells, meta, cq, cr, q, r, SURF, M['farmland'])
        _put(cells, meta, cq, cr, q, r, SURF + 1, 0)
    _put(cells, meta, cq, cr, -28, 40, SURF + 1, M['skywheat'], 2)
    _put(cells, meta, cq, cr, -25, 41, SURF + 1, M['berry_crop'], 1)
    _put(cells, meta, cq, cr, -26, 42, SURF + 1, M['skywheat'], 1)
    for q, r in ((-29, 39), (-29, 41), (-23, 39), (-23, 42), (-28, 43)):
        _put(cells, meta, cq, cr, q, r, SURF + 1, woven)
    _put(cells, meta, cq, cr, -24, 43, SURF + 1, banner_leaf)
    # A little irrigation pool
    for q, r in ((-22, 43), (-21, 43), (-22, 44)):
        _put(cells, meta, cq, cr, q, r, SURF - 1, M['stone'])
        _put(cells, meta, cq, cr, q, r, SURF, M['water'], 7)
        _put(cells, meta, cq, cr, q, r, SURF + 1, 0)

    # ----- Lumen's way-court on the south shore -----
    for dq in range(-3, 4):
        for dr in range(-3, 3):
            if hex_distance(0, 0, dq, dr) <= 3:
                q, r = 6 + dq, -32 + dr
                _put(cells, meta, cq, cr, q, r, SURF, dusk)
                for y in range(SURF + 1, SURF + 3):
                    if (q, r) != (6, -32):
                        pass
    _put(cells, meta, cq, cr, 6, -32, SURF + 1, 0)  # Lumen stands here; waystone is beside
    _put(cells, meta, cq, cr, 8, -32, SURF + 1, M['waystone'], 0)
    _put(cells, meta, cq, cr, 4, -33, SURF + 1, M['glimmer_font'], 0)
    _put(cells, meta, cq, cr, 8, -34, SURF + 1, clamp_violet)
    _put(cells, meta, cq, cr, 4, -30, SURF + 1, banner_honey)

    # ----- Bridge over the cloud gap -----
    _bridge(cells, meta, cq, cr, 8, -38, 8, -48, M['pale_planks'] if 'pale_planks' in M else M['planks'],
            lattice, brass)

    # ----- Shrine knoll -----
    _put(cells, meta, cq, cr, 10, -58, SURF + 3, M['carved_stone'])
    _put(cells, meta, cq, cr, 10, -58, SURF + 4, M['waystone'], 0)
    for dq, dr in DIRS:
        _put(cells, meta, cq, cr, 10 + dq, -58 + dr, SURF + 3, M['carved_stone'])
        _put(cells, meta, cq, cr, 10 + dq, -58 + dr, SURF + 4, 0)
    _put(cells, meta, cq, cr, 10, -60, SURF + 4, dusk)
    _put(cells, meta, cq, cr, 10, -60, SURF + 5, dusk)
    _put(cells, meta, cq, cr, 10, -60, SURF + 6, cosmic)
    _put(cells, meta, cq, cr, 12, -57, SURF + 4, clamp_violet)
    _put(cells, meta, cq, cr, 8, -57, SURF + 4, banner_honey)

    # Chests at stations
    for (q, r, y) in CHESTS:
        _put(cells, meta, cq, cr, q, r, y, M['chest'], 0)
        _put(cells, meta, cq, cr, q, r, y - 1, tile if (q, r) != (5, -31) else dusk)

    # Last: every lesson NPC stands in open air with a solid cell underfoot
    for q, r, *_rest in NPCS:
        loc = _local(cq, cr, q, r)
        if not loc:
            continue
        if cells[loc[0], SURF, loc[1]] == 0:
            _column(cells, meta, cq, cr, q, r, BOT, SURF - 1, M['stone'], M['loam'])
            _put(cells, meta, cq, cr, q, r, SURF, tile)
        for y in range(SURF + 1, SURF + 4):
            _put(cells, meta, cq, cr, q, r, y, 0)

    return cells, meta, realm


def _workshop(cells, meta, cq, cr, q, r, plaster, lattice, stain, lamp, banner):
    """A roomy open-front workshop; Tess stands in the yard to the north."""
    # floor
    for dq in range(-3, 4):
        for dr in range(-3, 3):
            _put(cells, meta, cq, cr, q + dq, r + dr, SURF, plaster if abs(dq) + abs(dr) else _mat('honey_patterned_tile', 'pale_planks'))
            _put(cells, meta, cq, cr, q + dq, r + dr, SURF + 1, 0)
            _put(cells, meta, cq, cr, q + dq, r + dr, SURF + 2, 0)
    # walls (open on +r, Tess's yard)
    for dq in range(-3, 4):
        for dr in range(-3, 3):
            edge = dq in (-3, 3) or dr == -3
            if edge:
                win = (dr == -3 and dq in (-1, 1)) or (dq in (-3, 3) and dr == -1)
                _put(cells, meta, cq, cr, q + dq, r + dr, SURF + 1, plaster)
                _put(cells, meta, cq, cr, q + dq, r + dr, SURF + 2, stain if win else plaster)
            _put(cells, meta, cq, cr, q + dq, r + dr, SURF + 3, plaster)
    _put(cells, meta, cq, cr, q, r, SURF + 1, M['tinker_bench'], 0)
    _put(cells, meta, cq, cr, q - 3, r + 2, SURF + 1, banner)
    _put(cells, meta, cq, cr, q + 3, r + 2, SURF + 1, banner)
    _put(cells, meta, cq, cr, q + 2, r + 2, SURF + 1, lattice)


def _kiln_hall(cells, meta, cq, cr, q, r, brick, iron, brass, lamp):
    """Open-front kiln hall; Cole stands in the yard to the north."""
    for dq in range(-3, 4):
        for dr in range(-3, 3):
            _put(cells, meta, cq, cr, q + dq, r + dr, SURF, brick)
            _put(cells, meta, cq, cr, q + dq, r + dr, SURF + 1, 0)
            _put(cells, meta, cq, cr, q + dq, r + dr, SURF + 2, 0)
    for dq in range(-3, 4):
        for dr in range(-3, 3):
            edge = dq in (-3, 3) or dr == -3
            if edge:
                _put(cells, meta, cq, cr, q + dq, r + dr, SURF + 1, brick)
                _put(cells, meta, cq, cr, q + dq, r + dr, SURF + 2, iron if dq == 0 and dr == -3 else brick)
            _put(cells, meta, cq, cr, q + dq, r + dr, SURF + 3, brick)
            if abs(dq) == 3 or dr == -3:
                _put(cells, meta, cq, cr, q + dq, r + dr, SURF + 4, brick)
    _put(cells, meta, cq, cr, q, r, SURF + 1, M['kiln'], 0)
    _put(cells, meta, cq, cr, q + 2, r - 1, SURF + 1, brass)


def _practice_house(cells, meta, cq, cr, q, r, plaster, stain, pale_lat, lattice):
    """Two-storey practice house, open door on the north, ladder on the west wall.

    Mira stands in the yard north of the door, never inside the house.
    """
    # footprint dq -3..3, dr -2..2; door at (q, r+2)
    for dq in range(-3, 4):
        for dr in range(-2, 3):
            _put(cells, meta, cq, cr, q + dq, r + dr, SURF, plaster)
    # walls two storeys, windows, roof
    for dq in range(-3, 4):
        for dr in range(-2, 3):
            edge = dq in (-3, 3) or dr in (-2, 2)
            door = dr == 2 and dq == 0
            if edge and not door:
                win = (dr in (-2, 2) and dq in (-2, 2)) or (dq in (-3, 3) and dr == 0)
                _put(cells, meta, cq, cr, q + dq, r + dr, SURF + 1, plaster)
                _put(cells, meta, cq, cr, q + dq, r + dr, SURF + 2, stain if win else plaster)
                _put(cells, meta, cq, cr, q + dq, r + dr, SURF + 3, plaster)
                _put(cells, meta, cq, cr, q + dq, r + dr, SURF + 4, stain if win else plaster)
            if door:
                _put(cells, meta, cq, cr, q + dq, r + dr, SURF + 1, M['door'], 4 | 8)
                _put(cells, meta, cq, cr, q + dq, r + dr, SURF + 2, M['door'], 16 | 4 | 8)
                _put(cells, meta, cq, cr, q + dq, r + dr, SURF + 3, plaster)
            # roof
            _put(cells, meta, cq, cr, q + dq, r + dr, SURF + 5, plaster)
    # interior floor of the loft, leaving a hole by the ladder
    for dq in range(-2, 3):
        for dr in range(-1, 2):
            if not (dq == -2 and dr == 0):
                _put(cells, meta, cq, cr, q + dq, r + dr, SURF + 3, _mat('pale_planks', 'planks'))
    # exterior ladder on the west wall
    for y in range(SURF + 1, SURF + 6):
        _put(cells, meta, cq, cr, q - 4, r, y, M['ladder'], 4)
    _put(cells, meta, cq, cr, q - 3, r, SURF + 1, lattice)
    _put(cells, meta, cq, cr, q + 4, r + 2, SURF + 1, pale_lat)


def _pond(cells, meta, cq, cr, cq0, cr0, rad):
    for dq in range(-rad, rad + 1):
        for dr in range(-rad, rad + 1):
            if hex_distance(0, 0, dq, dr) <= rad:
                q, r = cq0 + dq, cr0 + dr
                for y in range(SURF - 2, SURF + 1):
                    _put(cells, meta, cq, cr, q, r, y, 0)
                _put(cells, meta, cq, cr, q, r, SURF - 2, M['stone'])
                _put(cells, meta, cq, cr, q, r, SURF - 1, M['water'], 7)


def _bridge(cells, meta, cq, cr, q0, r0, q1, r1, plank, rail, post):
    pts = hex_line(q0, r0, q1, r1)
    for q, r in pts:
        _put(cells, meta, cq, cr, q, r, SURF, plank)
        _put(cells, meta, cq, cr, q, r, SURF + 1, 0)
        _put(cells, meta, cq, cr, q, r, SURF + 2, 0)
        # a supporting stem so the span doesn't look like a floating ribbon
        for y in range(SURF - 4, SURF):
            _put(cells, meta, cq, cr, q, r, y, post if y == SURF - 4 else plank)
        # rails on either side
        for i, (dq, dr) in enumerate(DIRS[:2]):
            _put(cells, meta, cq, cr, q + dq, r + dr, SURF, plank)
            _put(cells, meta, cq, cr, q + dq, r + dr, SURF + 1, rail)
    # a lamp post on the knoll side of the bridge
    _put(cells, meta, cq, cr, q0, r0, SURF + 1, post)
    _put(cells, meta, cq, cr, q1, r1, SURF + 1, post)
    _put(cells, meta, cq, cr, q1, r1, SURF + 2, _mat('sky_crystal_lamp', 'lantern'))
    # keep the deck under the end lamps walkable beside the post
    _put(cells, meta, cq, cr, q0, r0, SURF, plank)
    _put(cells, meta, cq, cr, q1, r1, SURF, plank)


def npc_records():
    out = []
    for q, r, name, color, lines in NPCS:
        x, z = center(q, r)
        out.append({'q': q, 'r': r, 'x': x, 'y': (SURF + 1) * LAYER, 'z': z,
                    'name': name, 'color': color, 'lines': list(lines), 'line': 0, 'yaw': 180.0})
    return out


def chest_key(q, r, y):
    return f'{q},{r},{y}'


def fill_tutorial_chests(session):
    for (q, r, y), items in CHESTS.items():
        key = chest_key(q, r, y)
        if key in session.chests:
            continue
        inv = session.chests[key] = __import__('tidewake.inventory', fromlist=['Inventory']).Inventory(27)
        for iid, n in items:
            inv.add(iid, n)


def shrine_pos():
    x, z = center(10, -58)
    return x, (SURF + 4) * LAYER, z
