"""A small hand-built lesson island, launched from the title screen."""
import numpy as np

from .config import CHUNK, LAYERS, LAYER
from .hexgrid import center, hex_distance, DIRS
from . import materials as MT
from . import items as I

M = MT.ID
SURF = 48
BOT = 42
RADIUS = 36
SPAWN = (0, 0, SURF)

# (q, r, name, colour, lines)
NPCS = [
    # stand in the open beside each station, never inside a hut, chest, or waystone
    (2, 1, 'Willow', (0.86, 0.72, 0.58),
     ('Welcome to the lesson island. Walk with W A S D, look with the mouse, and jump with Space.',
      'Follow the packed-earth path and the signposts. Talk to everyone. Press E for your backpack, J for the journal, P for the Path.')),
    (8, -2, 'Bram', (0.55, 0.62, 0.48),
     ('Hold left click on a tree to gather wood. Heartwood becomes planks at the bench.',
      'Stone needs a pick. Craft one from sticks and cobble once you have a Tinker Bench.')),
    (16, 2, 'Tess', (0.78, 0.58, 0.62),
     ('Press E. Turn Heartwood into Planks, then Planks into Sticks and a Tinker Bench.',
      'Right-click a placed bench for the full 3×3 grid. Click a recipe in the book to fill it.')),
    (22, 6, 'Cole', (0.70, 0.50, 0.40),
     ('Right-click the kiln. Fuel goes underneath, and what you cook or smelt goes on the left.',
      'There is Emberite and some hopmeat in the chest if you want to try it now.')),
    (20, -6, 'Mira', (0.62, 0.70, 0.78),
     ('Right-click to place a block. A door needs two empty cells, one above the other — then right-click to open it.',
      'Ladders hang on a wall. Walk into the rungs to climb. There are extras in the chest.')),
    (14, 16, 'Finn', (0.50, 0.68, 0.72),
     ('Take the fishing rod from the chest. Right-click the pool to cast, and wait.',
      'When the bobber dips, right-click again to reel. Pull too early and the fish gets away.')),
    (6, 14, 'Sela', (0.62, 0.58, 0.40),
     ('A hoe tills turf or loam into a bed. Plant the seeds from the chest, then wait — they grow faster by a pool.',
      'When a crop is tall and ripe, break it to harvest. Three ears of skywheat bake into a loaf.')),
    (0, -16, 'Lumen', (0.92, 0.78, 0.48),
     ('Glimmer is scarce in the wild, but a few motes practice here. Walk into a golden mote to catch one.',
      'Spend 1 Glimmer on the waystone so it remembers you, then travel to the shrine on the far knoll. The Font spends Glimmer for lasting gifts.')),
]

CHESTS = {
    # actual chest cell (q, r, y): list of (iid, count) — beside the station, not under an NPC
    (7, -3, SURF + 1): [(I.STICK.id, 8), (MT.ID['heartwood'], 8)],
    (21, 3, SURF + 1): [(I.EMBERITE.id, 6), (I.HOPMEAT.id, 2), (MT.ID['stone'], 16)],
    (21, -7, SURF + 1): [(MT.ID['planks'], 16), (MT.ID['door'], 2), (MT.ID['ladder'], 6)],
    (13, 15, SURF + 1): [(I.ROD.id, 1), (I.BERRIES.id, 4)],
    (5, 15, SURF + 1): [(I.HOE.id, 1), (I.GRAIN_SEEDS.id, 6), (I.ROOT_SEEDS.id, 4), (I.BERRY_SEEDS.id, 4)],
    (1, -15, SURF + 1): [(I.GLIMMER.id, 4), (MT.ID['waystone'], 1)],
}

# second waystone for travel practice
WAY_B = (14, -16)


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


def generate_chunk(cq, cr):
    """A quiet meadow island at the origin; everywhere else is empty sky."""
    cells = np.zeros((CHUNK, LAYERS, CHUNK), np.uint8)
    meta = np.zeros((CHUNK, LAYERS, CHUNK), np.uint8)
    realm = np.zeros((CHUNK, CHUNK), np.uint8)
    q0, r0 = cq * CHUNK, cr * CHUNK
    # cheap reject: island only lives near the origin
    if hex_distance(q0 + CHUNK // 2, r0 + CHUNK // 2, 0, 0) > RADIUS + CHUNK:
        return cells, meta, realm

    for lq in range(CHUNK):
        for lr in range(CHUNK):
            q, r = q0 + lq, r0 + lr
            d = hex_distance(q, r, 0, 0)
            if d > RADIUS:
                continue
            realm[lq, lr] = 0
            # a slightly raised rim, a low knoll in the south, room to walk
            knoll = hex_distance(q, r, 0, -16) <= 4
            top = SURF + (1 if d >= RADIUS - 2 else 0) + (2 if knoll else 0)
            _column(cells, meta, cq, cr, q, r, BOT, top - 1, M['stone'], M['loam'])
            _put(cells, meta, cq, cr, q, r, top, M['turf'])

    def _paint_path(cells, meta, cq, cr, pts, wide=True):
        seen = set()
        for i, (q, r) in enumerate(pts):
            ring = [(q, r)]
            if wide:
                ring += [(q + dq, r + dr) for dq, dr in DIRS]
            for qq, rr in ring:
                if (qq, rr) in seen:
                    continue
                seen.add((qq, rr))
                loc = _local(cq, cr, qq, rr)
                if loc and cells[loc[0], SURF, loc[1]] in (M['turf'], M['loam'], M['stone'], M['packed_earth']):
                    _put(cells, meta, cq, cr, qq, rr, SURF, M['packed_earth'])
                    _put(cells, meta, cq, cr, qq, rr, SURF + 1, 0)

    # packed-earth path, station to station, wide enough to see the next person
    path = [(0, 0), (2, 1), (5, 0), (8, -2), (12, 0), (16, 2), (19, 4), (22, 6),
            (22, 0), (22, -4), (20, -6), (16, -4), (12, 6), (14, 16), (10, 16),
            (6, 14), (2, 6), (0, 0), (0, -8), (0, -16), (8, -16), (14, -16)]
    _paint_path(cells, meta, cq, cr, path)

    # signposts at the turns, pointing along the path
    for q, r in ((4, 0), (12, 0), (19, 5), (22, -2), (12, 8), (2, 4), (0, -8)):
        _put(cells, meta, cq, cr, q, r, SURF, M['packed_earth'])
        _put(cells, meta, cq, cr, q, r, SURF + 1, M['signpost'])

    # trees for the mining lesson — beside Bram, not on him
    for q, r in ((7, -5), (9, -5), (10, -3), (6, -4)):
        _tree(cells, meta, cq, cr, q, r, 7)

    # Tess's hut (bench inside); Tess stands in the yard in front
    _hut(cells, meta, cq, cr, 16, 0, M['tinker_bench'])
    # Cole's kiln shed; Cole stands in front
    _hut(cells, meta, cq, cr, 22, 4, M['kiln'], w=2)
    _put(cells, meta, cq, cr, 22, 4, SURF + 1, M['kiln'], 0)
    # Mira's yard: a short wall, a clear open door in a frame, and a ladder
    for i in range(3):
        _put(cells, meta, cq, cr, 23, -6, SURF + 1 + i, M['pale_planks'])
        _put(cells, meta, cq, cr, 23, -4, SURF + 1 + i, M['pale_planks'])
    for y in (SURF + 1, SURF + 2):
        _put(cells, meta, cq, cr, 22, -6, y, M['pale_planks'])
        _put(cells, meta, cq, cr, 22, -4, y, M['pale_planks'])
    _put(cells, meta, cq, cr, 22, -5, SURF + 3, M['pale_planks'])
    _put(cells, meta, cq, cr, 22, -5, SURF + 1, M['door'], 4 | 8)
    _put(cells, meta, cq, cr, 22, -5, SURF + 2, M['door'], 16 | 4 | 8)
    _put(cells, meta, cq, cr, 23, -7, SURF + 1, M['ladder'], 4)
    _put(cells, meta, cq, cr, 23, -7, SURF + 2, M['ladder'], 4)
    _put(cells, meta, cq, cr, 23, -7, SURF + 3, M['ladder'], 4)

    # fishing pond + dock (Finn stands on the dock)
    for dq in range(-3, 4):
        for dr in range(-3, 4):
            if hex_distance(0, 0, dq, dr) <= 3:
                q, r = 16 + dq, 18 + dr
                for y in range(SURF - 2, SURF + 1):
                    _put(cells, meta, cq, cr, q, r, y, 0)
                _put(cells, meta, cq, cr, q, r, SURF - 2, M['stone'])
                _put(cells, meta, cq, cr, q, r, SURF - 1, M['water'], 7)
    for q, r in ((14, 16), (15, 16), (14, 17)):
        _put(cells, meta, cq, cr, q, r, SURF, M['planks'])
        _put(cells, meta, cq, cr, q, r, SURF + 1, 0)

    # farm beds (Sela stands in front of them)
    for q, r in ((5, 16), (6, 16), (7, 16), (5, 17), (6, 17), (7, 17)):
        _put(cells, meta, cq, cr, q, r, SURF, M['farmland'])
    _put(cells, meta, cq, cr, 5, 16, SURF + 1, M['skywheat'], 2)
    _put(cells, meta, cq, cr, 7, 17, SURF + 1, M['berry_crop'], 1)

    # glimmer knoll + far shrine (Lumen stands beside the waystone, not in it)
    _put(cells, meta, cq, cr, 2, -16, SURF + 1, M['waystone'], 0)
    _put(cells, meta, cq, cr, 1, -17, SURF + 1, M['glimmer_font'], 0)
    for dy in range(1, 3):
        _put(cells, meta, cq, cr, 2, -18, SURF + dy, M['carved_stone'])
    _put(cells, meta, cq, cr, 14, -16, SURF + 1, M['waystone'], 0)
    _put(cells, meta, cq, cr, 14, -16, SURF, M['carved_stone'])
    _put(cells, meta, cq, cr, 14, -17, SURF, M['carved_stone'])

    # welcome bedroll and a glowstick, off the spawn cell
    _put(cells, meta, cq, cr, 0, 1, SURF + 1, M['bedroll'])
    _put(cells, meta, cq, cr, -1, 1, SURF + 1, M['glowstick'])

    # chests at stations (empty cells above packed earth / planks)
    for (q, r, y) in CHESTS:
        _put(cells, meta, cq, cr, q, r, y, M['chest'], 0)

    # last: keep every lesson NPC standing in open air with a clear cell underfoot
    for q, r, *_rest in NPCS:
        loc = _local(cq, cr, q, r)
        if not loc:
            continue
        # if this column was never land (shouldn't happen), skip
        if cells[loc[0], SURF, loc[1]] == 0:
            _column(cells, meta, cq, cr, q, r, BOT, SURF - 1, M['stone'], M['loam'])
            _put(cells, meta, cq, cr, q, r, SURF, M['packed_earth'])
        for y in range(SURF + 1, SURF + 4):
            _put(cells, meta, cq, cr, q, r, y, 0)
        # a little room around their feet too
        for dq, dr in DIRS:
            loc2 = _local(cq, cr, q + dq, r + dr)
            if loc2 and cells[loc2[0], SURF + 1, loc2[1]] not in (
                    0, M['signpost'], M['petals'], M['grass'], M['wildflower'], M['sprout']):
                # don't flatten huts or stations beside them; only clear plant clutter
                if cells[loc2[0], SURF + 1, loc2[1]] in (M['canopy'],):
                    continue

    return cells, meta, realm


def _hut(cells, meta, cq, cr, q, r, station, w=2):
    """A tiny three-wall shelter, open and lit, with a station inside."""
    # pale floor so the room stays bright
    for dq in range(-1, w):
        for dr in range(-1, 2):
            _put(cells, meta, cq, cr, q + dq, r + dr, SURF, M['pale_planks'])
    # walls: pale planks, a wide south doorway, and a glass window on each side
    for dq in range(-1, w):
        for dr in range(-1, 2):
            edge = dq in (-1, w - 1) or dr in (-1, 1)
            doorway = dr == 1 and dq in (0, 1 if w > 2 else 0)
            if edge and not doorway:
                window = (dr in (-1, 1) and dq == (0 if w == 2 else 0)) or (dq in (-1, w - 1) and dr == 0)
                _put(cells, meta, cq, cr, q + dq, r + dr, SURF + 1, M['pale_planks'])
                _put(cells, meta, cq, cr, q + dq, r + dr, SURF + 2,
                     M['glass'] if window else M['pale_planks'])
            _put(cells, meta, cq, cr, q + dq, r + dr, SURF + 3, M['thatch'])
    _put(cells, meta, cq, cr, q, r, SURF + 1, station, 0)
    # a warm lamp so the inside isn't a black cave
    _put(cells, meta, cq, cr, q, r, SURF + 2, M['ember_lamp'], 0)


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
    x, z = center(2, -16)
    return x, (SURF + 2) * LAYER, z
