"""The 'texture pack': a procedural atlas of small tileable detail patterns, one top and one side
tile per material. Each texel is a brightness multiplier (stored /2, so 0.5 = unchanged) that the
chunk shader applies over the block colour, so the cozy palette stays but blocks gain grain,
strata, cracks, leaves, boards, bricks and sparkle. Built with numpy at startup (~0.1 s)."""
import numpy as np

T = 64                  # tile size in texels
COLS = 16               # atlas columns -> tile index = material * 2 + (side ? 1 : 0)


def _rng(k):
    return np.random.default_rng(1000 + k)


Y, X = np.mgrid[0:T, 0:T].astype(np.float64) / T      # 0..1


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
        return facets(rng, 6 if mat != 30 else 3) * (bevel(0.05) if mat == 30 else 1.0)
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
        r = np.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2)
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
        return band * runes * n(5, 2, 0.05) if side else bevel(0.08) * n(5, 2, 0.04)
    if mat in (26, 29):     # planks, chest
        b = boards(rng, 4)
        if mat == 29 and side:
            frame = np.where((Y < 0.1) | (Y > 0.9) | (np.abs(X - 0.5) < 0.05), 0.72, 1.0)
            latch = np.where((np.abs(X - 0.5) < 0.07) & (np.abs(Y - 0.62) < 0.08), 1.35, 1.0)
            return b * frame * latch
        return b
    if mat == 27:           # tinker bench
        return boards(rng, 3) * (np.where((np.abs(X - 0.5) < 0.02) | (np.abs(Y - 0.5) < 0.02), 0.75, 1.0) if not side else 1.0)
    if mat in (28, 31):     # kiln, bricks
        return bricks(rng, 4, 2)
    if mat == 41:           # mossy bricks
        return bricks(rng, 4, 2) * np.where(vnoise(rng, 3, 2) > 0.15, 1.12, 1.0)
    if 36 <= mat <= 39:     # ores: dark stone with bright flecks
        flecks = np.where(vnoise(rng, 8, 2) > 0.32, 1.35, 0.72)
        return flecks * cracks(rng, 6) * n(6, 2, 0.06)
    if mat == 40:           # polished stone
        return bevel(0.07) * n(3, 2, 0.03)
    if mat == 42:           # lumen lamp: frame + glowing pane
        frame = np.where((X < 0.12) | (X > 0.88) | (Y < 0.12) | (Y > 0.88), 0.7, 1.15)
        return frame * n(4, 2, 0.05)
    return n(6, 2, 0.06)


def atlas(n_mats):
    rows = (n_mats * 2 + COLS - 1) // COLS
    A = np.full((rows * T, COLS * T), 0.5)
    for m in range(n_mats):
        for side in (0, 1):
            k = m * 2 + side
            r, c = divmod(k, COLS)
            t = np.clip(tile(m, side), 0.35, 1.8) if m else np.ones((T, T))
            A[r * T:(r + 1) * T, c * T:(c + 1) * T] = t / 2.0
    img = np.clip(A * 255, 0, 255).astype(np.uint8)
    return img, rows
