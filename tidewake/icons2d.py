"""Hand-drawn 16x16 pixel-art icons for non-block items (tools, food, materials).
Each is drawn with a small palette derived from the item's colours, then scaled to 64x64
with a soft shadow. Blocks keep their rendered 3D textured hex icons."""
import numpy as np

ART = {
    'stick': ['................', '.............ww.', '............wWw.', '...........wWw..', '..........wWw...',
              '.........wWw....', '........wWw.....', '.......wWw......', '......wWw.......', '.....wWw........',
              '....wWw.........', '...wWw..........', '..wWw...........', '..Ww............', '................', '................'],
    'plume': ['................', '...........lll..', '.........llbbl..', '........lbbbbl..', '.......lbbbbl...', '......lbbbbl....',
              '.....lbbbdl.....', '....lbbbdl......', '...lbbbdl.......', '...lbbdl........', '...ldd..........', '..dd............',
              '.dd.............', 'd...............', '................', '................'],
    'ingot': ['................', '................', '................', '................', '.....llllllll...', '....lhhhhhhhbo..',
              '...lhhbbbbbbbo..', '..lbbbbbbbbbdo..', '..obbbbbbbbbdo..', '..oddddddddddo..', '..oooooooooooo..', '................',
              '................', '................', '................', '................'],
    'gem': ['................', '................', '......oooo......', '....oolhhlo.....', '...olhhbbbldo...', '..olhbbbbbbddo..',
            '..obbbbbbbbddo..', '..odbbbbbbdddo..', '...odbbbbddddo..', '....odbbbdddo...', '.....odbdddo....', '......oddo......',
            '.......oo.......', '................', '................', '................'],
    'lump': ['................', '................', '................', '......oooo......', '....oolhhloo....', '...olhhbbbblo...',
             '..olhbbbbbbbdo..', '..obbbbdbbbbdo..', '..obbbbbbbbddo..', '..odbbbbbbdddo..', '...oddbbddddo...', '....oooooooo....',
             '................', '................', '................', '................'],
    'dust': ['................', '................', '..........h.....', '......l.....h...', '...h....b.......', '.....bb.....l...',
             '....bbbbb.......', '...lbbbbbb...h..', '..obbbbbbbbo....', '..odbbbbbbddo...', '...oddddddddo...', '....oooooooo....',
             '................', '................', '................', '................'],
    'berries': ['................', '.......gg.......', '......g..g......', '.....g....g.....', '....oo....oo....', '...olbo..olbo...',
                '..olhbbooolhbbo.', '..obbbbolhbbbbo.', '..obbbdobbbbbdo.', '...oddo.obbbddo.', '....oo...oddddo.', '..........oooo..',
                '................', '................', '................', '................'],
    'meat': ['................', '................', '.......oooo.....', '.....oolbbboo...', '....olbbbbbbbo..', '...olbbllbbbbdo.',
             '...obbbbbbbbbdo.', '...obbbbbbbbddo.', '...odbbbbbddddo.', '...hodddddddoo..', '..hhh.ooooooo...', '.hhh............',
             '.hh.............', '................', '................', '................'],
    'egg': ['................', '................', '.......oo.......', '......ohho......', '.....ohhbbo.....', '....ohbbdbbo....',
            '....obbbbbbo....', '...obbdbbbbbo...', '...obbbbbdbbo...', '...odbbbbbbdo...', '....odbbbbdo....', '.....oddddo.....',
            '......oooo......', '................', '................', '................'],
    'pie': ['................', '................', '................', '................', '.....oooooo.....', '...oollllllloo..',
            '..olllcllclllo..', '..olcccccccclo..', '.olllccllccllloo', '.obbbbbbbbbbbbo.', '.odbdbdbdbdbdbo.', '..oddddddddddo..',
            '...oooooooooo...', '................', '................', '................'],
    'pail': ['................', '.....oooooo.....', '....o......o....', '...o........o...', '..oooooooooooo..', '..olhbbbbbbbdo..',
             '..olccccccccdo..', '..olbbbbbbbbdo..', '...olbbbbbbdo...', '...olbbbbbbdo...', '...obbbbbbbdo...', '....odddddddo....'[:16],
             '....oooooooo....', '................', '................', '................'],
    'pick': ['................', '....oooooooo....', '..oohhbbbbbboo..', '.ohbbbboobbbbbo.', '.obbdoo.wWoodbbo', 'obdo....wW..obdo',
             'odo.....wW...odo', 'oo......wW....oo', '........wW......', '........wW......', '........wW......', '........wW......',
             '........wW......', '........wW......', '........WW......', '................'],
    'axe': ['................', '.....oooo.......', '...oohhbbo......', '..ohhbbbbwW.....', '..obbbbbbwW.....', '..obbbbdowW.....',
            '..odbbdo.wW.....', '...oddo..wW.....', '....oo...wW.....', '.........wW.....', '.........wW.....', '.........wW.....',
            '.........wW.....', '.........wW.....', '.........WW.....', '................'],
    'spade': ['................', '.......WW.......', '......wWWw......', '.......wW.......', '.......wW.......', '.......wW.......',
              '.......wW.......', '......owWo......', '.....ohbbbo.....', '....ohbbbbbo....', '....obbbbbdo....', '....obbbbbdo....',
              '....odbbbddo....', '.....oddddo.....', '......oooo......', '................'],
    'blade': ['................', '.............oo.', '............ohbo', '...........ohbdo', '..........ohbdo.', '.........ohbdo..',
              '........ohbdo...', '.......ohbdo....', '..oo..ohbdo.....', '...oowhbdo......', '....owWdo.......', '....oWwo........',
              '...wWo.oo.......', '..wWw...........', '..WW............', '................'],
}

MODEL_ART = {'stick': 'stick', 'ingot': 'ingot', 'gem': 'gem', 'berries': 'berries', 'pie': 'pie', 'pail': 'pail',
             'pick': 'pick', 'axe': 'axe', 'spade': 'spade', 'blade': 'blade'}
NAME_ART = {'Plume': 'plume', 'Gloom Dust': 'dust', 'Raw Hopmeat': 'meat', 'Roast Hopmeat': 'meat', 'Speckled Egg': 'egg',
            'Glowcap Stew': 'pie'}


def art_for(it):
    if it is None or it.model in ('block', 'deco'):
        return None
    return NAME_ART.get(it.name) or MODEL_ART.get(it.model) or ('lump' if it.model == 'lump' else None)


def render(it, size=64):
    """-> (size, size, 4) uint8 RGBA, top row first."""
    key = art_for(it)
    if key is None:
        return None
    g = ART[key]
    c1 = np.array(it.color, dtype=np.float64)
    c2 = np.array(it.color2 if it.color2 else it.color, dtype=np.float64)
    wood = np.array([0.72, 0.54, 0.36])
    if key == 'stick':
        c1 = np.array(it.color)
        wood = c1
    pal = {
        'o': np.minimum(c1 * 0.38, 1), 'b': c1, 'l': np.minimum(c1 * 1.15 + 0.05, 1), 'h': np.minimum(c1 * 0.6 + 0.45, 1),
        'd': c1 * 0.72, 'w': wood, 'W': wood * 0.72, 'g': np.array([0.40, 0.62, 0.36]),
        'c': c2,
    }
    if key in ('pie',) and it.name == 'Glowcap Stew':
        pal['l'] = np.array([0.80, 0.62, 0.44])
        pal['c'] = c1
        pal['b'] = np.array([0.66, 0.50, 0.34])
        pal['d'] = pal['b'] * 0.75
        pal['o'] = pal['b'] * 0.4
    if key == 'pie':
        pal['b'], pal['d'], pal['o'] = c1 * 0.9, c1 * 0.7, c1 * 0.38
    if key == 'pail':
        pal['c'] = c2 if it.name.endswith('Water') else c1 * 0.8
    if key == 'meat' and it.name.startswith('Raw'):
        pal['h'] = np.array([0.98, 0.94, 0.88])
    if key == 'meat' and it.name.startswith('Roast'):
        pal['h'] = np.array([0.96, 0.90, 0.80])
    if key == 'egg':
        pal['d'] = np.array([0.70, 0.56, 0.44])
    img = np.zeros((16, 16, 4))
    for y, row in enumerate(g):
        for x, ch in enumerate(row[:16]):
            if ch in pal:
                img[y, x, :3] = pal[ch]
                img[y, x, 3] = 1.0
    big = np.repeat(np.repeat(img, size // 16, 0), size // 16, 1)
    # soft drop shadow
    sh = np.zeros_like(big)
    k = size // 16
    sh[k:, k:, 3] = big[:-k, :-k, 3] * 0.28
    out = sh.copy()
    a = big[..., 3:4]
    out[..., :3] = big[..., :3] * a + sh[..., :3] * (1 - a)
    out[..., 3] = np.maximum(big[..., 3], sh[..., 3])
    return np.clip(out * 255, 0, 255).astype(np.uint8)
