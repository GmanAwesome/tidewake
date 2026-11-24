"""Every kind of cell in Tidewake, the four elements, and the forms you can tune.

Nothing is mined or crafted. You *gather* a cell back into the elements it is made of,
and you *shape* new cells by tuning a chord of one or two elements.
"""
import numpy as np

STONE_E, WATER_E, LIGHT_E, GROWTH_E = range(4)
ELEMENTS = ['Stone', 'Water', 'Light', 'Growth']
ELEMENT_COLORS = [(0.80, 0.72, 0.62), (0.42, 0.70, 0.95), (1.00, 0.84, 0.45), (0.52, 0.82, 0.48)]

# kind: 'full' = opaque hex prism; 'water'; 'deco' = small non-solid shapes built from parts
# parts: (radius scale, y0, y1, colour) in fractions of a cell
_M = [
    # name          kind    top colour            side colour            emit  solid yields(S,W,L,G)  sound
    ('Air',         'air',  (0, 0, 0),            (0, 0, 0),             0.0, False, (0, 0, 0, 0), None),
    ('Stone',       'full', (0.80, 0.78, 0.72),   (0.74, 0.71, 0.66),    0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Loam',        'full', (0.58, 0.45, 0.36),   (0.55, 0.42, 0.34),    0.0, True,  (1, 0, 0, 0), 'soft'),
    ('Turf',        'full', (0.55, 0.78, 0.42),   (0.55, 0.42, 0.34),    0.0, True,  (1, 0, 0, 1), 'soft'),
    ('Sand',        'full', (0.94, 0.86, 0.68),   (0.90, 0.81, 0.62),    0.0, True,  (1, 0, 0, 0), 'sand'),
    ('Snow',        'full', (0.95, 0.97, 1.00),   (0.88, 0.91, 0.96),    0.0, True,  (0, 1, 0, 0), 'sand'),
    ('Ice',         'full', (0.72, 0.88, 0.97),   (0.62, 0.80, 0.93),    0.0, True,  (0, 1, 0, 0), 'glass'),
    ('Basalt',      'full', (0.33, 0.35, 0.42),   (0.27, 0.29, 0.35),    0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Rosestone',   'full', (0.93, 0.66, 0.58),   (0.90, 0.62, 0.55),    0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Heartwood',   'full', (0.66, 0.52, 0.40),   (0.52, 0.38, 0.30),    0.0, True,  (0, 0, 0, 2), 'wood'),
    ('Canopy',      'full', (0.40, 0.68, 0.38),   (0.36, 0.62, 0.35),    0.0, True,  (0, 0, 0, 1), 'leaf'),
    ('Water',       'water', (0.36, 0.66, 0.86),  (0.32, 0.60, 0.82),    0.0, False, (0, 1, 0, 0), 'water'),
    ('Crystal',     'deco', (0.66, 0.88, 1.00),   (0.55, 0.80, 0.98),    0.9, False, (1, 0, 1, 0), 'glass'),
    ('Vine',        'deco', (0.34, 0.62, 0.34),   (0.30, 0.56, 0.31),    0.0, False, (0, 1, 0, 1), 'leaf'),
    ('Bloom',       'deco', (1.00, 0.62, 0.78),   (0.45, 0.70, 0.40),    0.7, False, (0, 0, 1, 1), 'leaf'),
    ('Clay',        'full', (0.86, 0.54, 0.40),   (0.80, 0.48, 0.36),    0.0, True,  (1, 1, 0, 0), 'soft'),
    ('Mossrock',    'full', (0.46, 0.68, 0.42),   (0.62, 0.66, 0.56),    0.0, True,  (1, 0, 0, 1), 'stone'),
    ('Cloudstuff',  'full', (0.99, 0.98, 1.00),   (0.93, 0.93, 0.99),    0.15, True, (0, 1, 1, 0), 'puff'),
    ('Lantern',     'deco', (1.00, 0.86, 0.52),   (1.00, 0.80, 0.45),    1.0, False, (0, 0, 1, 0), 'glass'),
    ('Sprout',      'deco', (0.56, 0.86, 0.44),   (0.44, 0.72, 0.36),    0.0, False, (0, 0, 0, 1), 'leaf'),
    ('Glowcap',     'deco', (0.52, 0.96, 0.86),   (0.92, 0.90, 0.84),    0.85, False, (0, 0, 1, 1), 'leaf'),
    ('Plinth',      'full', (0.76, 0.74, 0.84),   (0.66, 0.64, 0.76),    0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Dormant Spire', 'full', (0.44, 0.42, 0.56), (0.38, 0.36, 0.50),    0.0, True,  (0, 0, 0, 0), 'stone'),
    ('Awake Spire', 'full', (0.90, 0.86, 1.00),   (0.80, 0.76, 0.98),    0.45, True,  (0, 0, 0, 0), 'glass'),
    ('Lumen Shard', 'deco', (0.80, 0.68, 1.00),   (0.72, 0.60, 0.98),    0.9, False, (0, 0, 2, 0), 'glass'),
    ('Petals',      'deco', (1.00, 0.96, 0.80),   (0.45, 0.70, 0.40),    0.0, False, (0, 0, 0, 1), 'leaf'),
]

NAMES = [m[0] for m in _M]
ID = {m[0].lower().replace(' ', '_'): i for i, m in enumerate(_M)}
N = len(_M)
KIND = [m[1] for m in _M]
TOP = np.array([m[2] for m in _M], dtype=np.float32)
SIDE = np.array([m[3] for m in _M], dtype=np.float32)
EMIT = np.array([m[4] for m in _M], dtype=np.float32)
SOLID = np.array([m[5] for m in _M], dtype=bool)
YIELDS = [m[6] for m in _M]
SOUND = [m[7] for m in _M]

OPAQUE = np.array([k == 'full' for k in KIND], dtype=bool)      # hides neighbouring faces
IS_WATER = np.array([k == 'water' for k in KIND], dtype=bool)
IS_DECO = np.array([k == 'deco' for k in KIND], dtype=bool)
GATHERABLE = np.array([k != 'air' and m[0] not in ('Dormant Spire', 'Awake Spire') for k, m in zip(KIND, _M)])

# shapes of the small cells: list of (radius scale, y0, y1, use_top_colour)
PARTS = {
    ID['crystal']: [(0.42, 0.0, 0.72, True), (0.24, 0.72, 1.05, True)],
    ID['vine']: [(0.78, 0.0, 1.0, True)],
    ID['bloom']: [(0.07, 0.0, 0.46, False), (0.20, 0.30, 0.40, False), (0.36, 0.44, 0.52, True), (0.13, 0.52, 0.60, 'core')],
    ID['lantern']: [(0.18, 0.15, 0.22, False), (0.30, 0.22, 0.72, True), (0.16, 0.72, 0.80, False)],
    ID['sprout']: [(0.07, 0.0, 0.38, False), (0.22, 0.32, 0.50, True)],
    ID['glowcap']: [(0.13, 0.0, 0.62, False), (0.56, 0.60, 0.86, True)],
    ID['lumen_shard']: [(0.30, 0.45, 1.0, True), (0.16, 0.12, 0.45, True)],
    ID['petals']: [(0.05, 0.0, 0.30, False), (0.24, 0.30, 0.36, True), (0.09, 0.36, 0.42, 'core')],
}

# point-light colour and radius (world units) for glowing cells
LIGHTS = {
    ID['crystal']: ((0.45, 0.80, 1.0), 7.0),
    ID['bloom']: ((1.0, 0.55, 0.75), 5.0),
    ID['lantern']: ((1.0, 0.78, 0.45), 11.0),
    ID['glowcap']: ((0.40, 1.0, 0.85), 6.0),
    ID['awake_spire']: ((0.80, 0.70, 1.0), 16.0),
    ID['lumen_shard']: ((0.70, 0.55, 1.0), 6.0),
    ID['cloudstuff']: ((0.9, 0.9, 1.0), 3.0),
}

# ---- realms (biomes) -----------------------------------------------------------
REALMS = ['Meadow Isles', 'Amberwood', 'Rose Mesas', 'Frostglass', 'Basalt Steps', 'Mossfen', 'Duneglass',
          'Lumen Grove']
REALM_TURF = np.array([(0.56, 0.80, 0.44), (0.82, 0.76, 0.46), (0.72, 0.78, 0.48), (0.93, 0.96, 1.0),
                       (0.47, 0.66, 0.47), (0.40, 0.62, 0.36), (0.88, 0.82, 0.58), (0.62, 0.50, 0.86)], np.float32)
REALM_CANOPY = np.array([(0.42, 0.70, 0.40), (0.93, 0.66, 0.38), (0.62, 0.74, 0.40), (0.48, 0.66, 0.62),
                         (0.38, 0.58, 0.40), (0.50, 0.72, 0.42), (0.78, 0.80, 0.46), (0.84, 0.56, 0.92)], np.float32)
ROSE_BANDS = np.array([(0.93, 0.64, 0.56), (0.97, 0.80, 0.67), (0.84, 0.54, 0.52), (0.98, 0.88, 0.76),
                       (0.90, 0.70, 0.60)], np.float32)
PETAL_COLORS = np.array([(1.0, 0.96, 0.80), (1.0, 0.84, 0.40), (0.70, 0.78, 1.0), (1.0, 0.70, 0.82)], np.float32)

# ---- tuning: chord of elements -> form -----------------------------------------
# a chord is a sorted tuple of 1 or 2 element indices
FORMS = {
    (STONE_E,): ID['stone'],
    (WATER_E,): ID['water'],
    (LIGHT_E,): ID['lantern'],
    (GROWTH_E,): ID['sprout'],
    (STONE_E, WATER_E): ID['clay'],
    (STONE_E, LIGHT_E): ID['crystal'],
    (STONE_E, GROWTH_E): ID['mossrock'],
    (WATER_E, LIGHT_E): ID['cloudstuff'],
    (WATER_E, GROWTH_E): ID['vine'],
    (LIGHT_E, GROWTH_E): ID['bloom'],
}
FORM_HINTS = {
    ID['stone']: 'a plain building cell',
    ID['water']: 'flows, falls and pools',
    ID['lantern']: 'a warm hanging light',
    ID['sprout']: 'grows into a tree on turf',
    ID['clay']: 'soft terracotta for building',
    ID['crystal']: 'grows taller in the dusk tide',
    ID['mossrock']: 'slowly greens the stone around it',
    ID['cloudstuff']: 'springy: bounce on it',
    ID['vine']: 'creeps down cliffs; climb it',
    ID['bloom']: 'glowing flowers that spread in the light',
}
FORM_LIST = list(FORMS.keys())


def chord_cost(chord):
    cost = [0, 0, 0, 0]
    for e in chord:
        cost[e] += 1
    return cost
