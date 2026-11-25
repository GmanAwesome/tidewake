"""The 'texture pack': a procedural atlas of small tileable detail patterns, one top and one side
tile per material. Each texel is a brightness multiplier (stored /2, so 0.5 = unchanged) that the
chunk shader applies over the block colour, so the cozy palette stays but blocks gain grain,
strata, cracks, leaves, boards, bricks and sparkle. Built with numpy at startup (~0.1 s)."""
import numpy as np

T = 64                  # tile size in texels
COLS = 16               # atlas columns -> tile index = material * 2 + (side ? 1 : 0); fronts at 2 * N + material
# channel R: brightness multiplier (/2).  channel G: glow mask (0.5 = normal emission, 0 = none, 1 = double)


def _rng(k):
    return np.random.default_rng(1000 + k)


Y, X = np.mgrid[0:T, 0:T].astype(np.float64) / T      # 0..1


def hex_r():
    """World-space radius from the hex centre, given the pointy-top bounding-box UV."""
    lx = (X - 0.5) * np.sqrt(3.0)
    lz = (Y - 0.5) * 2.0
    return np.sqrt(lx * lx + lz * lz)



def vnoise(rng, cells, octaves=1):
    """Tileable smooth value noise in about [-1, 1]."""
    out = np.zeros((T, T))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        c = cells * (2 ** o)
        g = rng.uniform(-1, 1, (c, c))
        fx, fy = X * c, Y * c
        x0, y0 = np.floor(fx).astype(int), np.floor(fy).astype(int)
        tx, ty = fx - x0, fy - y0
        tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
        x1, y1 = (x0 + 1) % c, (y0 + 1) % c
        x0, y0 = x0 % c, y0 % c
        a = g[y0, x0] + (g[y0, x1] - g[y0, x0]) * tx
        b = g[y1, x0] + (g[y1, x1] - g[y1, x0]) * tx
        out += (a + (b - a) * ty) * amp
        tot += amp
        amp *= 0.5
    return out / tot


def voronoi(rng, n):
    """Tileable cells -> (distance to nearest, distance to edge, cell id)."""
    pts = rng.uniform(0, 1, (n, 2))
    d1 = np.full((T, T), 9.0)
    d2 = np.full((T, T), 9.0)
    idx = np.zeros((T, T), int)
    for i, (px, py) in enumerate(pts):
        dx = np.abs(X - px)
        dy = np.abs(Y - py)
        dx = np.minimum(dx, 1 - dx)
        dy = np.minimum(dy, 1 - dy)
        d = np.sqrt(dx * dx + dy * dy)
        closer = d < d1
        d2 = np.where(closer, d1, np.minimum(d2, d))
        idx = np.where(closer, i, idx)
        d1 = np.where(closer, d, d1)
    return d1, d2 - d1, idx


def speck(rng, density, lo, hi, size=1):
    m = np.ones((T, T))
    n = int(T * T * density)
    ys, xs = rng.integers(0, T, n), rng.integers(0, T, n)
    vals = rng.uniform(lo, hi, n)
    for dy in range(size):
        for dx in range(size):
            m[(ys + dy) % T, (xs + dx) % T] = vals
    return m


def strata(rng, bands, amp):
    v = vnoise(rng, 4) * 0.08
    return 1 + amp * np.sin((Y + v) * np.pi * 2 * bands + rng.uniform(0, 6)) * (0.6 + 0.4 * vnoise(rng, 2))


def cracks(rng, n, width=0.012, dark=0.72):
    _, edge, _ = voronoi(rng, n)
    return np.where(edge < width, dark + (1 - dark) * edge / width, 1.0)


def boards(rng, rows, vertical=False):
    yy = X if vertical else Y
    xx = Y if vertical else X
    row = np.floor(yy * rows)
    f = yy * rows - row
    gap = np.where((f < 0.06) | (f > 0.96), 0.7, 1.0)
    shift = (row * 0.37) % 1
    seam = np.where(np.abs(((xx + shift) % 0.5) - 0.0) < 0.012, 0.75, 1.0)
    grain = 1 + 0.07 * np.sin((xx * 9 + vnoise(rng, 4) * 0.6) * np.pi * 2) + 0.04 * vnoise(rng, 8)
    tone = 1 + 0.06 * np.sin(row * 2.3)
    return gap * seam * grain * tone


def bricks(rng, rows=4, cols=2, mortar=0.06):
    row = np.floor(Y * rows)
    xx = X * cols + (row % 2) * 0.5
    fy = Y * rows - row
    fx = xx - np.floor(xx)
    m = (fy < mortar * rows / 2) | (fx < mortar * cols / 2)
    tone = 1 + 0.08 * np.sin(row * 3.1 + np.floor(xx) * 5.7)
    return np.where(m, 0.68, tone * (1 + 0.05 * vnoise(rng, 8)))


def leaves(rng, n=26):
    d1, edge, idx = voronoi(rng, n)
    tone = 0.9 + 0.22 * (idx * 0.618 % 1)
    blob = np.clip(1.0 - d1 * 9.0, 0, 1)
    return (0.74 + 0.36 * blob) * tone * np.where(edge < 0.01, 0.8, 1.0)


def facets(rng, n=7):
    _, edge, idx = voronoi(rng, n)
    tone = 0.86 + 0.3 * (idx * 0.618 % 1)
    return tone * np.where(edge < 0.012, 1.25, 1.0)


def bevel(w=0.07):
    e = np.minimum(np.minimum(X, 1 - X), np.minimum(Y, 1 - Y))
    hl = np.where((X < w) | (Y < w), 1.1, np.where((X > 1 - w) | (Y > 1 - w), 0.86, 1.0))
    return np.where(e < w, hl, 1.0)


def tile(mat, side):
    rng = _rng(mat * 2 + side)
    n = lambda c, o=2, a=0.08: 1 + a * vnoise(rng, c, o)
    if mat == 1:            # stone
        return (strata(rng, 3, 0.05) * cracks(rng, 7) * n(4, 3)) if side else cracks(rng, 9, 0.014) * n(4, 3, 0.1)
    if mat == 2:            # loam
        return speck(rng, 0.08, 0.8, 1.15) * n(6, 2, 0.1) * speck(rng, 0.008, 0.7, 0.85, 2)
    if mat == 3:            # turf
        if side:
            fringe = np.where(Y > 0.72 + 0.12 * vnoise(rng, 8), 0.8, 1.0)
            return speck(rng, 0.07, 0.82, 1.15) * n(6) * fringe
        blades = speck(rng, 0.22, 0.82, 1.2) * speck(rng, 0.02, 1.15, 1.3, 2)
        return blades * n(3, 2, 0.12)
    if mat == 4:            # sand
        rip = 1 + 0.06 * np.sin((Y * 6 + vnoise(rng, 3) * 0.6) * np.pi * 2)
        return speck(rng, 0.3, 0.92, 1.08) * (rip if not side else strata(rng, 5, 0.04))
    if mat == 5:            # snow
        return n(4, 2, 0.04) * speck(rng, 0.01, 1.12, 1.25)
    if mat in (6, 12, 30):  # ice, crystal, glass
        return facets(rng, 6 if mat != 30 else 3) * (bevel(0.05) if (mat == 30 and side) else 1.0)
    if mat == 7:            # basalt: little hex columns
        if side:
            col = np.abs(((X * 4) % 1) - 0.5)
            return np.where(col > 0.46, 0.72, 1.0) * n(6, 3, 0.1)
        return cracks(rng, 6, 0.016, 0.65) * n(5)
    if mat == 8:            # rosestone
        return strata(rng, 6, 0.06) * n(5)
    if mat == 9:            # heartwood
        if side:
            bark = 1 + 0.16 * np.sin((X * 7 + vnoise(rng, 3) * 0.5) * np.pi * 2) * (0.6 + 0.4 * vnoise(rng, 2))
            return bark * n(8, 2, 0.06)
        r = hex_r()
        return 1 + 0.08 * np.sin((r * 9 + vnoise(rng, 3) * 0.3) * np.pi * 2)
    if mat == 10:           # canopy
        return leaves(rng, 46 if side else 60)
    if mat == 11:           # water
        return n(3, 2, 0.12) * (1 + 0.05 * np.sin((X + Y * 0.5) * np.pi * 8))
    if mat == 15:           # clay
        return strata(rng, 8, 0.025) * n(4, 2, 0.04)
    if mat == 16:           # mossrock
        moss = np.where(vnoise(rng, 4, 2) > 0.1, 1.12, 0.92)
        return moss * cracks(rng, 7) * speck(rng, 0.06, 0.85, 1.12)
    if mat in (17, 32):     # cloudstuff, fluff
        d1, _, _ = voronoi(rng, 9)
        return 0.92 + 0.12 * np.clip(1 - d1 * 4, 0, 1)
    if mat in (21, 22, 23):  # plinth & spires: carved bands
        band = np.where((np.abs(Y - 0.5) < 0.04) | (Y < 0.04), 0.78, 1.0)
        runes = np.where((np.abs(((X * 6) % 1) - 0.5) < 0.06) & (np.abs(Y - 0.5) > 0.12) & (np.abs(Y - 0.5) < 0.3), 0.85, 1.0)
        return band * runes * n(5, 2, 0.05) if side else cracks(rng, 5, 0.008, 0.88) * n(5, 2, 0.04)
    if mat == 26:           # planks
        return boards(rng, 4)
    if mat == 29:           # chest: boards with iron bands and a lid seam
        if not side:
            return boards(rng, 4) * np.where(vnoise(rng, 2) > 0.5, 0.9, 1.0)
        return chest_side(rng, False)
    if mat == 27:           # tinker bench: plank top; sides show the apron, legs and a stretcher
        if not side:
            return boards(rng, 3) * speck(rng, 0.01, 0.75, 0.9)
        return bench_side(rng, False)
    if mat == 28:           # kiln: clay bricks, sooty top
        return bricks(rng, 4, 2) if side else cracks(rng, 6, 0.01, 0.8) * n(4, 2, 0.1) * np.where(vnoise(rng, 3) > 0.2, 0.8, 1.0)
    if mat == 31:
        return bricks(rng, 4, 2)
    if mat == 41:           # mossy bricks
        return bricks(rng, 4, 2) * np.where(vnoise(rng, 3, 2) > 0.15, 1.12, 1.0)
    if 36 <= mat <= 39:     # ores: dark stone with bright flecks
        flecks = np.where(vnoise(rng, 8, 2) > 0.32, 1.35, 0.72)
        return flecks * cracks(rng, 6) * n(6, 2, 0.06)
    if mat == 40:           # polished stone
        return (bevel(0.07) if side else cracks(rng, 4, 0.006, 0.9)) * n(3, 2, 0.03)
    if mat == 42:           # lumen lamp: iron frame + glowing pane
        fr = (X < 0.12) | (X > 0.88) | (Y < 0.12) | (Y > 0.88)
        if not side:
            return n(4, 2, 0.05), np.full((T, T), 0.6)
        return np.where(fr, 0.55, 1.15) * n(4, 2, 0.05), np.where(fr, 0.0, 0.75)
    if mat == 13:           # vine: leafy strands
        strands = 1 + 0.18 * np.sin((X * 5 + vnoise(rng, 3) * 0.4) * np.pi * 2)
        return strands * leaves(rng, 40) * 1.05
    if mat in (14, 25):     # bloom, petals: soft petal veins
        r = hex_r()
        ang = np.arctan2((Y - 0.5) * 2.0, (X - 0.5) * np.sqrt(3.0))
        return (1 + 0.1 * np.cos(ang * 5)) * (1 - 0.1 * r) * n(5, 2, 0.05)
    if mat in (19, 35):     # sprout, berry bush: leaves with veins
        veins = np.where(np.abs(((X + Y * 0.5) * 4) % 1 - 0.5) < 0.04, 0.85, 1.0)
        return leaves(rng, 34) * veins
    if mat == 20:           # glowcap: bright spots that glow
        d1, _, _ = voronoi(rng, 7)
        spot = d1 < 0.07
        return np.where(spot, 1.3, 0.95) * n(5, 2, 0.05), np.where(spot, 1.0, 0.25)
    if mat == 24:           # lumen shard: facets with glowing seams
        _, edge, idx = voronoi(rng, 5)
        return 0.9 + 0.25 * (idx * 0.618 % 1), np.where(edge < 0.02, 1.0, 0.45)
    if mat == 18:           # lantern: iron bars over glowing glass
        bars = (np.abs(((X * 3) % 1) - 0.5) > 0.42)
        return np.where(bars, 0.45, 1.1), np.where(bars, 0.0, 0.8)
    if mat == 33:           # bedroll: woven fabric with two straps
        weave = 1 + 0.05 * np.sign(np.sin(X * np.pi * 32) * np.sin(Y * np.pi * 32))
        straps = (np.abs(X - 0.3) < 0.05) | (np.abs(X - 0.7) < 0.05)
        plaid = 1 + 0.06 * (np.sin(Y * np.pi * 8) > 0.6) + 0.06 * (np.sin(X * np.pi * 8) > 0.6)
        return weave * (np.where(straps, 0.62, 1.0) if side else plaid)
    if mat == 34:           # glowstick: wood grain, glowing tip
        return 1 + 0.1 * np.sin((X * 6 + vnoise(rng, 3) * 0.3) * np.pi * 2), np.where(Y > 0.5, 0.9, 0.3)
    if mat == 43:           # door: vertical boards, frame, a little window
        b = boards(rng, 4, vertical=True)
        frame = (X < 0.12) | (X > 0.88) | (Y < 0.08) | (Y > 0.92)
        window = (np.abs(X - 0.5) < 0.18) & (Y > 0.48) & (Y < 0.78)
        out = np.where(frame, 0.55, b)
        return np.where(window, 1.35, out)
    if mat == 44:           # ladder: two stiles and rungs
        stile = (np.abs(X - 0.18) < 0.07) | (np.abs(X - 0.82) < 0.07)
        rung = (np.abs((Y * 4) % 1 - 0.5) < 0.12) & (X > 0.12) & (X < 0.88)
        return np.where(stile | rung, boards(rng, 5, vertical=True) * 1.05, 0.35)
    # 1.4.1 ground cover (ids appended after berry crop)
    from .materials import ID as _MID
    if mat == _MID.get('grass'):
        blade = 1 + 0.12 * np.sin((X * 14 + vnoise(rng, 5) * 0.4) * np.pi * 2)
        tip = np.where(Y > 0.72, 0.85, 1.0)
        return blade * tip * n(6, 2, 0.06)
    if mat == _MID.get('wildflower'):
        r = hex_r()
        petal = (r < 0.55) & (np.abs(np.sin(np.arctan2(Y - 0.5, X - 0.5) * 5)) > 0.35)
        return np.where(petal, 1.25, 0.8) * n(5, 2, 0.05)
    if mat == _MID.get('mushroom'):
        cap = ((X - 0.5) ** 2 + ((Y - 0.58) * 0.8) ** 2) < 0.22 ** 2
        spots = cap & (vnoise(rng, 8, 2) > 0.28)
        stem = (np.abs(X - 0.5) < 0.12) & (Y < 0.5)
        return np.where(spots, 1.3, np.where(cap | stem, 1.05, 0.4)) * n(4, 2, 0.04)
    if mat == _MID.get('pebble'):
        d1, edge, idx = voronoi(rng, 9)
        return (0.9 + 0.2 * (idx * 0.618 % 1)) * np.where(edge < 0.02, 0.75, 1.0) * n(4, 2, 0.04)
    if mat == _MID.get('shrub'):
        return leaves(rng, 40) * n(5, 2, 0.06)
    if mat == _MID.get('reeds'):
        stem = np.abs(((X * 6) % 1) - 0.5) < 0.12
        return np.where(stem, 1.1 * (1 + 0.08 * np.sin(Y * np.pi * 8)), 0.4) * n(4, 2, 0.05)
    if mat == _MID.get('signpost'):
        post = np.abs(X - 0.5) < 0.08
        board = (Y > 0.55) & (Y < 0.9) & (X > 0.18) & (X < 0.82)
        return np.where(post | board, boards(rng, 4, vertical=True), 0.35)
    # 1.4 phase 2b: style-driven tiles for the expanded roster (procedural, never copied)
    from .materials import TEX_STYLE
    style = TEX_STYLE[mat] if mat < len(TEX_STYLE) else ''
    if style == 'wood':
        if side:
            bark = 1 + 0.16 * np.sin((X * 7 + vnoise(rng, 3) * 0.5) * np.pi * 2) * (0.6 + 0.4 * vnoise(rng, 2))
            return bark * n(8, 2, 0.06)
        r = hex_r()
        return 1 + 0.08 * np.sin((r * 9 + vnoise(rng, 3) * 0.3) * np.pi * 2)
    if style == 'planks':
        return boards(rng, 4)
    if style == 'bricks':
        return bricks(rng, 4, 2)
    if style == 'tiles':
        # larger floor tiles with a grout grid (not the same as bricks)
        rows, cols, mortar = 3, 3, 0.045
        fy = Y * rows - np.floor(Y * rows)
        fx = X * cols - np.floor(X * cols)
        grout = (fy < mortar * rows) | (fx < mortar * cols)
        tone = 1 + 0.05 * np.sin(np.floor(Y * rows) * 2.7 + np.floor(X * cols) * 4.1)
        return np.where(grout, 0.72, tone * (1 + 0.03 * vnoise(rng, 6))) * (bevel(0.04) if side else 1.0)
    if style == 'polished':
        vein = 1 + 0.06 * np.sin((X * 3 + Y * 5 + vnoise(rng, 3) * 0.8) * np.pi * 2)
        return (bevel(0.07) if side else cracks(rng, 4, 0.005, 0.9)) * vein * n(3, 2, 0.025)
    if style == 'cobble':
        d1, edge, idx = voronoi(rng, 14)
        tone = 0.88 + 0.2 * (idx * 0.618 % 1)
        return tone * np.where(edge < 0.03, 0.7, 1.0) * n(4, 2, 0.04)
    if style == 'slate':
        return strata(rng, 10, 0.08) * n(4, 2, 0.04) * (cracks(rng, 5, 0.008, 0.85) if not side else 1)
    if style == 'chalk':
        return speck(rng, 0.14, 0.88, 1.12, 2) * n(5, 2, 0.05)
    if style == 'sandstone':
        return strata(rng, 7, 0.05) * speck(rng, 0.08, 0.9, 1.1) * n(4, 2, 0.04)
    if style == 'cinder':
        holes = np.where(vnoise(rng, 8, 2) > 0.38, 0.55, 1.0)
        return holes * speck(rng, 0.1, 0.8, 1.15) * n(5, 2, 0.08)
    if style == 'starstone':
        fleck = np.where(vnoise(rng, 10, 2) > 0.45, 1.55, 0.85)
        glow = np.where(fleck > 1.2, 0.8, 0.15)
        return fleck * n(4, 2, 0.06), glow
    if style == 'salt':
        d1, edge, _ = voronoi(rng, 18)
        return (0.92 + 0.16 * np.clip(1 - d1 * 6, 0, 1)) * np.where(edge < 0.015, 1.15, 1.0)
    if style == 'palestone':
        return n(4, 2, 0.04) * (bevel(0.05) if side else cracks(rng, 5, 0.007, 0.9))
    if style == 'thatch':
        bundle = np.floor(Y * 10)
        straw = 1 + 0.1 * np.sin((X * 18 + bundle * 0.3 + vnoise(rng, 6) * 0.4) * np.pi * 2)
        gap = np.where((Y * 10 - bundle) < 0.08, 0.75, 1.0)
        return straw * gap * (1 + 0.04 * vnoise(rng, 8))
    if style == 'shingles':
        row = np.floor(Y * 6)
        xx = (X + (row % 2) * 0.5)
        fx, fy = xx - np.floor(xx), Y * 6 - row
        edge = (fy < 0.08) | (fx < 0.06) | (fx > 0.94)
        # curved lower lip of each shingle
        lip = (fy > 0.82) & (((fx - 0.5) ** 2 * 0.6 + (fy - 1.0) ** 2) < 0.08)
        tone = 1 + 0.08 * np.sin(row * 2.4 + np.floor(xx) * 3.1)
        return np.where(edge | lip, 0.68, tone) * n(5, 2, 0.04)
    if style == 'carved':
        band = np.where((np.abs(Y - 0.5) < 0.05) | (Y < 0.06) | (Y > 0.94), 0.78, 1.0)
        motif = ((np.abs(X - 0.5) < 0.18) & (np.abs(Y - 0.5) < 0.18)) | ((X - 0.5) ** 2 + (Y - 0.5) ** 2 < 0.04)
        rosette = motif & ~((np.abs(X - 0.5) < 0.06) & (np.abs(Y - 0.5) < 0.06))
        return band * np.where(rosette, 0.72, 1.0) * n(5, 2, 0.04) * (bevel(0.06) if side else 1)
    if style == 'mosaic':
        cells = 8
        fx, fy = X * cells - np.floor(X * cells), Y * cells - np.floor(Y * cells)
        grout = (fx < 0.12) | (fy < 0.12)
        tone = 0.85 + 0.3 * ((np.floor(X * cells) * 7 + np.floor(Y * cells) * 13) % 5) / 5
        return np.where(grout, 0.65, tone) * n(3, 2, 0.03)
    if style == 'earth':
        return n(5, 2, 0.08) * speck(rng, 0.07, 0.85, 1.1)
    if style == 'wattle':
        weave = 1 + 0.1 * np.sin(X * np.pi * 10) * np.sin(Y * np.pi * 8)
        stick = np.where((np.abs((X * 6) % 1 - 0.5) < 0.08) | (np.abs((Y * 8) % 1 - 0.5) < 0.06), 0.8, 1.0)
        return weave * stick * n(4, 2, 0.05)
    if style == 'cloth':
        weave = 1 + 0.06 * np.sin(X * np.pi * 16) + 0.06 * np.sin(Y * np.pi * 16)
        return weave * n(3, 2, 0.03)
    if style == 'heather':
        return leaves(rng, 36 if side else 50) * speck(rng, 0.08, 0.9, 1.2)
    if style == 'lamp':
        fr = (X < 0.12) | (X > 0.88) | (Y < 0.12) | (Y > 0.88)
        if not side:
            return n(4, 2, 0.05), np.full((T, T), 0.6)
        return np.where(fr, 0.55, 1.15) * n(4, 2, 0.05), np.where(fr, 0.0, 0.75)
    if style == 'glass':
        streak = 1 + 0.04 * np.sin((X * 2 + Y * 7) * np.pi * 2)
        return streak * bevel(0.06) * n(3, 2, 0.02)
    if style == 'waystone':
        band = np.where((np.abs(Y - 0.5) < 0.05) | (Y < 0.08) | (Y > 0.92), 0.72, 1.0)
        rune = ((np.abs(X - 0.5) < 0.08) & (Y > 0.2) & (Y < 0.8)) | ((X - 0.5) ** 2 + (Y - 0.62) ** 2 < 0.04)
        glow = np.where(rune, 0.85, 0.15)
        return band * np.where(rune, 1.35, 1.0) * n(5, 2, 0.04) * bevel(0.07), glow
    if style == 'font':
        bowl = ((X - 0.5) ** 2 + ((Y - 0.55) * 0.8) ** 2 < 0.28 ** 2) & (Y > 0.28)
        rim = bowl & ~(((X - 0.5) ** 2 + ((Y - 0.55) * 0.8) ** 2 < 0.20 ** 2) & (Y > 0.34))
        out = np.where(rim, 0.7, np.where(bowl, 1.35, 0.85)) * n(4, 2, 0.05)
        glow = np.where(bowl & ~rim, 0.9, 0.1)
        return out, glow
    if style == 'farm':
        row = np.floor(Y * 8) if side else np.floor(Y * 6)
        furrow = np.abs((Y * 8 if side else Y * 6) - row - 0.5) < 0.18
        tone = 1 + 0.08 * np.sin(row * 1.7 + X * 4)
        return np.where(furrow, 0.72, tone) * n(5, 2, 0.07) * speck(rng, 0.06, 0.9, 1.08)
    return n(6, 2, 0.06)


def bench_side(rng, front):
    """Workbench side: plank apron on top, two legs, dark recess between with a stretcher (and a drawer on the front)."""
    wood = boards(rng, 2, vertical=True) * (1 + 0.04 * vnoise(rng, 8))
    apron = Y > 0.74
    legs = (X < 0.16) | (X > 0.84)
    stretcher = (Y > 0.16) & (Y < 0.27)
    out = np.where(apron | legs | stretcher, wood, 0.34 + 0.06 * vnoise(rng, 4))
    out = np.where(apron & (np.abs(Y - 0.745) < 0.02), 0.6, out)                    # apron edge shadow
    out = np.where(legs & ~apron & ((np.abs(X - 0.16) < 0.015) | (np.abs(X - 0.84) < 0.015)), 0.65, out)
    if front:
        drawer = (np.abs(X - 0.5) < 0.24) & (Y > 0.44) & (Y < 0.68)
        out = np.where(drawer, wood * 1.05, out)
        out = np.where(drawer & ((np.abs(np.abs(X - 0.5) - 0.24) < 0.02) | (np.abs(Y - 0.44) < 0.02) | (np.abs(Y - 0.68) < 0.02)), 0.6, out)
        knob = (X - 0.5) ** 2 + (Y - 0.56) ** 2 < 0.03 ** 2
        out = np.where(knob, 1.45, out)
        # a saw hanging on the apron
        saw = (np.abs(Y - 0.87) < 0.05 - (X - 0.2) * 0.12) & (X > 0.2) & (X < 0.62)
        out = np.where(saw, 1.55, out)
        out = np.where((X > 0.62) & (X < 0.72) & (np.abs(Y - 0.85) < 0.04), 0.7, out)
    return out


def chest_side(rng, front):
    """Chest: vertical boards, iron corner bands and top band, lid seam; the front has a latch and keyhole."""
    b = boards(rng, 5, vertical=True)
    iron = (X < 0.09) | (X > 0.91) | (Y > 0.9) | (Y < 0.07) | (np.abs(Y - 0.62) < 0.035)
    out = np.where(iron, 0.52 + 0.06 * vnoise(rng, 8), b)
    rivets = iron & ((((X * 10) % 1) - 0.5) ** 2 + (((Y * 16) % 1) - 0.5) ** 2 < 0.06)
    out = np.where(rivets, 0.85, out)
    out = np.where(np.abs(Y - 0.6) < 0.008, 0.4, out)                              # lid seam
    if front:
        plate = (np.abs(X - 0.5) < 0.09) & (Y > 0.44) & (Y < 0.7)
        out = np.where(plate, 1.6, out)
        hole = ((X - 0.5) ** 2 + ((Y - 0.53) * 0.8) ** 2 < 0.022 ** 2) | ((np.abs(X - 0.5) < 0.008) & (Y > 0.47) & (Y < 0.53))
        out = np.where(hole, 0.25, out)
    return out


def kiln_front(rng):
    """Clay-brick kiln front with an arched firebox; the fire inside glows (G channel)."""
    br = bricks(rng, 4, 2)
    cx, top = 0.5, 0.52
    arch = ((np.abs(X - cx) < 0.26) & (Y < top)) | (((X - cx) ** 2 + ((Y - top) * 1.0) ** 2) < 0.26 ** 2)
    arch &= Y > 0.1
    rim = ~arch & ((((np.abs(X - cx) < 0.32) & (Y < top) & (Y > 0.06)) | (((X - cx) ** 2 + (Y - top) ** 2) < 0.32 ** 2)))
    out = np.where(rim, 0.78 + 0.08 * vnoise(rng, 8), br)
    fire = 0.30 + 0.5 * np.clip(1.0 - (Y - 0.1) / 0.45, 0, 1) * (0.7 + 0.3 * vnoise(rng, 6))
    out = np.where(arch, fire, out)
    sill = (np.abs(X - cx) < 0.34) & (Y < 0.1)
    out = np.where(sill, 0.7, out)
    glow = np.where(arch, np.clip(1.15 - (Y - 0.1) * 1.1, 0.2, 1.0), 0.0)
    return out, glow


FRONTS = {27: lambda rng: bench_side(rng, True), 28: kiln_front, 29: lambda rng: chest_side(rng, True)}


def atlas(n_mats):
    tiles = n_mats * 3
    rows = (tiles + COLS - 1) // COLS
    A = np.full((rows * T, COLS * T, 2), 0.5)

    def put(k, t):
        mult, glow = t if isinstance(t, tuple) else (t, None)
        r, c = divmod(k, COLS)
        A[r * T:(r + 1) * T, c * T:(c + 1) * T, 0] = np.clip(mult, 0.3, 1.9) / 2.0
        if glow is not None:
            A[r * T:(r + 1) * T, c * T:(c + 1) * T, 1] = np.clip(glow, 0, 1)

    for m in range(n_mats):
        for side in (0, 1):
            put(m * 2 + side, tile(m, side) if m else np.ones((T, T)))
        f = FRONTS.get(m)
        put(n_mats * 2 + m, f(_rng(500 + m)) if f else (tile(m, 1) if m else np.ones((T, T))))
    img = np.clip(A * 255, 0, 255).astype(np.uint8)
    return img, rows