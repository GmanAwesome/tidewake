"""Find long thin vertical columns of non-water blocks (pillars) in generated v6 chunks.

A pillar cell is solid, not water, and has no solid horizontal neighbour in the same layer.
Runs of >= MIN_RUN such cells stacked in one column are reported with the material mix.
"""
import sys
import collections
import numpy as np

sys.path.insert(0, '.')
from tidewake.generator import Generator
from tidewake import gensettings as GS, materials as MT
from tidewake.mesher import pad_chunk

MIN_RUN = 10
INTENDED = {MT.ID['dormant_spire']} if 'dormant_spire' in MT.ID else set()   # landmarks, on purpose
DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1))


def scan(seed, chunks, version=6):
    g = Generator(seed, GS.normalize({'generator_version': version}))
    cache = {}

    def get(a, b):
        if (a, b) not in cache:
            cache[(a, b)] = g.generate(a, b)[0]
        return cache[(a, b)]
    hits = []
    for cq, cr in chunks:
        P = pad_chunk(lambda a, b: get(a, b), cq, cr)       # (18, L, 18) with a 1-cell border
        solid = (P > 0) & ~MT.IS_WATER[P]
        nb = np.zeros_like(solid)
        for dq, dr in DIRS:
            nb |= np.roll(np.roll(solid, dq, 0), dr, 2)
        lone = solid & ~nb
        core = lone[1:-1, :, 1:-1]
        cc = P[1:-1, :, 1:-1]
        for i, k in zip(*np.nonzero(core.sum(1) >= MIN_RUN)):
            col = core[i, :, k]
            y = 0
            L = len(col)
            while y < L:
                if col[y]:
                    y0 = y
                    while y < L and col[y]:
                        y += 1
                    if y - y0 >= MIN_RUN and not (set(cc[i, y0:y, k].tolist()) & INTENDED):
                        mats = collections.Counter(MT.NAMES[m] for m in cc[i, y0:y, k])
                        hits.append((cq, cr, i, k, y0, y - 1, dict(mats.most_common(3))))
                else:
                    y += 1
    return hits


if __name__ == '__main__':
    seeds = [int(s) for s in sys.argv[1:]] or [7, -1565669544, 2024]
    total = 0
    for s in seeds:
        chunks = [(a, b) for a in range(-12, 12, 2) for b in range(-12, 12, 2)]
        h = scan(s, chunks)
        total += len(h)
        kinds = collections.Counter(next(iter(x[6])) for x in h)
        print('seed', s, 'chunks', len(chunks), 'pillars', len(h), dict(kinds.most_common(8)))
        for x in h[:6]:
            print('  ', x)
    print('TOTAL', total)
