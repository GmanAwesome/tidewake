"""1.4.4 lesson-island showpieces: big, extravagant builds that use every placeable block.

Everything here is computed once per process into a dict of (q, r, y) -> (mat, meta),
bucketed by chunk, and stamped by tutorial.generate_chunk after the stations and the
path. Ground-level cells on the lesson path, at the stations and around the guides are
reserved, so the lesson stays readable and walkable; arches and sky platforms may pass
over the path higher up.

Layout (hex q, r):
  Rainbow Plaza + Cosmic Clocktower ... (28, 20)   inside the lesson loop
  Bazaar ring (16 colour stalls) ..... around the plaza
  Hall of Stones ziggurat ............ (46, 24)
  Glass Conservatory dome ............ (10, 34)
  Mossback Monument (turtle statue) .. (14, 14)
  Bounce Park + Sky Funfair .......... (24, 6), platforms up at SURF+16..24
  Starwatch Observatory .............. (20, -22)
  Treehouse Grove .................... (24, 64)
  Frost Folly / Ember Forge .......... (-34, 34) / (-34, 24)
  Tidewell Sanctuary canopy .......... Lumen's court (6, -32)
  Knoll crown ........................ (10, -58)
  Path arches ........................ four spots over the path
  Block Gallery ...................... west of the plaza, one pedestal per leftover block
  Meadow plants and trees ............ scattered over open land
"""
import math

from .config import CHUNK, LAYERS, HEX
from .hexgrid import center, hex_distance, DIRS, ring as hex_ring
from . import materials as MT

M = MT.ID
SQ3 = math.sqrt(3.0)

HUES = ('rose', 'ember', 'honey', 'leaf', 'moss', 'tide', 'sky', 'indigo',
        'violet', 'orchid', 'blush', 'cocoa', 'snow', 'pearl', 'ash', 'ink')

# Not placeable by players; never expected on the island.
NOT_PLACEABLE = {'air', 'dormant_spire', 'awake_spire'}

# Peaceful lesson creatures: (kind, q, r, hover layers above ground, tether cells)
MOBS = [
    ('woolhop', 2, 30, 0, 8), ('woolhop', 6, 28, 0, 8), ('woolhop', 18, 40, 0, 8), ('woolhop', -8, 30, 0, 8),
    ('mossturtle', 18, 12, 0, 6), ('mossturtle', 10, 18, 0, 6),
    ('islekit', 20, 62, 0, 7), ('islekit', 28, 66, 0, 7), ('islekit', 24, 58, 0, 7),
    ('crystalbeetle', 40, 20, 0, 6), ('crystalbeetle', 50, 30, 0, 6), ('crystalbeetle', 44, 32, 0, 6),
    ('pebblebeak', 14, 52, 0, 6), ('pebblebeak', 2, 58, 0, 6),
    ('skyjelly', 26, 4, 10, 10), ('skyjelly', 32, 10, 14, 10), ('skyjelly', 18, 30, 12, 10),
    ('fairy', 10, 34, 3, 5), ('fairy', 8, 32, 4, 5),
    ('cloudray', 30, 20, 30, 18),
]


def _land():
    from . import tutorial as T
    return T.in_land


class Plan:
    def __init__(self, surf):
        self.S = surf
        self.cells = {}
        self.reserved = set()      # (q, r) kept clear from S+1 .. S+4

    # -- primitives -------------------------------------------------------
    def put(self, q, r, y, mat, meta=0, force=False):
        if mat is None or not (0 <= y < LAYERS):
            return
        if (q, r) in self.reserved and self.S <= y <= self.S + 4:
            return
        self.cells[(q, r, y)] = (int(mat), int(meta))

    def get(self, q, r, y):
        v = self.cells.get((q, r, y))
        return v[0] if v else None

    def col(self, q, r, y0, y1, mat):
        for y in range(y0, y1 + 1):
            self.put(q, r, y, mat)

    def disk(self, q, r, y, rad, mat):
        for dq in range(-rad, rad + 1):
            for dr in range(-rad, rad + 1):
                if hex_distance(0, 0, dq, dr) <= rad:
                    self.put(q + dq, r + dr, y, mat)

    def ring(self, q, r, y, rad, mat):
        for a, b in hex_ring(q, r, rad):
            self.put(a, b, y, mat)

    def round_cells(self, q, r, rad):
        """Cells within a round (world-space) radius, with distance and angle."""
        x0, z0 = center(q, r)
        n = int(rad) + 2
        out = []
        for dq in range(-n, n + 1):
            for dr in range(-n, n + 1):
                x, z = center(q + dq, r + dr)
                d = math.hypot(x - x0, z - z0) / (HEX * SQ3)
                if d <= rad + 0.01:
                    out.append((q + dq, r + dr, d, math.atan2(z - z0, x - x0)))
        return out


def _m(name, fallback='stone'):
    return M[name] if name in M else M[fallback]


def _hue(i, family):
    return M[f'{HUES[i % 16]}_{family}']


# --------------------------------------------------------------------------
# builds
# --------------------------------------------------------------------------
def rainbow_plaza(P, q, r):
    S = P.S
    # 16 terrazzo wedges, a pearl rim and an ink ring
    for a, b, d, ang in P.round_cells(q, r, 11.5):
        sector = int(((ang + math.pi) / (2 * math.pi)) * 16) % 16
        if d > 10.5:
            mat = M['ink_terrazzo']
        elif d > 9.5:
            mat = M['pearl_patterned_tile']
        elif d < 3.6:
            mat = M['snow_terrazzo']
        else:
            mat = _hue(sector, 'terrazzo')
        P.put(a, b, S, mat, force=True)
        for y in range(S + 1, S + 6):
            P.put(a, b, y, 0)
    # lamp posts: pewter shafts with a crystal lamp of each colour around the rim
    for i, (a, b) in enumerate(hex_ring(q, r, 10)[::max(1, len(hex_ring(q, r, 10)) // 16)][:16]):
        P.col(a, b, S + 1, S + 3, M['pewter'])
        P.put(a, b, S + 4, _hue(i, 'crystal_lamp'))
        P.put(a, b, S + 5, _hue(i, 'banner'))
    cosmic_clocktower(P, q, r)


def cosmic_clocktower(P, q, r):
    S = P.S
    bands = ['ochre_bricks', 'brass', 'ink_bricks', 'copper', 'rose_checker', 'wrought_iron',
             'sky_stripe', 'pewter', 'ink_checker', 'rose_stripe', 'brass', 'ochre_bricks']
    h = 34
    for i in range(h):
        mat = M[bands[(i // 3) % len(bands)]]
        P.ring(q, r, S + 1 + i, 3, mat)
        P.ring(q, r, S + 1 + i, 2, mat)
        for a, b in hex_ring(q, r, 1) + [(q, r)]:
            P.put(a, b, S + 1 + i, 0)
        if i in (8, 17, 26):
            P.ring(q, r, S + 1 + i, 4, M['wrought_iron'])            # balcony
            if i == 26:
                P.ring(q, r, S + 2 + i, 4, M['pale_lattice'])
    # ladder up the inside, a door gap at the foot
    for i in range(h):
        P.put(q, r, S + 1 + i, M['ladder'], 0)
    for a, b in ((q + 3, r), (q + 2, r)):
        P.put(a, b, S + 1, 0)
        P.put(a, b, S + 2, 0)
    # clock faces on six sides
    for d, (dq, dr) in enumerate(DIRS):
        fq, fr = q + dq * 3, r + dr * 3
        P.put(fq, fr, S + 22, M['snow_patterned_tile'])
        P.put(fq, fr, S + 23, M['honey_crystal_lamp'] if d % 2 == 0 else M['snow_patterned_tile'])
        P.put(fq, fr, S + 24, M['snow_patterned_tile'])
    # glass belfry, onion cap of shimmer cloud, a cosmic star on top
    for i, mat in enumerate((M['violet_glass'], M['amber_glass'], M['green_glass'], M['glass'])):
        P.ring(q, r, S + 35 + i, 3, mat)
    P.disk(q, r, S + 39, 3, M['brass'])
    P.disk(q, r, S + 40, 2, M['shimmer_cloud'])
    P.disk(q, r, S + 41, 1, M['shimmer_cloud'])
    P.put(q, r, S + 42, M['copper'])
    P.put(q, r, S + 43, M['cosmic_star'])
    P.put(q, r, S + 36, M['lumen_lamp'])


def bazaar(P, q, r):
    """Sixteen colour stalls around the plaza, each its own dyed family."""
    S = P.S
    spots = hex_ring(q, r, 14)
    step = len(spots) / 16.0
    for i in range(16):
        a, b = spots[int(i * step)]
        x0, z0 = center(q, r)
        x1, z1 = center(a, b)
        # posts
        for dq, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            P.col(a + dq, b + dr, S + 1, S + 3, M['dark_planks'] if i % 2 else M['cedar_planks'])
        P.disk(a, b, S, 1, _hue(i, 'patterned_tile'))
        P.disk(a, b, S + 4, 1, _hue(i, 'woven_panel'))
        P.put(a, b, S + 5, _hue(i, 'woven_panel'))
        P.put(a, b, S + 1, _hue(i, 'stained_glass'))     # glass counter
        P.put(a + 1, b - 1, S + 1, _hue(i, 'banner'))
    # cloth canopies between stalls
    cloths = ('linen', 'crimson_cloth', 'dusk_cloth', 'heather')
    for i, (a, b) in enumerate(hex_ring(q, r, 16)[::6]):
        P.put(a, b, S + 1, M['wattle'])
        P.put(a, b, S + 2, M[cloths[i % 4]])


def hall_of_stones(P, q, r):
    """A stepped ziggurat: every stone, brick, tile and polish in bands, ores as gems."""
    S = P.S
    stones = ['stone', 'cobble', 'slate', 'chalk', 'sandstone', 'cinder', 'salt_block', 'pale_stone',
              'basalt', 'rosestone', 'clay', 'packed_earth', 'mossy_bricks', 'carved_stone', 'mosaic',
              'polished_stone', 'polished_basalt', 'polished_rosestone', 'polished_slate', 'polished_chalk',
              'polished_sandstone', 'polished_pale_stone', 'stone_bricks', 'basalt_bricks', 'rosestone_bricks',
              'slate_bricks', 'sandstone_bricks', 'chalk_bricks', 'cinder_bricks', 'snow_bricks', 'dusk_bricks',
              'lavender_bricks', 'verdigris_bricks', 'bricks', 'stone_tiles', 'basalt_tiles', 'rosestone_tiles',
              'slate_tiles', 'sandstone_tiles', 'chalk_tiles', 'clay_tiles', 'verdigris_tiles', 'lavender_tiles',
              'starstone', 'polished_starstone', 'starstone_tiles']
    tiers = 8
    y = S + 1
    k = 0
    for t in range(tiers):
        rad = 9 - t
        for hh in range(3):
            mat = M[stones[k % len(stones)]]
            k += 1
            P.disk(q, r, y, rad, mat)
            y += 1
    # ore gems set into the tier faces
    ores = ['emberite_ore', 'verdigris_ore', 'silverine_ore', 'aetherite_ore']
    for t in range(tiers):
        rad = 9 - t
        for d, (dq, dr) in enumerate(DIRS):
            P.put(q + dq * rad, r + dr * rad, S + 2 + t * 3, M[ores[(d + t) % 4]])
    # slab staircase up the +q face, every slab kind in turn
    slabs = ['stone_slab', 'cobble_slab', 'planks_slab', 'cedar_planks_slab', 'pale_planks_slab',
             'dark_planks_slab', 'bricks_slab', 'stone_bricks_slab', 'sandstone_slab', 'slate_slab',
             'thatch_slab', 'shingles_slab', 'polished_stone_slab']
    for t in range(tiers + 1):
        sq = q + 10 - t
        P.put(sq, r, S + t * 3, M['polished_stone'])
        P.put(sq, r, S + t * 3 + 1, M[slabs[t % len(slabs)]])
        P.put(sq, r - 1, S + t * 3 + 1, M[slabs[(t + 6) % len(slabs)]])
        for yy in range(S + t * 3 + 2, S + t * 3 + 5):
            P.put(sq, r, yy, 0)
            P.put(sq, r - 1, yy, 0)
    # crown: four lamps of the old lamp kinds and a starstone tile top
    top = S + 1 + tiers * 3
    P.disk(q, r, top, 1, M['starstone_tiles'])
    for (dq, dr), lamp in zip(DIRS, ('ember_lamp', 'aether_lamp', 'verdigris_lamp', 'lumen_lamp', 'kiln', 'starstone')):
        P.put(q + dq, r + dr, top + 1, M[lamp])
    P.put(q, r, top + 1, M['plinth'])
    P.put(q, r, top + 2, M['lumen_shard'])


def conservatory(P, q, r):
    """A great stained-glass dome full of every plant."""
    S = P.S
    R = 9.0
    glass16 = [_hue(i, 'stained_glass') for i in range(16)]
    plain = [M['glass'], M['green_glass'], M['amber_glass'], M['violet_glass']]
    cells = P.round_cells(q, r, R)
    for a, b, d, ang in cells:
        P.put(a, b, S, M['leaf_terrazzo'] if d > R - 1.2 else M['turf'], force=True)
        for y in range(S + 1, S + 12):
            P.put(a, b, y, 0)
    for a, b, d, ang in cells:
        hgt = math.sqrt(max(0.0, R * R - d * d)) * 1.15
        nxt = math.sqrt(max(0.0, R * R - (d + 1.0) ** 2)) * 1.15 if d + 1.0 < R else 0.0
        y_top = S + int(round(hgt))
        y_bot = S + 1 + int(round(nxt))
        sector = int(((ang + math.pi) / (2 * math.pi)) * 16) % 16
        for y in range(y_bot, y_top + 1):
            lat = y - S
            rib = sector % 4 == 0
            if rib:
                mat = M['pale_lattice'] if lat % 2 else M['wood_lattice']
            elif lat > 8:
                mat = plain[(sector + lat) % 4]
            else:
                mat = glass16[(sector + lat // 3) % 16]
            P.put(a, b, y, mat)
    # four arched doorways
    for d in (0, 2, 3, 5):
        dq, dr = DIRS[d]
        for k in range(8, 11):
            for y in range(S + 1, S + 4):
                P.put(q + dq * k, r + dr * k, y, 0)
    # inside: a garden of every plant on matching ground
    beds = [('bloom', 'turf'), ('vine', 'mossrock'), ('sprout', 'loam'), ('glowcap', 'mossrock'),
            ('petals', 'turf'), ('berry_bush', 'turf'), ('grass', 'turf'), ('wildflower', 'turf'),
            ('mushroom', 'loam'), ('pebble', 'sand'), ('shrub', 'turf'), ('reeds', 'sand'),
            ('crystal', 'snow'), ('lumen_shard', 'ice'), ('skywheat', 'farmland'),
            ('sweetroot_crop', 'farmland'), ('berry_crop', 'farmland')]
    for i, (a, b, d, ang) in enumerate(c for c in cells if 2.5 < c[2] < R - 2.0):
        plant, ground = beds[(int((ang + math.pi) * 4) + int(d)) % len(beds)]
        P.put(a, b, S, M[ground], force=True)
        meta = 3 if plant in ('skywheat', 'sweetroot_crop', 'berry_crop') else 0
        P.put(a, b, S + 1, M[plant], meta)
    # central pool with a fountain of glass and a lamp
    for a, b, d, ang in cells:
        if d < 2.2:
            P.put(a, b, S - 1, M['stone'], force=True)
            P.put(a, b, S, M['water'], 7, force=True)
    P.col(q, r, S, S + 3, M['polished_chalk'])
    P.put(q, r, S + 4, M['lumen_lamp'])
    P.put(q, r, S + 5, M['glass'])


def mossback_monument(P, q, r):
    """A giant moss turtle statue with a garden growing on its shell."""
    S = P.S
    for a, b, d, ang in P.round_cells(q, r, 6.2):
        h = int(round(math.sqrt(max(0.0, 6.2 ** 2 - d * d)) * 0.9))
        for y in range(S + 2, S + 2 + h):
            mat = M['moss_terrazzo'] if (int(d) + y) % 3 else M['leaf_patterned_tile']
            P.put(a, b, y, mat)
        P.put(a, b, S + 2 + h, M['moss_patterned_tile'] if d > 2 else M['turf'])
        if d < 4.5 and (a * 7 + b * 3) % 3 == 0:
            P.put(a, b, S + 3 + h, M['shrub'] if (a + b) % 2 else M['bloom'])
    # legs, head and tail
    for dq, dr in ((4, -2), (-4, 2), (2, 3), (-2, -3)):
        P.col(q + dq, r + dr, S + 1, S + 2, M['sage_plaster'])
    hq, hr = q + 8, r - 1
    for y in range(S + 2, S + 6):
        P.disk(hq - 1, hr, y, 1 if y < S + 5 else 0, M['sage_plaster'])
    P.disk(hq, hr, S + 5, 1, M['sage_plaster'])
    P.put(hq + 1, hr, S + 5, M['sage_plaster'])
    P.put(hq + 1, hr - 1, S + 6, M['ink_terrazzo'])       # eyes
    P.put(hq, hr + 1, S + 6, M['ink_terrazzo'])
    P.put(q - 7, r + 1, S + 2, M['sage_plaster'])
    P.put(q - 8, r + 1, S + 2, M['sage_plaster'])
    P.disk(q, r, S, 7, M['packed_earth'])
    P.put(q, r, S + 9, M['leaf_crystal_lamp'])


def bounce_park(P, q, r):
    """Ground jelly pads and checker pavilions, with a ladder tower to the sky funfair."""
    S = P.S
    jellies = ('rose_jelly', 'tide_jelly', 'honey_jelly', 'violet_jelly')
    for i, (dq, dr) in enumerate(((0, 0), (3, -1), (-3, 1), (1, 3), (-1, -3), (4, 2), (-4, -2))):
        P.disk(q + dq, r + dr, S, 1, M[jellies[i % 4]])
    for a, b in hex_ring(q, r, 6):
        P.put(a, b, S, M['rose_checker'] if (a + b) % 2 else M['ink_checker'])
    for a, b in hex_ring(q, r, 7):
        P.put(a, b, S + 1, M['sky_stripe'] if (a - b) % 3 else M['rose_stripe'])
    # ladder tower to the platforms
    tq, tr = q + 6, r - 6
    for y in range(S + 1, S + 18):
        P.ring(tq, tr, y, 1, M['pale_planks'] if y % 4 else M['rose_stripe'])
        P.put(tq, tr, y, M['ladder'], 0)
    for y in (S + 1, S + 2):
        P.put(tq - 1, tr + 1, y, 0)
    sky_funfair(P, tq, tr, S + 17)


def sky_funfair(P, q, r, y):
    """Floating cloud islands joined by plank bridges, with a star gazebo above."""
    pads = [(q, r, 4, 'shimmer_cloud'), (q - 10, r + 6, 4, 'cloudstuff'), (q + 8, r + 8, 3, 'fluff_block'),
            (q - 4, r + 14, 3, 'shimmer_cloud')]
    for i, (a, b, rad, mat) in enumerate(pads):
        yy = y + (0, 2, -1, 4)[i]
        P.disk(a, b, yy, rad, M[mat])
        P.disk(a, b, yy - 1, rad - 1, M[mat])
        P.disk(a, b, yy - 2, max(0, rad - 2), M[mat])
        P.put(a, b, yy, M[('rose_jelly', 'honey_jelly', 'tide_jelly', 'violet_jelly')[i]])
        for (dq, dr) in DIRS[::2]:
            P.put(a + dq * rad, b + dr * rad, yy + 1, M['pale_lattice'])
    # bridges between pads
    from .tutorial import hex_line
    for (a0, b0, _, _), (a1, b1, _, _), y0, y1 in ((pads[0], pads[1], y, y + 2), (pads[0], pads[2], y, y - 1),
                                                   (pads[1], pads[3], y + 2, y + 4)):
        pts = hex_line(a0, b0, a1, b1)
        for k, (a, b) in enumerate(pts):
            yy = y0 + round((y1 - y0) * k / max(1, len(pts) - 1))
            if P.get(a, b, yy) in (None, 0):
                P.put(a, b, yy, M['pale_planks'])
            P.put(a, b, yy + 1, 0)
    # star gazebo
    gq, gr, gy = q - 4, r + 14, y + 5
    for dq, dr in DIRS[::2]:
        P.col(gq + dq * 2, gr + dr * 2, gy, gy + 3, M['ivory_plaster'])
    P.disk(gq, gr, gy + 4, 2, M['indigo_terrazzo'])
    P.disk(gq, gr, gy + 5, 1, M['indigo_patterned_tile'])
    P.put(gq, gr, gy + 6, M['cosmic_star'])
    P.put(gq, gr, gy, M['bedroll'])


def observatory(P, q, r):
    S = P.S
    for y in range(S + 1, S + 18):
        mat = M['lavender_bricks'] if y % 5 else M['dusk_bricks']
        P.ring(q, r, y, 3, mat)
        P.ring(q, r, y, 2, mat)
        for a, b in hex_ring(q, r, 1) + [(q, r)]:
            P.put(a, b, y, 0)
        P.put(q, r, y, M['ladder'], 0)
    P.put(q + 3, r, S + 1, 0)
    P.put(q + 3, r, S + 2, 0)
    P.put(q + 2, r, S + 1, 0)
    P.put(q + 2, r, S + 2, 0)
    P.disk(q, r, S + 18, 4, M['polished_starstone'])
    P.ring(q, r, S + 19, 4, M['verdigris_bricks'])
    for i in range(4):
        P.disk(q, r, S + 20 + i, 3 - i, M['starstone_tiles'] if i % 2 else M['verdigris_tiles'])
    # brass telescope pointing at the sky
    for k in range(6):
        P.put(q + 1 + k // 2, r - 1, S + 19 + k, M['brass'] if k < 5 else M['copper'])
    P.put(q - 3, r + 1, S + 19, M['aether_lamp'])
    P.disk(q, r, S, 5, M['slate_tiles'])


def treehouse_grove(P, q, r):
    """Four giant trees, each with its own wood, joined by plank walkways."""
    S = P.S
    woods = [('heartwood', 'planks', 'thatch'), ('cedar_heartwood', 'cedar_planks', 'shingles'),
             ('pale_heartwood', 'pale_planks', 'thatch'), ('dark_heartwood', 'dark_planks', 'shingles')]
    spots = [(q - 5, r - 2), (q + 5, r - 3), (q + 4, r + 5), (q - 5, r + 6)]
    deck_y = S + 9
    for (a, b), (log, plank, roof) in zip(spots, woods):
        for y in range(S + 1, S + 18):
            P.disk(a, b, y, 1 if y < S + 14 else 0, M[log])
        for y in range(S + 14, S + 21):
            rad = 4 if y < S + 19 else 2
            P.disk(a, b, y, rad, M['canopy'])
        for a2, b2 in hex_ring(a, b, 1) + [(a, b)]:
            P.put(a2, b2, S + 14, M[log])
        # deck, railing, hut
        P.disk(a, b, deck_y, 3, M[plank])
        P.ring(a, b, deck_y + 1, 3, M['wood_lattice'])
        P.ring(a, b, deck_y + 1, 2, 0)
        hq, hr = a + 2, b - 1
        P.ring(hq, hr, deck_y + 1, 1, M[plank])
        P.ring(hq, hr, deck_y + 2, 1, M[plank])
        P.disk(hq, hr, deck_y + 3, 1, M[roof])
        P.put(hq, hr, deck_y + 4, M[roof + '_slab' if roof + '_slab' in M else roof])
        P.put(hq, hr, deck_y + 1, M['bedroll'])
        P.put(hq + 1, hr, deck_y + 1, 0)
        P.put(hq + 1, hr, deck_y + 2, 0)
        P.put(a - 1, b + 1, deck_y + 2, M['lantern'])
        for y in range(S + 1, deck_y + 1):
            P.put(a - 2, b, y, M['ladder'], 0)
        P.put(a - 2, b, deck_y + 1, 0)
    from .tutorial import hex_line
    for i in range(4):
        (a0, b0), (a1, b1) = spots[i], spots[(i + 1) % 4]
        for a, b in hex_line(a0, b0, a1, b1)[2:-2]:
            P.put(a, b, deck_y, M['planks'])
            P.put(a, b, deck_y + 1, 0)
    P.put(q, r, S + 1, M['tinker_bench'])
    P.put(q + 1, r, S + 1, M['barrel'] if 'barrel' in M else M['cedar_planks'])


def frost_folly(P, q, r):
    S = P.S
    for a, b, d, ang in P.round_cells(q, r, 5.5):
        P.put(a, b, S, M['snow'], force=True)
    for d, (dq, dr) in enumerate(DIRS):
        a, b = q + dq * 4, r + dr * 4
        h = 5 + (d % 3) * 2
        for y in range(S + 1, S + 1 + h):
            P.put(a, b, y, M['ice'] if y % 3 else M['snow_bricks'])
        P.put(a, b, S + 1 + h, M['salt_block'])
    P.disk(q, r, S + 1, 1, M['polished_chalk'])
    P.put(q, r, S + 2, M['chalk_bricks'])
    P.put(q, r, S + 3, M['snow_crystal_lamp'])
    P.put(q + 1, r + 1, S + 1, M['snow_banner'])


def ember_forge(P, q, r):
    S = P.S
    for a, b, d, ang in P.round_cells(q, r, 5.0):
        P.put(a, b, S, M['cinder_bricks'] if d > 3 else M['basalt_tiles'], force=True)
    for a, b in hex_ring(q, r, 4):
        P.col(a, b, S + 1, S + 2, M['cinder'])
    for a, b in hex_ring(q, r, 4)[::3]:
        P.col(a, b, S + 3, S + 5, M['polished_basalt'])
        P.put(a, b, S + 6, M['ember_crystal_lamp'])
    P.disk(q, r, S + 6, 4, M['basalt_bricks'])
    P.disk(q, r, S + 7, 2, M['ember_patterned_tile'])
    P.put(q, r, S + 1, M['kiln'])
    P.put(q + 1, r, S + 1, M['emberite_ore'])
    for a, b in ((q + 4, r), (q + 3, r), (q + 4, r - 1)):
        P.put(a, b, S + 1, 0)
        P.put(a, b, S + 2, 0)


def tidewell_sanctuary(P, q, r):
    """A raised stained-glass canopy over Lumen's court, open on every side."""
    S = P.S
    for d, (dq, dr) in enumerate(DIRS):
        a, b = q + dq * 5, r + dr * 5
        P.col(a, b, S + 1, S + 6, M['dusk_plaster'])
        P.put(a, b, S + 7, M['violet_crystal_lamp'] if d % 2 else M['dusk_plaster'])
    for a, b, d, ang in P.round_cells(q, r, 5.6):
        sector = int(((ang + math.pi) / (2 * math.pi)) * 16) % 16
        lift = int(round(math.sqrt(max(0.0, 5.6 ** 2 - d * d)) * 0.5))
        P.put(a, b, S + 7 + lift, _hue(sector, 'stained_glass'))
    P.put(q, r, S + 11, M['shimmer_cloud'])
    for a, b in hex_ring(q, r, 6)[::4]:
        P.put(a, b, S + 1, M['violet_banner'])


def knoll_crown(P, q, r, top):
    for i, (a, b) in enumerate(hex_ring(q, r, 8)[::6]):
        P.col(a, b, top + 1, top + 5, M['carved_stone'])
        P.put(a, b, top + 6, M['polished_pale_stone'])
        P.put(a, b, top + 7, M['crystal'])
    for a, b in hex_ring(q, r, 8):
        P.put(a, b, top + 6, M['polished_pale_stone'])


def arch(P, q0, r0, q1, r1, mat, cap, banner):
    """Two legs and a lintel, spanning between (q0, r0) and (q1, r1)."""
    S = P.S
    from .tutorial import hex_line
    for a, b in ((q0, r0), (q1, r1)):
        P.col(a, b, S + 1, S + 7, mat)
    for a, b in hex_line(q0, r0, q1, r1):
        P.put(a, b, S + 8, cap)
        P.put(a, b, S + 9, mat)
    mq, mr = (q0 + q1) // 2, (r0 + r1) // 2
    P.put(mq, mr, S + 7, banner)
    P.put(mq, mr, S + 10, M['honey_crystal_lamp'])


def meadow(P, land, avoid_tree):
    """Flowers, grass and some trees across open land, deterministic."""
    S = P.S
    plants = ['grass', 'grass', 'wildflower', 'petals', 'bloom', 'shrub', 'mushroom', 'pebble', 'sprout',
              'berry_bush', 'grass', 'wildflower']
    woods = ['heartwood', 'pale_heartwood', 'cedar_heartwood', 'dark_heartwood']
    for q in range(-50, 81):
        for r in range(-76, 81):
            if not land(q, r) or (q, r) in P.reserved:
                continue
            if any((q, r, y) in P.cells for y in range(S, S + 4)):
                continue
            h = (q * 73856093 ^ r * 19349663) & 0xFFFF
            if h % 997 < 6 and not avoid_tree(q, r):
                ok = all(not any((q + dq, r + dr, y) in P.cells for y in range(S, S + 10))
                         and (q + dq, r + dr) not in P.reserved for dq, dr in [(0, 0)] + list(DIRS))
                if ok:
                    w = woods[h % 4]
                    hh = 6 + h % 4
                    P.col(q, r, S + 1, S + hh, M[w])
                    for dq, dr in [(0, 0)] + list(DIRS):
                        for y in range(S + hh - 1, S + hh + 2):
                            if not (dq == 0 and dr == 0 and y <= S + hh):
                                P.put(q + dq, r + dr, y, M['canopy'])
                    continue
            if h % 100 < 9:
                P.put(q, r, S + 1, M[plants[(h >> 4) % len(plants)]])


def block_gallery(P, q, r, used):
    """A curved colonnade of pedestals, one for each block not used elsewhere."""
    S = P.S
    want = [i for i in range(1, MT.N) if MT.NAMES[i].lower().replace(' ', '_') not in NOT_PLACEABLE
            and i not in used and i != M['water']]
    spots = []
    for rad in (4, 6, 8):
        spots += [c for c in hex_ring(q, r, rad) if c[0] <= q + 1]
    for (a, b), mid in zip(spots, want):
        P.put(a, b, S, M['polished_stone'], force=True)
        P.put(a, b, S + 1, M['plinth'])
        P.put(a, b, S + 2, mid)
    return want



def hot_air_balloon(put, q, r, y, R=7.0, hues=None):
    """A big striped hot air balloon: dyed envelope gores, ropes, a basket deck and a burner.
    `put(q, r, y, mat)` places one cell; (q, r, y) is the envelope's equator centre.
    Used by the lesson island and by the v6 sky structures."""
    hues = list(hues or HUES[:12])
    fam = ('terrazzo', 'patterned_tile', 'woven_panel')
    H = 0.85  # layer height in world units; hex spacing is SQ3
    n = int(R) + 2
    x0, z0 = center(q, r)
    # envelope: a shell, teardrop-shaped (narrower toward the bottom), vertical gores of colour
    ylo, yhi = int(-R * 1.45 / H), int(R * 1.2 / H)
    for dy in range(ylo, yhi + 1):
        wy = dy * H
        if wy >= 0:
            rad = math.sqrt(max(0.0, R * R - (wy / 1.2) ** 2))
        else:
            t = -wy / (R * 1.45)
            rad = R * math.sqrt(max(0.0, 1 - t * t)) * (1 - 0.55 * t)
        if rad < 0.6:
            if dy > 0:
                put(q, r, y + dy, M[f'{hues[0]}_terrazzo'])
            continue
        band = fam[(dy // 3) % 3] if dy % 6 == 0 else 'terrazzo'
        for dq in range(-n, n + 1):
            for dr in range(-n, n + 1):
                x, z = center(q + dq, r + dr)
                d = math.hypot(x - x0, z - z0)
                if rad - SQ3 * 0.95 < d <= rad:
                    ang = math.atan2(z - z0, x - x0)
                    gore = int(((ang + math.pi) / (2 * math.pi)) * len(hues)) % len(hues)
                    put(q + dq, r + dr, y + dy, M[f'{hues[gore]}_{band}'])
                elif d <= rad - SQ3 * 0.95 and dy == yhi - 1:
                    put(q + dq, r + dr, y + dy, M[f'{hues[(dq + dr) % len(hues)]}_terrazzo'])
    # crown cap and a mouth ring
    put(q, r, y + yhi + 1, M['brass'])
    mouth = y + ylo
    from .hexgrid import ring as _ring
    mr = max(1, int(R * 0.35))
    for a, b in _ring(q, r, mr):
        put(a, b, mouth, M['brass'])
    # burner glow in the mouth
    put(q, r, mouth, M['ember_crystal_lamp'])
    put(q, r, mouth - 1, M['wrought_iron'])
    # basket: a deck with rails, hanging below on ropes
    bh = max(4, int(R * 0.9))
    by = mouth - bh
    br = max(2, int(R * 0.3))
    for d, (dq, dr) in enumerate(DIRS):
        for k in range(1, bh):
            t = k / bh
            rq = round(dq * (mr + (br - mr) * t))
            rr = round(dr * (mr + (br - mr) * t))
            put(q + rq, r + rr, mouth - k, M['linen'] if d % 2 else M['heather'])
    for dq in range(-br, br + 1):
        for dr in range(-br, br + 1):
            if hex_distance(0, 0, dq, dr) <= br:
                put(q + dq, r + dr, by, M['cedar_planks'])
                put(q + dq, r + dr, by - 1, M['wattle'] if hex_distance(0, 0, dq, dr) == br else M['dark_planks'])
    for a, b in _ring(q, r, br):
        put(a, b, by + 1, M['wood_lattice'])
    for (dq, dr) in DIRS[::2]:
        put(q + dq * br, r + dr * br, by + 2, M['lantern'])
    put(q, r, by + 1, M['chest'])
    put(q + 1, r, by + 1, M['honey_banner'])
    return by


def windmill(P, q, r):
    S = P.S
    P.disk(q, r, S, 6, M['packed_earth'])
    for y in range(S + 1, S + 20):
        rad = 4 if y < S + 8 else 3 if y < S + 15 else 2
        P.ring(q, r, y, rad, M['ivory_plaster'] if y % 6 else M['cedar_planks'])
        for k in range(rad):
            for a, b in hex_ring(q, r, k):
                P.put(a, b, y, 0)
    P.put(q + 4, r, S + 1, 0)
    P.put(q + 4, r, S + 2, 0)
    for y in range(S + 20, S + 24):
        P.disk(q, r, y, 23 + S - y, M['shingles'])
    # sails: four long arms in the q / r plane, drawn on the -r face
    hub_q, hub_r, hub_y = q, r - 3, S + 17
    P.put(hub_q, hub_r, hub_y, M['brass'])
    for k in range(1, 12):
        for dq, dy in ((k, 0), (-k, 0), (0, k), (0, -k)):
            yy = hub_y + round(dy * SQ3 / 0.85 * 0.5) if dy else hub_y
            P.put(hub_q + dq, hub_r - 1, yy if dy == 0 else hub_y + dy * 2, M['dark_planks'])
            if k > 3:
                cloth = M['crimson_cloth'] if (k // 2) % 2 else M['linen']
                if dy == 0:
                    P.put(hub_q + dq, hub_r - 1, hub_y + (1 if dq > 0 else -1), cloth)
                else:
                    P.put(hub_q + (-1 if dy > 0 else 1), hub_r - 1, hub_y + dy * 2, cloth)
    # mill yard: sacks of grain (wheat) and a fence
    for a, b in hex_ring(q, r, 6)[::2]:
        P.put(a, b, S + 1, M['wattle'])
    for a, b in hex_ring(q, r, 5)[::5]:
        P.put(a, b, S + 1, M['skywheat'], 3)


def hedge_maze(P, q, r, R=9):
    S = P.S
    for a, b, d, ang in P.round_cells(q, r, R + 0.5):
        P.put(a, b, S, M['packed_earth'] if d > 1.5 else M['polished_chalk'], force=True)
    for ring_r in (3, 5, 7, 9):
        gap = int(((ring_r * 37) % 360))
        for a, b, d, ang in P.round_cells(q, r, ring_r + 0.5):
            if d < ring_r - 0.5:
                continue
            deg = (math.degrees(ang) + 360) % 360
            if abs(((deg - gap + 180) % 360) - 180) < 14:
                continue
            P.put(a, b, S + 1, M['canopy'])
            P.put(a, b, S + 2, M['canopy'])
            if (a + b) % 7 == 0:
                P.put(a, b, S + 3, M['bloom'])
    P.put(q, r, S + 1, M['carved_stone'])
    P.put(q, r, S + 2, M['plinth'])
    P.put(q, r, S + 3, M['cosmic_star'])


def woolhop_statue(P, q, r):
    """A giant fluffy woolhop made of fluff and cloud."""
    S = P.S
    for a, b, d, ang in P.round_cells(q, r, 6.5):
        h = int(round(math.sqrt(max(0.0, 6.5 ** 2 - d * d)) * 1.6))
        for y in range(S + 3, S + 3 + h):
            P.put(a, b, y, M['fluff_block'] if (a + b + y) % 5 else M['cloudstuff'])
    for dq, dr in ((3, -2), (-3, 2), (2, 2), (-2, -2)):
        P.col(q + dq, r + dr, S + 1, S + 3, M['ash_terrazzo'])
    hq, hr = q, r - 7
    for y in range(S + 8, S + 13):
        P.disk(hq, hr, y, 2, M['ink_terrazzo'])
    P.put(hq - 1, hr - 2, S + 11, M['snow_terrazzo'])
    P.put(hq + 1, hr - 2, S + 11, M['snow_terrazzo'])
    P.col(hq - 2, hr, S + 13, S + 15, M['ink_terrazzo'])
    P.col(hq + 2, hr, S + 13, S + 15, M['ink_terrazzo'])
    P.disk(q, r, S, 7, M['moss_terrazzo'])


def sky_castle(P, q, r, y):
    """A floating castle on a cloud, high over the island."""
    for k, rad in enumerate((11, 10, 8, 6, 3)):
        P.disk(q, r, y - k, rad, M['cloudstuff'] if k else M['shimmer_cloud'])
    P.disk(q, r, y + 1, 9, M['stone_tiles'])
    for yy in range(y + 2, y + 8):
        P.ring(q, r, yy, 8, M['stone_bricks'])
    for a, b in hex_ring(q, r, 8)[::2]:
        P.put(a, b, y + 8, M['stone_bricks'])
    for d, (dq, dr) in enumerate(DIRS):
        tq, tr = q + dq * 8, r + dr * 8
        for yy in range(y + 2, y + 14):
            P.disk(tq, tr, yy, 1, M['chalk_bricks'] if yy % 4 else M['stone_bricks'])
        P.disk(tq, tr, y + 14, 2, M['indigo_patterned_tile'])
        P.disk(tq, tr, y + 15, 1, M['indigo_patterned_tile'])
        P.put(tq, tr, y + 16, M['sky_banner'])
    for yy in range(y + 2, y + 22):
        P.ring(q, r, yy, 3, M['polished_chalk'] if yy % 5 else M['snow_bricks'])
        P.ring(q, r, yy, 2, M['polished_chalk'] if yy % 5 else M['snow_bricks'])
    for yy in range(y + 10, y + 20, 3):
        for (dq, dr) in DIRS:
            P.put(q + dq * 3, r + dr * 3, yy, M['sky_stained_glass'])
    for k in range(4):
        P.disk(q, r, y + 22 + k, 3 - k, M['sky_patterned_tile'])
    P.put(q, r, y + 26, M['sky_crystal_lamp'])


# --------------------------------------------------------------------------
_CACHE = {}


def station_blocks():
    """Blocks the hand-built lesson stations already place (read from tutorial.py)."""
    import os
    import re
    src = open(os.path.join(os.path.dirname(__file__), 'tutorial.py')).read()
    names = set(re.findall(r"M\['([a-z_]+)'\]", src)) | set(re.findall(r"_mat\('([a-z_]+)'", src))
    return {M[n] for n in names if n in M}


def plan():
    """Build every showpiece once; returns {(cq, cr): [(lq, y, lr, mat, meta), ...]}."""
    if 'buckets' in _CACHE:
        return _CACHE['buckets']
    from . import tutorial as T
    land = T.in_land
    S = T.SURF
    P = Plan(S)
    # reserve the path, its shoulders, the stations, the guides and the plaza
    for q, r in T.path_cells():
        for dq, dr in [(0, 0)] + list(DIRS):
            P.reserved.add((q + dq, r + dr))
    stations = [(0, 0, 7), (34, -9, 6), (58, 4, 5), (60, 28, 5), (38, 48, 5), (10, 60, 6),
                (-26, 41, 5), (6, -32, 4), (8, -43, 6)]
    for q, r, rad in stations:
        for dq in range(-rad, rad + 1):
            for dr in range(-rad, rad + 1):
                if hex_distance(0, 0, dq, dr) <= rad:
                    P.reserved.add((q + dq, r + dr))
    for q, r, *_ in T.NPCS:
        for dq, dr in [(0, 0)] + list(DIRS):
            P.reserved.add((q + dq, r + dr))
    for q, r, _y in T.CHESTS:
        P.reserved.add((q, r))

    rainbow_plaza(P, 28, 20)
    bazaar(P, 28, 20)
    hall_of_stones(P, 47, 22)
    conservatory(P, 10, 36)
    mossback_monument(P, 12, 12)
    bounce_park(P, 24, 4)
    observatory(P, 22, -24)
    treehouse_grove(P, 24, 66)
    frost_folly(P, -36, 36)
    ember_forge(P, -34, 24)
    tidewell_sanctuary(P, 6, -32)
    knoll_crown(P, 10, -58, S + 3)
    arch(P, 24, -3, 23, -9, M['blush_plaster'], M['rose_patterned_tile'], M['rose_banner'])
    arch(P, 56, 14, 63, 13, M['sage_plaster'], M['leaf_patterned_tile'], M['leaf_banner'])
    arch(P, 30, 50, 29, 56, M['ivory_plaster'], M['honey_patterned_tile'], M['honey_banner'])
    arch(P, -16, 39, -13, 45, M['dusk_plaster'], M['violet_patterned_tile'], M['violet_banner'])

    windmill(P, 61, -11)
    hedge_maze(P, -3, 29)
    woolhop_statue(P, 34, 39)
    sky_castle(P, -16, 18, S + 34)

    def avoid_tree(q, r):
        x, z = center(q, r)
        return z < 0 and abs(x) < 12        # keep the citadel view from spawn clear

    meadow(P, land, avoid_tree)

    used = {v[0] for v in P.cells.values()} | station_blocks()
    left = block_gallery(P, -14, 2, used)
    _CACHE['gallery'] = left

    buckets = {}
    for (q, r, y), (mat, meta) in P.cells.items():
        cq, cr = q // CHUNK, r // CHUNK
        buckets.setdefault((cq, cr), []).append((q - cq * CHUNK, y, r - cr * CHUNK, mat, meta))
    _CACHE['buckets'] = buckets
    _CACHE['plan'] = P
    return buckets


def apply(cells, meta, cq, cr):
    for lq, y, lr, mat, mt in plan().get((cq, cr), ()):
        cells[lq, y, lr] = mat
        meta[lq, y, lr] = mt


def placeable_ids():
    return [i for i in range(1, MT.N) if MT.NAMES[i].lower().replace(' ', '_') not in NOT_PLACEABLE]
