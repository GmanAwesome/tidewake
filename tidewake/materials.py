"""Every kind of cell in Tidewake.

Cells are mined (hold the mouse), drop items, and items are placed or crafted.
New cells are only ever appended, so old saves keep their meaning.
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
    # ---- 1.1: blocks you craft, ores you mine
    ('Planks',      'full', (0.86, 0.68, 0.48),   (0.78, 0.60, 0.42),    0.0, True,  (0, 0, 0, 1), 'wood'),
    ('Tinker Bench', 'full', (0.92, 0.74, 0.50),  (0.62, 0.44, 0.32),    0.0, True,  (0, 0, 0, 1), 'wood'),
    ('Kiln',        'full', (0.98, 0.62, 0.38),   (0.58, 0.54, 0.56),    0.25, True, (1, 0, 0, 0), 'stone'),
    ('Chest',       'full', (0.80, 0.56, 0.36),   (0.70, 0.46, 0.30),    0.0, True,  (0, 0, 0, 1), 'wood'),
    ('Glass',       'glass', (0.84, 0.94, 1.00),  (0.80, 0.92, 1.00),    0.05, True, (0, 0, 0, 0), 'glass'),
    ('Bricks',      'full', (0.82, 0.46, 0.40),   (0.74, 0.40, 0.36),    0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Fluff Block', 'full', (0.99, 0.95, 0.90),   (0.95, 0.90, 0.86),    0.0, True,  (0, 0, 0, 0), 'puff'),
    ('Bedroll',     'deco', (0.94, 0.52, 0.56),   (0.99, 0.95, 0.90),    0.0, False, (0, 0, 0, 0), 'puff'),
    ('Glowstick',   'deco', (1.00, 0.78, 0.40),   (0.60, 0.44, 0.30),    1.0, False, (0, 0, 0, 0), 'wood'),
    ('Berry Bush',  'deco', (0.36, 0.62, 0.40),   (0.36, 0.62, 0.40),    0.0, False, (0, 0, 0, 1), 'leaf'),
    ('Emberite Ore', 'full', (0.98, 0.52, 0.30),  (0.40, 0.38, 0.42),    0.30, True, (1, 0, 0, 0), 'stone'),
    ('Verdigris Ore', 'full', (0.38, 0.86, 0.72), (0.58, 0.60, 0.60),    0.12, True, (1, 0, 0, 0), 'stone'),
    ('Silverine Ore', 'full', (0.88, 0.92, 1.00), (0.56, 0.56, 0.64),    0.20, True, (1, 0, 0, 0), 'stone'),
    ('Aetherite Ore', 'full', (0.80, 0.56, 1.00), (0.42, 0.38, 0.52),    0.60, True, (1, 0, 0, 0), 'glass'),
    ('Polished Stone', 'full', (0.90, 0.88, 0.84), (0.80, 0.78, 0.74),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Mossy Bricks', 'full', (0.56, 0.70, 0.46),  (0.68, 0.48, 0.42),    0.0, True,  (1, 0, 0, 1), 'stone'),
    ('Lumen Lamp',  'full', (1.00, 0.92, 0.70),   (0.98, 0.84, 0.60),    1.0, True,  (0, 0, 1, 0), 'glass'),
    # ---- 1.4: doors and ladders (not full cubes; collision is special-cased)
    ('Door',        'deco', (0.86, 0.68, 0.48),   (0.62, 0.44, 0.30),    0.0, False, (0, 0, 0, 1), 'wood'),
    ('Ladder',      'deco', (0.78, 0.58, 0.38),   (0.70, 0.50, 0.32),    0.0, False, (0, 0, 0, 1), 'wood'),
    # ---- 1.4 phase 2b: woods, stone families, bricks, tiles, lamps, slabs, glass
    ('Cedar Heartwood', 'full', (0.48, 0.30, 0.22),  (0.36, 0.22, 0.16),   0.0, True,  (0, 0, 0, 2), 'wood'),
    ('Pale Heartwood',  'full', (0.86, 0.78, 0.62),  (0.74, 0.66, 0.50),   0.0, True,  (0, 0, 0, 2), 'wood'),
    ('Dark Heartwood',  'full', (0.36, 0.24, 0.18),  (0.26, 0.16, 0.12),   0.0, True,  (0, 0, 0, 2), 'wood'),
    ('Cedar Planks',    'full', (0.64, 0.40, 0.28),  (0.56, 0.34, 0.24),   0.0, True,  (0, 0, 0, 1), 'wood'),
    ('Pale Planks',     'full', (0.92, 0.86, 0.70),  (0.86, 0.78, 0.62),   0.0, True,  (0, 0, 0, 1), 'wood'),
    ('Dark Planks',     'full', (0.48, 0.32, 0.24),  (0.40, 0.26, 0.20),   0.0, True,  (0, 0, 0, 1), 'wood'),
    ('Cobble',          'full', (0.62, 0.60, 0.56),  (0.56, 0.54, 0.50),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Slate',           'full', (0.40, 0.44, 0.50),  (0.34, 0.38, 0.44),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Chalk',           'full', (0.94, 0.93, 0.88),  (0.88, 0.86, 0.80),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Sandstone',       'full', (0.86, 0.72, 0.48),  (0.78, 0.64, 0.42),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Cinder',          'full', (0.28, 0.24, 0.24),  (0.22, 0.18, 0.18),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Starstone',       'full', (0.22, 0.18, 0.36),  (0.16, 0.14, 0.28),   0.18, True, (1, 0, 1, 0), 'stone'),
    ('Salt Block',      'full', (0.96, 0.96, 0.94),  (0.90, 0.92, 0.90),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Pale Stone',      'full', (0.86, 0.86, 0.84),  (0.78, 0.78, 0.76),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Polished Basalt', 'full', (0.40, 0.42, 0.48),  (0.32, 0.34, 0.40),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Polished Rosestone', 'full', (0.96, 0.74, 0.68), (0.90, 0.66, 0.60), 0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Polished Slate',  'full', (0.50, 0.54, 0.60),  (0.42, 0.46, 0.52),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Polished Chalk',  'full', (0.98, 0.97, 0.94),  (0.92, 0.90, 0.86),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Polished Sandstone', 'full', (0.92, 0.80, 0.58), (0.86, 0.74, 0.52), 0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Polished Starstone', 'full', (0.30, 0.26, 0.48), (0.24, 0.20, 0.40), 0.22, True, (1, 0, 1, 0), 'stone'),
    ('Polished Pale Stone', 'full', (0.94, 0.94, 0.92), (0.86, 0.86, 0.84), 0.0, True, (1, 0, 0, 0), 'stone'),
    ('Stone Bricks',    'full', (0.76, 0.74, 0.68),  (0.68, 0.66, 0.60),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Basalt Bricks',   'full', (0.36, 0.38, 0.44),  (0.30, 0.32, 0.38),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Rosestone Bricks','full', (0.90, 0.60, 0.52),  (0.82, 0.52, 0.46),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Slate Bricks',    'full', (0.44, 0.48, 0.54),  (0.38, 0.42, 0.48),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Sandstone Bricks','full', (0.84, 0.68, 0.44),  (0.76, 0.60, 0.38),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Chalk Bricks',    'full', (0.92, 0.90, 0.84),  (0.84, 0.82, 0.76),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Cinder Bricks',   'full', (0.34, 0.28, 0.26),  (0.28, 0.22, 0.20),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Snow Bricks',     'full', (0.94, 0.96, 0.98),  (0.86, 0.88, 0.92),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Dusk Bricks',     'full', (0.40, 0.42, 0.62),  (0.34, 0.36, 0.54),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Lavender Bricks', 'full', (0.72, 0.58, 0.78),  (0.64, 0.50, 0.70),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Verdigris Bricks','full', (0.32, 0.70, 0.62),  (0.26, 0.62, 0.54),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Stone Tiles',     'full', (0.78, 0.76, 0.72),  (0.70, 0.68, 0.64),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Basalt Tiles',    'full', (0.38, 0.40, 0.46),  (0.32, 0.34, 0.40),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Rosestone Tiles', 'full', (0.94, 0.68, 0.62),  (0.86, 0.60, 0.54),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Slate Tiles',     'full', (0.46, 0.50, 0.56),  (0.40, 0.44, 0.50),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Sandstone Tiles', 'full', (0.88, 0.74, 0.52),  (0.80, 0.66, 0.46),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Chalk Tiles',     'full', (0.96, 0.95, 0.90),  (0.88, 0.86, 0.80),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Clay Tiles',      'full', (0.84, 0.50, 0.38),  (0.76, 0.44, 0.32),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Starstone Tiles', 'full', (0.28, 0.22, 0.42),  (0.22, 0.18, 0.34),   0.16, True, (1, 0, 1, 0), 'stone'),
    ('Verdigris Tiles', 'full', (0.30, 0.72, 0.64),  (0.24, 0.64, 0.56),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Lavender Tiles',  'full', (0.76, 0.62, 0.82),  (0.68, 0.54, 0.74),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Thatch',          'full', (0.82, 0.68, 0.36),  (0.72, 0.58, 0.28),   0.0, True,  (0, 0, 0, 1), 'leaf'),
    ('Shingles',        'full', (0.70, 0.38, 0.32),  (0.62, 0.32, 0.28),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Carved Stone',    'full', (0.84, 0.80, 0.72),  (0.74, 0.70, 0.64),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Mosaic',          'full', (0.70, 0.66, 0.72),  (0.62, 0.58, 0.64),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Packed Earth',    'full', (0.62, 0.48, 0.34),  (0.56, 0.42, 0.30),   0.0, True,  (1, 0, 0, 0), 'soft'),
    ('Wattle',          'full', (0.78, 0.68, 0.50),  (0.70, 0.60, 0.44),   0.0, True,  (0, 0, 0, 1), 'wood'),
    ('Linen',           'full', (0.90, 0.86, 0.76),  (0.82, 0.78, 0.68),   0.0, True,  (0, 0, 0, 0), 'puff'),
    ('Crimson Cloth',   'full', (0.72, 0.22, 0.26),  (0.62, 0.16, 0.20),   0.0, True,  (0, 0, 0, 0), 'puff'),
    ('Dusk Cloth',      'full', (0.32, 0.30, 0.48),  (0.26, 0.24, 0.40),   0.0, True,  (0, 0, 0, 0), 'puff'),
    ('Heather',         'full', (0.62, 0.48, 0.70),  (0.42, 0.50, 0.36),   0.0, True,  (0, 0, 0, 1), 'soft'),
    ('Ember Lamp',      'full', (1.00, 0.62, 0.32),  (0.70, 0.40, 0.28),   1.0, True,  (0, 0, 1, 0), 'glass'),
    ('Aether Lamp',     'full', (0.78, 0.56, 1.00),  (0.48, 0.36, 0.70),   1.0, True,  (0, 0, 1, 0), 'glass'),
    ('Verdigris Lamp',  'full', (0.40, 0.92, 0.78),  (0.30, 0.58, 0.52),   1.0, True,  (0, 0, 1, 0), 'glass'),
    ('Green Glass',     'glass', (0.55, 0.90, 0.62), (0.45, 0.84, 0.55),  0.04, True,  (0, 0, 0, 0), 'glass'),
    ('Amber Glass',     'glass', (1.00, 0.82, 0.42), (0.96, 0.74, 0.32),  0.04, True,  (0, 0, 0, 0), 'glass'),
    ('Violet Glass',    'glass', (0.72, 0.52, 0.96), (0.62, 0.42, 0.90),  0.04, True,  (0, 0, 0, 0), 'glass'),
    ('Stone Slab',      'slab', (0.80, 0.78, 0.72),  (0.74, 0.71, 0.66),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Cobble Slab',     'slab', (0.62, 0.60, 0.56),  (0.56, 0.54, 0.50),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Planks Slab',     'slab', (0.86, 0.68, 0.48),  (0.78, 0.60, 0.42),   0.0, True,  (0, 0, 0, 1), 'wood'),
    ('Cedar Planks Slab','slab', (0.64, 0.40, 0.28), (0.56, 0.34, 0.24),   0.0, True,  (0, 0, 0, 1), 'wood'),
    ('Pale Planks Slab','slab', (0.92, 0.86, 0.70),  (0.86, 0.78, 0.62),   0.0, True,  (0, 0, 0, 1), 'wood'),
    ('Dark Planks Slab','slab', (0.48, 0.32, 0.24),  (0.40, 0.26, 0.20),   0.0, True,  (0, 0, 0, 1), 'wood'),
    ('Bricks Slab',     'slab', (0.82, 0.46, 0.40),  (0.74, 0.40, 0.36),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Stone Bricks Slab','slab', (0.76, 0.74, 0.68), (0.68, 0.66, 0.60),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Sandstone Slab',  'slab', (0.86, 0.72, 0.48),  (0.78, 0.64, 0.42),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Slate Slab',      'slab', (0.40, 0.44, 0.50),  (0.34, 0.38, 0.44),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Thatch Slab',     'slab', (0.82, 0.68, 0.36),  (0.72, 0.58, 0.28),   0.0, True,  (0, 0, 0, 1), 'leaf'),
    ('Shingles Slab',   'slab', (0.70, 0.38, 0.32),  (0.62, 0.32, 0.28),   0.0, True,  (1, 0, 0, 0), 'stone'),
    ('Polished Stone Slab','slab', (0.90, 0.88, 0.84), (0.80, 0.78, 0.74), 0.0, True, (1, 0, 0, 0), 'stone'),
    # ---- 1.4 phase 3: glimmer stations
    ('Waystone',      'full', (0.86, 0.80, 0.98),  (0.62, 0.56, 0.78),   0.55, True, (0, 0, 1, 0), 'stone'),
    ('Glimmer Font',  'full', (1.00, 0.90, 0.58),  (0.72, 0.62, 0.78),   0.85, True, (0, 0, 1, 0), 'glass'),
    ('Farmland',      'full', (0.52, 0.38, 0.26),  (0.48, 0.36, 0.24),   0.0, True,  (1, 0, 0, 0), 'soft'),
    ('Skywheat',      'deco', (0.82, 0.72, 0.38),  (0.46, 0.62, 0.32),   0.0, False, (0, 0, 0, 1), 'leaf'),
    ('Sweetroot Crop','deco', (0.62, 0.48, 0.30),  (0.40, 0.62, 0.34),   0.0, False, (0, 0, 0, 1), 'leaf'),
    ('Berry Crop',    'deco', (0.36, 0.62, 0.40),  (0.36, 0.62, 0.40),   0.0, False, (0, 0, 0, 1), 'leaf'),
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
IS_GLASS = np.array([k == 'glass' for k in KIND], dtype=bool)
IS_WATER = np.array([k == 'water' for k in KIND], dtype=bool)
IS_DECO = np.array([k == 'deco' for k in KIND], dtype=bool)
IS_SLAB = np.array([k == 'slab' for k in KIND], dtype=bool)
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
    ID['bedroll']: [(0.80, 0.0, 0.16, False), (0.62, 0.16, 0.30, True), (0.26, 0.30, 0.42, False)],
    ID['glowstick']: [(0.07, 0.0, 0.62, False), (0.13, 0.62, 0.86, True)],
    ID['berry_bush']: [(0.10, 0.0, 0.20, False), (0.52, 0.18, 0.62, True), (0.30, 0.62, 0.78, True),
                       (0.12, 0.40, 0.70, 'berry')],
    ID['skywheat']: [(0.05, 0.0, 0.55, False), (0.10, 0.50, 0.92, True), (0.14, 0.82, 1.02, 'grain')],
    ID['sweetroot_crop']: [(0.08, 0.0, 0.28, False), (0.28, 0.22, 0.62, True), (0.16, 0.50, 0.78, True)],
    ID['berry_crop']: [(0.08, 0.0, 0.22, False), (0.36, 0.18, 0.58, True), (0.22, 0.50, 0.78, True),
                       (0.10, 0.40, 0.70, 'berry')],
}
CROP_GROW = {ID['skywheat'], ID['sweetroot_crop'], ID['berry_crop']}

# point-light colour and radius (world units) for glowing cells
LIGHTS = {
    ID['crystal']: ((0.45, 0.80, 1.0), 7.0),
    ID['bloom']: ((1.0, 0.55, 0.75), 5.0),
    ID['lantern']: ((1.0, 0.78, 0.45), 11.0),
    ID['glowcap']: ((0.40, 1.0, 0.85), 6.0),
    ID['awake_spire']: ((0.80, 0.70, 1.0), 16.0),
    ID['lumen_shard']: ((0.70, 0.55, 1.0), 6.0),
    ID['cloudstuff']: ((0.9, 0.9, 1.0), 3.0),
    ID['glowstick']: ((1.0, 0.72, 0.40), 9.0),
    ID['aetherite_ore']: ((0.75, 0.50, 1.0), 4.0),
    ID['emberite_ore']: ((1.0, 0.50, 0.25), 3.0),
    ID['lumen_lamp']: ((1.0, 0.86, 0.60), 13.0),
    ID['kiln']: ((1.0, 0.55, 0.30), 4.0),
    ID['ember_lamp']: ((1.0, 0.50, 0.22), 13.0),
    ID['aether_lamp']: ((0.72, 0.48, 1.0), 13.0),
    ID['verdigris_lamp']: ((0.35, 0.90, 0.75), 13.0),
    ID['starstone']: ((0.50, 0.40, 0.90), 4.0),
    ID['polished_starstone']: ((0.55, 0.45, 0.95), 5.0),
    ID['starstone_tiles']: ((0.50, 0.40, 0.90), 4.0),
    ID['waystone']: ((0.75, 0.65, 1.0), 10.0),
    ID['glimmer_font']: ((1.0, 0.84, 0.45), 12.0),
}
ORES = [ID['emberite_ore'], ID['verdigris_ore'], ID['silverine_ore'], ID['aetherite_ore']]
WOODS = {ID['heartwood'], ID['cedar_heartwood'], ID['pale_heartwood'], ID['dark_heartwood']}

# ---- realms (biomes) -----------------------------------------------------------
REALMS = ['Meadow Isles', 'Amberwood', 'Rose Mesas', 'Frostglass', 'Basalt Steps', 'Mossfen', 'Duneglass',
          'Lumen Grove',
          # 1.4: eight new landscapes (existing materials, new palettes and flora)
          'Saltwind Flats', 'Cedar Highlands', 'Lavender Downs', 'Cinder Spires',
          'Chalk Barrens', 'Starfall Veil', 'Cloudstep Isles', 'Verdigris Canyons']
N_REALMS = len(REALMS)
REALM_TURF = np.array([(0.56, 0.80, 0.44), (0.82, 0.76, 0.46), (0.72, 0.78, 0.48), (0.93, 0.96, 1.0),
                       (0.47, 0.66, 0.47), (0.40, 0.62, 0.36), (0.88, 0.82, 0.58), (0.62, 0.50, 0.86),
                       # saltwind, cedar, lavender, cinder, chalk, starfall, cloudstep, verdigris
                       (0.78, 0.74, 0.58), (0.30, 0.48, 0.34), (0.72, 0.58, 0.82), (0.22, 0.20, 0.20),
                       (0.90, 0.88, 0.78), (0.28, 0.24, 0.48), (0.82, 0.90, 0.94), (0.22, 0.58, 0.50)], np.float32)
REALM_CANOPY = np.array([(0.42, 0.70, 0.40), (0.93, 0.66, 0.38), (0.62, 0.74, 0.40), (0.48, 0.66, 0.62),
                         (0.38, 0.58, 0.40), (0.50, 0.72, 0.42), (0.78, 0.80, 0.46), (0.84, 0.56, 0.92),
                         (0.62, 0.66, 0.40), (0.22, 0.40, 0.28), (0.86, 0.56, 0.78), (0.28, 0.22, 0.22),
                         (0.70, 0.78, 0.58), (0.62, 0.48, 0.90), (0.70, 0.86, 0.88), (0.18, 0.62, 0.48)], np.float32)
ROSE_BANDS = np.array([(0.93, 0.64, 0.56), (0.97, 0.80, 0.67), (0.84, 0.54, 0.52), (0.98, 0.88, 0.76),
                       (0.90, 0.70, 0.60)], np.float32)
PETAL_COLORS = np.array([(1.0, 0.96, 0.80), (1.0, 0.84, 0.40), (0.70, 0.78, 1.0), (1.0, 0.70, 0.82)], np.float32)



# Door meta: low 3 bits = facing (0-5), bit 8 = open, bit 16 = top half.
# Ladder meta: low 3 bits = the face it hangs on.

def is_blocking(world, q, r, y):
    """Solid for walking/physics. Open doors are passable; closed doors block."""
    m = world.get(q, r, y)
    if m < 0:
        return True
    if m == ID['door']:
        return (world.get_meta(q, r, y) & 8) == 0
    return bool(SOLID[m])


def _tex_style(name, kind):
    """Procedural atlas style for a material, inferred from its name."""
    n = name.lower()
    if kind == 'glass' or n.endswith(' glass') or n == 'glass':
        return 'glass'
    if 'lamp' in n:
        return 'lamp'
    if 'heartwood' in n:
        return 'wood'
    if 'planks' in n:
        return 'planks'
    if 'bricks' in n or n == 'bricks':
        return 'bricks'
    if 'tiles' in n or n == 'shingles' or n.endswith(' shingles'):
        return 'tiles' if 'tiles' in n else 'shingles'
    if n.startswith('polished') or 'polished' in n:
        return 'polished'
    if n == 'cobble' or n.startswith('cobble '):
        return 'cobble'
    if n == 'slate' or n.startswith('slate '):
        return 'slate'
    if n == 'chalk' or n.startswith('chalk '):
        return 'chalk'
    if n == 'sandstone' or n.startswith('sandstone '):
        return 'sandstone'
    if n == 'cinder' or n.startswith('cinder '):
        return 'cinder'
    if 'starstone' in n:
        return 'starstone'
    if n.startswith('salt'):
        return 'salt'
    if 'pale stone' in n:
        return 'palestone'
    if n == 'thatch' or n.startswith('thatch '):
        return 'thatch'
    if n == 'carved stone':
        return 'carved'
    if n == 'mosaic':
        return 'mosaic'
    if n == 'packed earth':
        return 'earth'
    if n == 'wattle':
        return 'wattle'
    if 'cloth' in n or n == 'linen':
        return 'cloth'
    if n == 'heather':
        return 'heather'
    if 'waystone' in n:
        return 'waystone'
    if 'font' in n:
        return 'font'
    if 'farmland' in n:
        return 'farm'
    if kind == 'slab':
        return _tex_style(name[:-5] if name.lower().endswith(' slab') else name, 'full')
    return ''


TEX_STYLE = [_tex_style(m[0], m[1]) for m in _M]


def layer_span(m, ly, layer):
    """World-space [bottom, top] of a solid cell, or None."""
    if m <= 0 or m >= N or not SOLID[m]:
        return None
    y0 = ly * layer
    return y0, y0 + (0.5 if IS_SLAB[m] else 1.0) * layer


def overlaps_solid(world, q, r, y0, y1, layer):
    """True if any blocking cell in this column overlaps the world-space interval [y0, y1)."""
    import math
    ly0 = int(math.floor(y0 / layer))
    ly1 = int(math.floor((y1 - 1e-9) / layer))
    for ly in range(ly0, ly1 + 1):
        m = world.get(q, r, ly)
        if m <= 0:
            continue
        if m == ID['door'] and not is_blocking(world, q, r, ly):
            continue
        if m == ID['door'] or (m < N and SOLID[m] and not IS_SLAB[m] and KIND[m] != 'full' and KIND[m] != 'glass' and KIND[m] != 'slab'):
            # closed door / other solid non-full (shouldn't happen often): full layer
            if is_blocking(world, q, r, ly) and ly * layer < y1 and (ly + 1) * layer > y0:
                return True
            continue
        if not is_blocking(world, q, r, ly) and not (m < N and SOLID[m]):
            continue
        span = layer_span(m, ly, layer)
        if span and span[0] < y1 and span[1] > y0:
            return True
    return False


def support_top(world, q, r, y, layer):
    """Highest solid top at or below world y in this column, or None."""
    import math
    ly = int(math.floor((y - 1e-6) / layer))
    best = None
    for k in range(ly, max(-1, ly - 4), -1):
        m = world.get(q, r, k)
        if m <= 0:
            continue
        if m == ID['door'] and not is_blocking(world, q, r, k):
            continue
        if not (m < N and SOLID[m]) and not is_blocking(world, q, r, k):
            continue
        span = layer_span(m, k, layer)
        if span is None:
            if is_blocking(world, q, r, k):
                span = (k * layer, (k + 1) * layer)
            else:
                continue
        if span[1] <= y + 0.02 or (span[0] < y <= span[1] + 0.001):
            best = span[1] if best is None else max(best, span[1])
            break
    return best
