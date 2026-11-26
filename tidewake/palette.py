"""1.4.4 dyes, decorative families and unique building blocks.

Material IDs are appended after the 1.4.3 set; this module never reshuffles
earlier cells. Dye items live in items.py (ids 256+), not in the uint8 cell space.
"""

# (key, display name, rgb, craft hint used by items.py)
DYES = (
    ('snow',   'Snow Dye',   (0.96, 0.96, 0.94)),
    ('pearl',  'Pearl Dye',  (0.80, 0.80, 0.82)),
    ('ash',    'Ash Dye',    (0.50, 0.50, 0.54)),
    ('ink',    'Ink Dye',    (0.16, 0.14, 0.18)),
    ('rose',   'Rose Dye',   (0.86, 0.28, 0.36)),
    ('ember',  'Ember Dye',  (0.92, 0.42, 0.16)),
    ('honey',  'Honey Dye',  (0.96, 0.78, 0.22)),
    ('leaf',   'Leaf Dye',   (0.42, 0.72, 0.28)),
    ('moss',   'Moss Dye',   (0.30, 0.50, 0.28)),
    ('tide',   'Tide Dye',   (0.18, 0.70, 0.68)),
    ('sky',    'Sky Dye',    (0.42, 0.70, 0.94)),
    ('indigo', 'Indigo Dye', (0.28, 0.34, 0.72)),
    ('violet', 'Violet Dye', (0.58, 0.34, 0.78)),
    ('orchid', 'Orchid Dye', (0.78, 0.36, 0.70)),
    ('blush',  'Blush Dye',  (0.96, 0.62, 0.72)),
    ('cocoa',  'Cocoa Dye',  (0.48, 0.32, 0.22)),
)

# family key, display stem, kind, style, base rgb, emit, solid, yields, sound, side_mul
FAMILIES = (
    ('patterned_tile', 'Patterned Tile', 'full',  'patterned', (0.78, 0.76, 0.72), 0.0,  True,  (1, 0, 0, 0), 'stone', 0.90),
    ('terrazzo',       'Terrazzo',       'full',  'terrazzo',  (0.86, 0.84, 0.80), 0.0,  True,  (1, 0, 0, 0), 'stone', 0.92),
    ('woven_panel',    'Woven Panel',    'full',  'woven',     (0.72, 0.64, 0.50), 0.0,  True,  (0, 0, 0, 1), 'wood',  0.88),
    ('stained_glass',  'Stained Glass',  'glass', 'stain',     (0.70, 0.82, 0.90), 0.12, True,  (0, 0, 0, 0), 'glass', 0.95),
    ('crystal_lamp',   'Crystal Lamp',   'full',  'crystal_lamp', (0.90, 0.92, 1.00), 1.0, True, (0, 0, 1, 0), 'glass', 0.85),
    ('banner',         'Banner',         'deco',  'banner',    (0.86, 0.40, 0.40), 0.0,  False, (0, 0, 0, 1), 'puff',  0.80),
)


def _mix(a, b, t):
    return tuple(max(0.0, min(1.0, a[i] * (1.0 - t) + b[i] * t)) for i in range(3))


def _shade(rgb, k):
    return tuple(max(0.0, min(1.0, c * k)) for c in rgb)


def materials():
    """Tuples in the materials._M format, ready to append."""
    out = []
    # ---- dyeable families (16 colours each)
    for key, stem, kind, _style, base, emit, solid, yields, sound, side_mul in FAMILIES:
        for dk, dname, dcol in DYES:
            tint = _mix(base, dcol, 0.62 if key != 'stained_glass' else 0.80)
            if key == 'crystal_lamp':
                tint = _mix((1.0, 1.0, 1.0), dcol, 0.55)
                emit_v = 1.0
            elif key == 'stained_glass':
                emit_v = 0.10
            else:
                emit_v = emit
            side = _shade(tint, side_mul)
            name = f'{dname[:-4]} {stem}'
            out.append((name, kind, tint, side, emit_v, solid, yields, sound))

    # ---- plaster, metal, lattice, extra bricks
    solids = [
        ('Ivory Plaster',  'full', (0.94, 0.90, 0.84), (0.88, 0.84, 0.78), 0.0, True, (1, 0, 0, 0), 'soft'),
        ('Blush Plaster',  'full', (0.90, 0.72, 0.74), (0.82, 0.64, 0.66), 0.0, True, (1, 0, 0, 0), 'soft'),
        ('Sage Plaster',   'full', (0.70, 0.78, 0.68), (0.60, 0.70, 0.58), 0.0, True, (1, 0, 0, 0), 'soft'),
        ('Dusk Plaster',   'full', (0.46, 0.44, 0.56), (0.38, 0.36, 0.48), 0.0, True, (1, 0, 0, 0), 'soft'),
        ('Pewter',         'full', (0.62, 0.64, 0.68), (0.50, 0.52, 0.56), 0.0, True, (1, 0, 0, 0), 'stone'),
        ('Brass',          'full', (0.82, 0.66, 0.32), (0.70, 0.54, 0.24), 0.08, True, (1, 0, 0, 0), 'stone'),
        ('Copper',         'full', (0.78, 0.42, 0.28), (0.66, 0.34, 0.22), 0.0, True, (1, 0, 0, 0), 'stone'),
        ('Wrought Iron',   'full', (0.28, 0.28, 0.30), (0.20, 0.20, 0.22), 0.0, True, (1, 0, 0, 0), 'stone'),
        ('Ochre Bricks',   'full', (0.78, 0.52, 0.28), (0.68, 0.44, 0.22), 0.0, True, (1, 0, 0, 0), 'stone'),
        ('Ink Bricks',     'full', (0.28, 0.26, 0.32), (0.22, 0.20, 0.26), 0.0, True, (1, 0, 0, 0), 'stone'),
        ('Wood Lattice',   'glass', (0.78, 0.60, 0.42), (0.70, 0.52, 0.36), 0.0, True, (0, 0, 0, 1), 'wood'),
        ('Pale Lattice',   'glass', (0.90, 0.84, 0.70), (0.82, 0.76, 0.62), 0.0, True, (0, 0, 0, 1), 'wood'),
        # fun unique
        ('Rose Jelly',     'full', (0.92, 0.42, 0.58), (0.80, 0.32, 0.48), 0.20, True, (0, 0, 0, 0), 'puff'),
        ('Tide Jelly',     'full', (0.30, 0.82, 0.80), (0.22, 0.70, 0.68), 0.20, True, (0, 0, 0, 0), 'puff'),
        ('Honey Jelly',    'full', (0.96, 0.78, 0.30), (0.86, 0.66, 0.22), 0.20, True, (0, 0, 0, 0), 'puff'),
        ('Violet Jelly',   'full', (0.62, 0.40, 0.86), (0.50, 0.30, 0.74), 0.20, True, (0, 0, 0, 0), 'puff'),
        ('Ink Checker',    'full', (0.18, 0.16, 0.20), (0.90, 0.90, 0.88), 0.0, True, (1, 0, 0, 0), 'stone'),
        ('Rose Checker',   'full', (0.82, 0.32, 0.40), (0.96, 0.90, 0.88), 0.0, True, (1, 0, 0, 0), 'stone'),
        ('Rose Stripe',    'full', (0.90, 0.36, 0.44), (0.98, 0.94, 0.92), 0.0, True, (0, 0, 0, 0), 'stone'),
        ('Sky Stripe',     'full', (0.36, 0.62, 0.90), (0.98, 0.94, 0.92), 0.0, True, (0, 0, 0, 0), 'stone'),
        ('Shimmer Cloud',  'full', (0.90, 0.94, 1.00), (0.78, 0.84, 0.98), 0.35, True, (0, 1, 1, 0), 'puff'),
        ('Cosmic Star',    'full', (0.18, 0.14, 0.40), (0.10, 0.08, 0.24), 1.0,  True, (0, 0, 2, 0), 'glass'),
    ]
    out.extend(solids)
    return out


def dyed_name(family_stem, dye_key):
    dname = next(n for k, n, _ in DYES if k == dye_key)
    return f'{dname[:-4]} {family_stem}'


def id_key(name):
    return name.lower().replace(' ', '_')


def extras():
    """Lights, deco parts, bounce names, hardness — keyed by material name."""
    lights = {}
    parts = {}
    for dk, dname, dcol in DYES:
        lamp = dyed_name('Crystal Lamp', dk)
        lights[lamp] = (_mix((1.0, 1.0, 1.0), dcol, 0.55), 12.0)
        banner = dyed_name('Banner', dk)
        parts[banner] = [
            (0.06, 0.55, 1.05, False),   # pole
            (0.42, 0.48, 0.92, True),    # flag
            (0.28, 0.20, 0.50, True),    # hang
        ]
    lights['Shimmer Cloud'] = ((0.80, 0.88, 1.00), 5.0)
    lights['Cosmic Star'] = ((0.55, 0.45, 1.00), 14.0)
    bounce = ['Rose Jelly', 'Tide Jelly', 'Honey Jelly', 'Violet Jelly']
    hard = {
        'Pewter': (3.4, 'pick', 1), 'Brass': (3.4, 'pick', 1),
        'Copper': (3.2, 'pick', 1), 'Wrought Iron': (4.0, 'pick', 1),
        'Cosmic Star': (3.6, 'pick', 1),
        'Wood Lattice': (1.6, 'axe', 0), 'Pale Lattice': (1.6, 'axe', 0),
    }
    return {'lights': lights, 'parts': parts, 'bounce': bounce, 'hard': hard}


def family_keys():
    """id_key prefixes for each dyeable family, in order."""
    return [id_key(dyed_name(stem, 'snow'))[:-len('_snow') + 0] if False else
            id_key(stem.replace(' ', '_') if False else stem)
            for _k, stem, *_ in FAMILIES]
