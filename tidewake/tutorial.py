"""A small hand-built lesson island, launched from the title screen."""
import numpy as np

from .config import CHUNK, LAYERS, LAYER
from .hexgrid import center, hex_distance, DIRS
from . import materials as MT
from . import items as I

M = MT.ID
SURF = 48
BOT = 42
RADIUS = 16
SPAWN = (0, 0, SURF)

# (q, r, name, colour, lines)
NPCS = [
    (0, 0, 'Willow', (0.86, 0.72, 0.58),
     ('Welcome to the lesson island. Walk with W A S D, look with the mouse, and jump with Space.',
      'Follow the path and talk to everyone. Press E for your backpack, J for the journal, P for the Path.')),
    (5, -1, 'Bram', (0.55, 0.62, 0.48),
     ('Hold left click on a tree to gather wood. Heartwood becomes planks at the bench.',
      'Stone needs a pick. Craft one from sticks and cobble once you have a Tinker Bench.')),
    (8, 1, 'Tess', (0.78, 0.58, 0.62),
     ('Press E. Turn Heartwood into Planks, then Planks into Sticks and a Tinker Bench.',
      'Right-click a placed bench for the full 3×3 grid. Click a recipe in the book to fill it.')),
    (11, 2, 'Cole', (0.70, 0.50, 0.40),
     ('Right-click the kiln. Fuel goes underneath, and what you cook or smelt goes on the left.',
      'There is Emberite and some hopmeat in the chest if you want to try it now.')),
    (13, -2, 'Mira', (0.62, 0.70, 0.78),
     ('Right-click to place a block. A door needs two empty cells, one above the other — then right-click to open it.',
      'Ladders hang on a wall. Walk into the rungs to climb. There are extras in the chest.')),
    (6, 7, 'Finn', (0.50, 0.68, 0.72),
     ('Take the fishing rod from the chest. Right-click the pool to cast, and wait.',
      'When the bobber dips, right-click again to reel. Pull too early and the fish gets away.')),
    (3, 6, 'Sela', (0.62, 0.58, 0.40),
     ('A hoe tills turf or loam into a bed. Plant the seeds from the chest, then wait — they grow faster by a pool.',
      'When a crop is tall and ripe, break it to harvest. Three ears of skywheat bake into a loaf.')),
    (0, -7, 'Lumen', (0.92, 0.78, 0.48),
     ('Glimmer is scarce in the wild, but a few motes practice here. Walk into a golden mote to catch one.',
      'Spend 1 Glimmer on the waystone so it remembers you, then travel to the shrine on the far knoll. The Font spends Glimmer for lasting gifts.')),
]

CHESTS = {
    # actual chest cell (q, r, y): list of (iid, count)
    (8, -1, SURF + 1): [(I.STICK.id, 8), (MT.ID['heartwood'], 8)],
    (10, 3, SURF + 1): [(I.EMBERITE.id, 6), (I.HOPMEAT.id, 2), (MT.ID['stone'], 16)],
    (12, -3, SURF + 1): [(MT.ID['planks'], 16), (MT.ID['door'], 2), (MT.ID['ladder'], 6)],
    (5, 6, SURF + 1): [(I.ROD.id, 1), (I.BERRIES.id, 4)],
    (3, 5, SURF + 1): [(I.HOE.id, 1), (I.GRAIN_SEEDS.id, 6), (I.ROOT_SEEDS.id, 4), (I.BERRY_SEEDS.id, 4)],
    (1, -6, SURF + 1): [(I.GLIMMER.id, 4), (MT.ID['waystone'], 1)],
}

# second waystone for travel practice
WAY_B = (9, -7)


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


def _tree(cells, meta, cq, cr, q, r, h=5):
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
            # a slightly raised rim, a lower pond bowl later
            top = SURF + (1 if d >= RADIUS - 1 else 0)
            _column(cells, meta, cq, cr, q, r, BOT, top - 1, M['stone'], M['loam'])
            _put(cells, meta, cq, cr, q, r, top, M['turf'])

    # packed-earth path through the stations
    path = [(0, 0), (2, -1), (4, -1), (5, -1), (6, 0), (8, 1), (10, 2), (11, 2),
            (12, 0), (13, -2), (10, 3), (8, 5), (6, 7), (4, 6), (3, 6),
            (1, 3), (0, -3), (0, -7), (5, -7), (9, -7)]
    for q, r in path:
        loc = _local(cq, cr, q, r)
        if loc and cells[loc[0], SURF, loc[1]] in (M['turf'], M['loam'], M['stone']):
            _put(cells, meta, cq, cr, q, r, SURF, M['packed_earth'])

    # trees for the mining lesson
    for q, r in ((4, -2), (6, -2), (5, 0), (3, -3)):
        _tree(cells, meta, cq, cr, q, r, 5)

    # Tess's hut: a tiny plank room with a bench and a chest
    _hut(cells, meta, cq, cr, 8, 1, M['tinker_bench'])
    # Cole's kiln shed
    _hut(cells, meta, cq, cr, 11, 2, M['kiln'], w=2)
    _put(cells, meta, cq, cr, 11, 2, SURF + 1, M['kiln'], 0)
    # Mira's yard: a short wall, a clear open door in a frame, and a ladder
    for i in range(3):
        _put(cells, meta, cq, cr, 14, -2, SURF + 1 + i, M['pale_planks'])
        _put(cells, meta, cq, cr, 14, 0, SURF + 1 + i, M['pale_planks'])
    # door posts and a lintel, opening in the middle
    for y in (SURF + 1, SURF + 2):
        _put(cells, meta, cq, cr, 13, -2, y, M['pale_planks'])
        _put(cells, meta, cq, cr, 13, 0, y, M['pale_planks'])
    _put(cells, meta, cq, cr, 13, -1, SURF + 3, M['pale_planks'])
    # face the yard and stand slightly ajar so the leaf and handle read as a door
    _put(cells, meta, cq, cr, 13, -1, SURF + 1, M['door'], 4 | 8)
    _put(cells, meta, cq, cr, 13, -1, SURF + 2, M['door'], 16 | 4 | 8)
    _put(cells, meta, cq, cr, 14, -3, SURF + 1, M['ladder'], 4)
    _put(cells, meta, cq, cr, 14, -3, SURF + 2, M['ladder'], 4)
    _put(cells, meta, cq, cr, 14, -3, SURF + 3, M['ladder'], 4)

    # fishing pond + dock
    for dq in range(-2, 3):
        for dr in range(-2, 3):
            if hex_distance(0, 0, dq, dr) <= 2:
                q, r = 6 + dq, 8 + dr
                # dig a bowl and fill with water
                for y in range(SURF - 2, SURF + 1):
                    _put(cells, meta, cq, cr, q, r, y, 0)
                _put(cells, meta, cq, cr, q, r, SURF - 2, M['stone'])
                _put(cells, meta, cq, cr, q, r, SURF - 1, M['water'], 7)
    for q, r in ((6, 7), (5, 7), (6, 6)):
        _put(cells, meta, cq, cr, q, r, SURF, M['planks'])
        _put(cells, meta, cq, cr, q, r, SURF + 1, 0)

    # farm beds
    for q, r in ((2, 6), (3, 6), (4, 6), (2, 7), (3, 7), (4, 7)):
        _put(cells, meta, cq, cr, q, r, SURF, M['farmland'])
    _put(cells, meta, cq, cr, 2, 6, SURF + 1, M['skywheat'], 2)
    _put(cells, meta, cq, cr, 4, 7, SURF + 1, M['berry_crop'], 1)

    # glimmer knoll + far shrine
    _put(cells, meta, cq, cr, 0, -7, SURF + 1, M['waystone'], 0)
    _put(cells, meta, cq, cr, 1, -7, SURF + 1, M['glimmer_font'], 0)
    for dy in range(1, 3):
        _put(cells, meta, cq, cr, 0, -8, SURF + dy, M['carved_stone'])
    _put(cells, meta, cq, cr, 9, -7, SURF + 1, M['waystone'], 0)
    _put(cells, meta, cq, cr, 9, -7, SURF, M['carved_stone'])
    _put(cells, meta, cq, cr, 9, -8, SURF, M['carved_stone'])

    # welcome bedroll and a glowstick
    _put(cells, meta, cq, cr, 0, 1, SURF + 1, M['bedroll'])
    _put(cells, meta, cq, cr, -1, 0, SURF + 1, M['glowstick'])

    # chests at stations (empty cells above packed earth / planks)
    for (q, r, y) in CHESTS:
        _put(cells, meta, cq, cr, q, r, y, M['chest'], 0)

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
    x, z = center(0, -7)
    return x, (SURF + 2) * LAYER, z
