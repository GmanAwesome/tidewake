"""Items: every block you can hold, plus tools, food and crafting bits.

Block items share their id with the cell they place (ids below 256). Everything else
lives at 256 and up. Recipes are shaped (a pattern on the 2x2 or 3x3 grid) unless
marked shapeless.
"""
import random

from . import materials as MT

M = MT.ID
BLOCK_LIMIT = 256

# hardness in seconds with bare hands; tool kind that speeds it up; minimum tool tier to get a drop
#                       secs  tool    tier
HARD = {
    'stone': (3.0, 'pick', 1), 'basalt': (3.6, 'pick', 1), 'rosestone': (2.6, 'pick', 1), 'plinth': (4.0, 'pick', 1),
    'polished_stone': (3.0, 'pick', 1), 'bricks': (3.4, 'pick', 1), 'mossy_bricks': (3.4, 'pick', 1),
    'mossrock': (2.8, 'pick', 1), 'kiln': (3.2, 'pick', 1), 'ice': (1.0, 'pick', 0),
    'emberite_ore': (4.0, 'pick', 1), 'verdigris_ore': (4.6, 'pick', 2), 'silverine_ore': (5.4, 'pick', 3),
    'aetherite_ore': (7.0, 'pick', 4), 'lumen_lamp': (0.6, None, 0), 'glass': (0.5, None, 0),
    'loam': (0.8, 'spade', 0), 'turf': (0.95, 'spade', 0), 'sand': (0.7, 'spade', 0), 'snow': (0.5, 'spade', 0),
    'clay': (0.9, 'spade', 0), 'cloudstuff': (0.6, 'spade', 0), 'fluff_block': (0.6, None, 0),
    'heartwood': (2.2, 'axe', 0), 'planks': (2.0, 'axe', 0), 'tinker_bench': (2.0, 'axe', 0), 'chest': (2.0, 'axe', 0), 'door': (2.0, 'axe', 0), 'ladder': (0.6, 'axe', 0),
    'canopy': (0.35, None, 0), 'crystal': (0.8, 'pick', 0), 'lumen_shard': (0.8, 'pick', 0),
}
DEFAULT_HARD = (0.15, None, 0)          # small things snap off instantly

_SOUND_HARD = {
    'stone': (3.2, 'pick', 1), 'wood': (2.0, 'axe', 0), 'soft': (0.9, 'spade', 0),
    'sand': (0.7, 'spade', 0), 'glass': (0.5, None, 0), 'puff': (0.6, None, 0), 'leaf': (0.3, None, 0),
}
for _i in range(1, MT.N):
    _key = MT.NAMES[_i].lower().replace(' ', '_')
    if _key not in HARD and MT.SOUND[_i] in _SOUND_HARD:
        HARD[_key] = _SOUND_HARD[MT.SOUND[_i]]
    if 'slab' in _key and _key in HARD:
        s, tool, tier = HARD[_key]
        HARD[_key] = (s * 0.6, tool, tier)
UNBREAKABLE = {M['dormant_spire'], M['awake_spire'], M['water']}

TIERS = ['Wooden', 'Stone', 'Verdigris', 'Silverine', 'Aetherite']
TIER_SPEED = [2.0, 3.6, 5.2, 7.0, 10.0]
TIER_USES = [60, 130, 260, 520, 1600]
TIER_COL = [(0.80, 0.62, 0.42), (0.70, 0.68, 0.66), (0.38, 0.84, 0.70), (0.86, 0.90, 1.00), (0.78, 0.55, 1.00)]
TOOL_KINDS = [('pick', 'Pick'), ('axe', 'Hatchet'), ('spade', 'Spade'), ('blade', 'Blade')]


class Item:
    def __init__(self, iid, name, kind, **kw):
        self.id, self.name, self.kind = iid, name, kind
        self.block = kw.get('block')
        self.tool = kw.get('tool')            # (kind, tier)
        self.food = kw.get('food', 0)
        self.stack = kw.get('stack', 64 if kind != 'tool' else 1)
        self.uses = kw.get('uses', 0)
        self.color = kw.get('color', (0.8, 0.8, 0.8))
        self.color2 = kw.get('color2', self.color)
        self.model = kw.get('model', 'block')
        self.damage = kw.get('damage', 1.0)
        self.desc = kw.get('desc', '')


ITEMS = {}
BY_NAME = {}


def _add(it):
    ITEMS[it.id] = it
    BY_NAME[it.name.lower().replace(' ', '_')] = it
    return it


BLOCK_DESC = {
    'cloudstuff': 'springy: bounce on it', 'vine': 'climb it; it creeps down cliffs', 'bloom': 'glows and spreads in the light',
    'crystal': 'grows in the dusk', 'sprout': 'plant on turf and it grows a tree', 'water': '',
    'tinker_bench': 'place it, then right-click to craft on a 3x3 grid', 'kiln': 'right-click: smelt ores, cook food',
    'chest': 'right-click to store things', 'bedroll': 'right-click to rest: sets your waking spot, skips the dusk',
    'glowstick': 'a little light', 'lumen_lamp': 'a bright lamp', 'mossrock': 'slowly greens stone around it',
    'door': 'right-click to open or close; two blocks tall', 'ladder': 'climb it; place it on a wall',
    'ember_lamp': 'a warm lamp', 'aether_lamp': 'a dusky lamp', 'verdigris_lamp': 'a teal lamp',
    'heather': 'lavender downs packing; a soft purple block',
}
for i in range(1, MT.N):
    key = MT.NAMES[i].lower().replace(' ', '_')
    if MT.NAMES[i] in ('Dormant Spire', 'Awake Spire'):
        continue
    model = 'block' if MT.KIND[i] in ('full', 'glass', 'water', 'slab') else 'deco'
    _add(Item(i, MT.NAMES[i], 'block', block=i, color=tuple(MT.TOP[i]), color2=tuple(MT.SIDE[i]), model=model,
              desc=BLOCK_DESC.get(key, '')))

_next = [256]


def _new(name, kind, **kw):
    it = Item(_next[0], name, kind, **kw)
    _next[0] += 1
    return _add(it)


STICK = _new('Stick', 'item', color=(0.66, 0.50, 0.34), model='stick')
EMBERITE = _new('Emberite', 'item', color=(0.98, 0.52, 0.30), color2=(0.30, 0.28, 0.32), model='lump', desc='burns well in a kiln')
VERDIGRIS = _new('Verdigris Ingot', 'item', color=(0.38, 0.84, 0.70), model='ingot')
SILVERINE = _new('Silverine Ingot', 'item', color=(0.88, 0.92, 1.00), model='ingot')
AETHERITE = _new('Aetherite', 'item', color=(0.80, 0.56, 1.00), model='gem', desc='the rarest stone in the sky')
FLUFF = _new('Fluff', 'item', color=(0.99, 0.95, 0.90), model='lump', desc='from woolhops')
PLUME = _new('Plume', 'item', color=(0.98, 0.86, 0.70), model='stick', desc='from pebblebeaks')
GLIMMER = _new('Glimmer', 'item', color=(1.00, 0.86, 0.45), model='gem', desc='catch golden dusk motes')
GLOOM = _new('Gloom Dust', 'item', color=(0.42, 0.30, 0.62), model='lump', desc='left by gloomlings')
BRICK = _new('Brick', 'item', color=(0.82, 0.46, 0.40), model='ingot')
BERRIES = _new('Duskberries', 'food', food=3, color=(0.62, 0.36, 0.86), model='berries')
HOPMEAT = _new('Raw Hopmeat', 'food', food=2, color=(0.94, 0.56, 0.56), model='lump')
ROAST = _new('Roast Hopmeat', 'food', food=7, color=(0.72, 0.44, 0.28), model='lump')
EGG = _new('Speckled Egg', 'food', food=2, color=(0.98, 0.94, 0.84), model='lump')
PIE = _new('Berry Pie', 'food', food=9, color=(0.92, 0.70, 0.46), color2=(0.62, 0.36, 0.86), model='pie')
STEW = _new('Glowcap Stew', 'food', food=8, color=(0.52, 0.96, 0.86), color2=(0.66, 0.50, 0.34), model='pie')
PAIL = _new('Pail', 'pail', stack=16, color=(0.38, 0.84, 0.70), model='pail', desc='right-click water to fill it')
PAIL_FULL = _new('Pail of Water', 'pail', stack=1, color=(0.38, 0.84, 0.70), color2=(0.36, 0.66, 0.86), model='pail')
TOOLS = {}
for t, tname in enumerate(TIERS):
    for kind, kname in TOOL_KINDS:
        dmg = 2.0 + t * 1.2 + (2.5 if kind == 'blade' else 0.5 if kind == 'axe' else 0)
        TOOLS[(kind, t)] = _new(f'{tname} {kname}', 'tool', tool=(kind, t), uses=TIER_USES[t], color=TIER_COL[t],
                                color2=(0.66, 0.50, 0.34), model=kind, damage=dmg)


def get(iid):
    return ITEMS.get(iid)


def find(name):
    """Look up an item by name, loosely ('stone pick', 'stone_pick', 'pick')."""
    k = name.lower().strip().replace(' ', '_')
    if k in BY_NAME:
        return BY_NAME[k]
    for n, it in BY_NAME.items():
        if n.startswith(k) or k in n:
            return it
    return None


# ------------------------------------------------------------------ mining
def mine_time(mat, item):
    """Seconds to break a cell with this item in hand, and whether it drops."""
    key = MT.NAMES[mat].lower().replace(' ', '_')
    secs, kind, tier = HARD.get(key, DEFAULT_HARD)
    have_kind, have_tier = (item.tool if item and item.tool else (None, -1))
    if kind and have_kind == kind:
        secs /= TIER_SPEED[have_tier]
        drops = have_tier + 1 >= tier
    else:
        drops = tier == 0
        if kind == 'pick' and tier > 0:
            secs *= 1.6
    if have_kind == 'blade' and key == 'canopy':
        secs /= 3
    return max(0.05, secs), drops


def drops_for(mat, rng=random):
    """List of (item id, count) dropped by a broken cell."""
    n = MT.NAMES[mat].lower().replace(' ', '_')
    if n == 'turf':
        return [(M['loam'], 1)]
    if n == 'canopy':
        out = []
        if rng.random() < 0.10:
            out.append((M['sprout'], 1))
        if rng.random() < 0.08:
            out.append((STICK.id, 1))
        return out
    if n == 'emberite_ore':
        return [(EMBERITE.id, 1 + (rng.random() < 0.3))]
    if n == 'aetherite_ore':
        return [(AETHERITE.id, 1)]
    if n == 'berry_bush':
        return [(BERRIES.id, rng.randint(1, 3))] + ([(M['berry_bush'], 1)] if rng.random() < 0.35 else [])
    if n == 'petals':
        return [(M['petals'], 1)] if rng.random() < 0.5 else []
    if n == 'ice':
        return [(M['ice'], 1)]
    if n == 'kiln':
        return [(M['kiln'], 1)]
    return [(mat, 1)]


# ------------------------------------------------------------------ crafting
STONES = 'stoneish'
_STONEISH = ['stone', 'basalt', 'rosestone', 'plinth', 'polished_stone',
            'cobble', 'slate', 'chalk', 'sandstone', 'cinder', 'starstone', 'salt_block', 'pale_stone',
            'polished_basalt', 'polished_rosestone', 'polished_slate', 'polished_chalk',
            'polished_sandstone', 'polished_starstone', 'polished_pale_stone']
GROUPS = {STONES: {M[k] for k in _STONEISH if k in M}}


def _ingr(x):
    return x


RECIPES = []          # (pattern rows of ids or None, (result id, count), shapeless)


def recipe(rows, result, count=1, shapeless=False):
    RECIPES.append((rows, (result, count), shapeless))


W, S, P, G_, E = M['heartwood'], STICK.id, M['planks'], GLIMMER.id, EMBERITE.id
recipe([[W]], P, 4)
recipe([[P], [P]], S, 4)
recipe([[P, P], [P, P]], M['tinker_bench'])
recipe([[STONES, STONES, STONES], [STONES, None, STONES], [STONES, STONES, STONES]], M['kiln'])
recipe([[P, P, P], [P, None, P], [P, P, P]], M['chest'])
recipe([[E], [S]], M['glowstick'], 4)
recipe([[FLUFF.id, FLUFF.id, FLUFF.id], [P, P, P]], M['bedroll'])
recipe([[FLUFF.id, FLUFF.id], [FLUFF.id, FLUFF.id]], M['fluff_block'])
recipe([[BRICK.id, BRICK.id], [BRICK.id, BRICK.id]], M['bricks'])
recipe([[M['bricks'], M['vine']]], M['mossy_bricks'], 1, shapeless=True)
recipe([[STONES, M['vine']]], M['mossrock'], 1, shapeless=True)
recipe([[FLUFF.id, G_], [G_, FLUFF.id]], M['cloudstuff'], 2)
recipe([[M['glass'], M['glass'], M['glass']], [M['glass'], G_, M['glass']], [M['glass'], M['glass'], M['glass']]], M['lumen_lamp'], 2)
recipe([[VERDIGRIS.id], [G_], [M['glass']]], M['lantern'], 2)
recipe([[M['sand'], M['loam']]], M['clay'], 2, shapeless=True)
recipe([[G_, M['sprout']]], M['bloom'], 2, shapeless=True)
recipe([[G_, M['glass']]], M['crystal'], 2, shapeless=True)
recipe([[VERDIGRIS.id, None, VERDIGRIS.id], [None, VERDIGRIS.id, None]], PAIL.id)
recipe([[BERRIES.id, BERRIES.id, BERRIES.id], [EGG.id, M['loam'], EGG.id]], PIE.id, 1)
recipe([[BERRIES.id, BERRIES.id, BERRIES.id], [EGG.id, M['sand'], EGG.id]], PIE.id, 1)
recipe([[M['glowcap'], M['glowcap'], M['heartwood']]], STEW.id, 1, shapeless=True)
recipe([[GLOOM.id, GLOOM.id], [GLOOM.id, GLOOM.id]], G_, 2)
recipe([[STONES, STONES], [STONES, STONES]], M['polished_stone'], 4)
mats = [P, STONES, VERDIGRIS.id, SILVERINE.id, AETHERITE.id]
for t, m in enumerate(mats):
    recipe([[m, m, m], [None, S, None], [None, S, None]], TOOLS[('pick', t)].id)
    recipe([[m, m], [m, S], [None, S]], TOOLS[('axe', t)].id)
    recipe([[m], [S], [S]], TOOLS[('spade', t)].id)
    recipe([[m], [m], [S]], TOOLS[('blade', t)].id)
recipe([[P, P], [P, P], [P, P]], M['door'], 3)
recipe([[S, None, S], [S, S, S], [S, None, S]], M['ladder'], 3)

# ---- 1.4 phase 2b: new woods, stone families, bricks, tiles, lamps, slabs, glass
for _log, _plank in ((M['cedar_heartwood'], M['cedar_planks']),
                     (M['pale_heartwood'], M['pale_planks']),
                     (M['dark_heartwood'], M['dark_planks'])):
    recipe([[_log]], _plank, 4)
recipe([[M['stone'], M['stone']], [M['stone'], M['stone']]], M['cobble'], 4)
for _src, _dst in (
    (M['basalt'], M['polished_basalt']), (M['rosestone'], M['polished_rosestone']),
    (M['slate'], M['polished_slate']), (M['chalk'], M['polished_chalk']),
    (M['sandstone'], M['polished_sandstone']), (M['starstone'], M['polished_starstone']),
    (M['pale_stone'], M['polished_pale_stone']),
):
    recipe([[_src, _src], [_src, _src]], _dst, 4)
for _src, _dst in (
    (M['stone'], M['stone_bricks']), (M['basalt'], M['basalt_bricks']),
    (M['rosestone'], M['rosestone_bricks']), (M['slate'], M['slate_bricks']),
    (M['sandstone'], M['sandstone_bricks']), (M['chalk'], M['chalk_bricks']),
    (M['cinder'], M['cinder_bricks']), (M['snow'], M['snow_bricks']),
    (M['polished_stone'], M['stone_tiles']), (M['polished_basalt'], M['basalt_tiles']),
    (M['polished_rosestone'], M['rosestone_tiles']), (M['polished_slate'], M['slate_tiles']),
    (M['polished_sandstone'], M['sandstone_tiles']), (M['polished_chalk'], M['chalk_tiles']),
    (M['polished_starstone'], M['starstone_tiles']), (M['bricks'], M['clay_tiles']),
    (M['verdigris_bricks'], M['verdigris_tiles']), (M['lavender_bricks'], M['lavender_tiles']),
):
    recipe([[_src, _src], [_src, _src]], _dst, 4)
recipe([[M['bricks'], M['snow']]], M['snow_bricks'], 1, shapeless=True)
recipe([[M['bricks'], M['lumen_shard']]], M['dusk_bricks'], 1, shapeless=True)
recipe([[M['bricks'], M['petals']]], M['lavender_bricks'], 1, shapeless=True)
recipe([[M['bricks'], M['mossrock']]], M['verdigris_bricks'], 1, shapeless=True)
recipe([[M['sand'], M['sand']], [M['sand'], M['stone']]], M['sandstone'], 4)
recipe([[M['cloudstuff'], M['stone']]], M['pale_stone'], 2, shapeless=True)
recipe([[M['canopy'], STICK.id], [STICK.id, M['canopy']]], M['thatch'], 4)
recipe([[M['thatch'], M['thatch']], [M['thatch'], M['thatch']]], M['shingles'], 4)
recipe([[M['polished_stone'], M['polished_stone']], [M['polished_stone'], M['polished_stone']]], M['carved_stone'], 4)
recipe([[M['stone_tiles'], M['glass']]], M['mosaic'], 4, shapeless=True)
recipe([[M['loam'], M['loam']], [M['loam'], M['loam']]], M['packed_earth'], 4)
recipe([[M['planks'], M['canopy']], [M['canopy'], M['planks']]], M['wattle'], 4)
recipe([[FLUFF.id, FLUFF.id], [M['canopy'], FLUFF.id]], M['linen'], 4)
recipe([[M['linen'], M['bloom']]], M['crimson_cloth'], 1, shapeless=True)
recipe([[M['linen'], M['lumen_shard']]], M['dusk_cloth'], 1, shapeless=True)
recipe([[M['petals'], M['turf']]], M['heather'], 2, shapeless=True)
recipe([[M['sand'], M['snow']]], M['salt_block'], 2, shapeless=True)
recipe([[M['basalt'], M['emberite_ore']]], M['cinder'], 2, shapeless=True)
recipe([[M['stone'], M['lumen_shard']]], M['starstone'], 2, shapeless=True)
# lamps
recipe([[M['glass'], E], [G_, M['glass']]], M['ember_lamp'])
recipe([[M['glass'], AETHERITE.id], [G_, M['glass']]], M['aether_lamp'])
recipe([[M['glass'], VERDIGRIS.id], [G_, M['glass']]], M['verdigris_lamp'])
# tinted glass
recipe([[M['glass'], M['glowcap']]], M['green_glass'], 1, shapeless=True)
recipe([[M['glass'], M['bloom']]], M['amber_glass'], 1, shapeless=True)
recipe([[M['glass'], M['lumen_shard']]], M['violet_glass'], 1, shapeless=True)
# slabs: three in a row -> six slabs
for _full, _slab in (
    (M['stone'], M['stone_slab']), (M['cobble'], M['cobble_slab']),
    (M['planks'], M['planks_slab']), (M['cedar_planks'], M['cedar_planks_slab']),
    (M['pale_planks'], M['pale_planks_slab']), (M['dark_planks'], M['dark_planks_slab']),
    (M['bricks'], M['bricks_slab']), (M['stone_bricks'], M['stone_bricks_slab']),
    (M['sandstone'], M['sandstone_slab']), (M['slate'], M['slate_slab']),
    (M['thatch'], M['thatch_slab']), (M['shingles'], M['shingles_slab']),
    (M['polished_stone'], M['polished_stone_slab']),
):
    recipe([[_full, _full, _full]], _slab, 6)


def _match_cell(want, have):
    if want is None:
        return have is None
    if have is None:
        return False
    if want in GROUPS:
        return have in GROUPS[want]
    return want == have


def _trim(grid):
    """grid: list of rows (ids or None) -> trimmed rows."""
    rows = [r for r in grid]
    while rows and all(v is None for v in rows[0]):
        rows.pop(0)
    while rows and all(v is None for v in rows[-1]):
        rows.pop()
    if not rows:
        return []
    cols = len(rows[0])
    left = min((next((i for i, v in enumerate(r) if v is not None), cols) for r in rows))
    right = max((max((i for i, v in enumerate(r) if v is not None), default=-1) for r in rows))
    return [r[left:right + 1] for r in rows]


def match(grid):
    """grid: list of rows of item ids (or None). -> (result id, count) or None"""
    g = _trim(grid)
    if not g:
        return None
    flat = sorted([v for r in g for v in r if v is not None])
    for rows, res, shapeless in RECIPES:
        if shapeless:
            want = [v for r in rows for v in r if v is not None]
            if len(want) != len(flat):
                continue
            pool = list(flat)
            ok = True
            for w_ in want:
                hit = next((i for i, h in enumerate(pool) if _match_cell(w_, h)), None)
                if hit is None:
                    ok = False
                    break
                pool.pop(hit)
            if ok:
                return res
            continue
        if len(rows) != len(g) or len(rows[0]) != len(g[0]):
            continue
        for mirror in (False, True):
            ok = True
            for r1, r2 in zip(rows, g):
                rr = list(reversed(r1)) if mirror else r1
                if any(not _match_cell(a, b) for a, b in zip(rr, r2)):
                    ok = False
                    break
            if ok:
                return res
    return None


def recipe_needs(rows):
    """Counts of ingredients for the recipe book: {id or group: n}."""
    need = {}
    for r in rows:
        for v in r:
            if v is not None:
                need[v] = need.get(v, 0) + 1
    return need


def recipe_size(rows):
    return max(len(rows), max(len(r) for r in rows))


def name_of(v):
    if v == STONES:
        return 'any stone'
    it = ITEMS.get(v)
    return it.name if it else '?'


# ------------------------------------------------------------------ the kiln
SMELT = {
    M['verdigris_ore']: VERDIGRIS.id, M['silverine_ore']: SILVERINE.id, M['sand']: M['glass'],
    M['clay']: BRICK.id, HOPMEAT.id: ROAST.id, M['stone']: M['polished_stone'], M['heartwood']: EMBERITE.id,
}
FUEL = {EMBERITE.id: 16.0, M['heartwood']: 6.0, M['planks']: 3.0, STICK.id: 1.0, GLOOM.id: 8.0,
        M['cedar_heartwood']: 6.0, M['pale_heartwood']: 6.0, M['dark_heartwood']: 6.0,
        M['cedar_planks']: 3.0, M['pale_planks']: 3.0, M['dark_planks']: 3.0,
        M['thatch']: 2.0}
SMELT_TIME = 4.0
