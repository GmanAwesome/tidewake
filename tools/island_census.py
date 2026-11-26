"""Island census for generator v6: counts by size class x altitude band.

Main-terrain islands come from columns() ('band' id + 'island_r' + 'com'), sampled on a grid.
Stacked islands come from tidewake.skytiers.accepted(), enumerated analytically.
"""
import sys
import collections
import numpy as np

sys.path.insert(0, '.')
from tidewake.generator import Generator
from tidewake import gensettings as GS, skytiers as STI
from tidewake.config import HEX, SQ3

BANDS = ((0, 100), (100, 200), (200, 300), (300, 400), (400, 500))
CLASSES = ('huge', 'large', 'medium', 'small', 'tiny')


def band_of(alt):
    for i, (lo, hi) in enumerate(BANDS):
        if lo <= alt < hi:
            return i
    return len(BANDS) - 1


def census(seed=7, half=1500.0, version=6, stacked=True):
    g = Generator(seed, GS.normalize({'generator_version': version}))
    tab = collections.Counter()
    # main terrain: sample every 4 cells over a square of +-half world units
    step = 4
    rmax = int(half / (HEX * 1.5))
    qmax = int(half / (HEX * SQ3)) + rmax // 2
    seen = {}
    for r0 in range(-rmax, rmax, 64):
        rs = np.arange(r0, min(rmax, r0 + 64), step)
        qs = np.arange(-qmax, qmax, step)
        Q, R = np.meshgrid(qs, rs, indexing='ij')
        c = g.columns(Q.ravel(), R.ravel())
        ins = c['island_r'] > 0
        for bid, rad, com in zip(c['band'][ins], c['island_r'][ins], c['com'][ins]):
            seen[(round(float(bid), 3), round(float(rad), 1))] = (float(rad), float(com))
        sk = c['skerry']
        # skerries (main tiny islets): count sampled columns / ~10 as a rough island count
        for alt in c['top'][sk]:
            tab[('tiny', band_of(alt))] += 0.1
    for rad, com in seen.values():
        tab[(STI.size_class(rad), band_of(com))] += 1
    if stacked:
        for ti, (kind, period, *_r) in enumerate(STI.TIERS):
            n = int(half / period) + 1
            for ci in range(-n, n):
                for cj in range(-n, n):
                    a = STI.accepted(g, ti, ci, cj)
                    if a:
                        tab[(STI.size_class(a[2]), band_of(a[3]))] += 1
    return tab


def table(tab):
    lines = ['class    ' + ''.join(f'{lo:>4}-{hi:<4}' for lo, hi in BANDS) + '  total']
    for k in CLASSES:
        row = [tab.get((k, b), 0) for b in range(len(BANDS))]
        lines.append(f'{k:<8} ' + ''.join(f'{v:>9.0f}' for v in row) + f'{sum(row):>7.0f}')
    return '\n'.join(lines)


if __name__ == '__main__':
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    for v, st in ((6, False), (6, True)):
        t = census(seed, version=v, stacked=st)
        print(f'seed {seed} v{v} {"with" if st else "without"} stacked layers ({sum(t.values()):.0f} islands in 3000x3000)')
        print(table(t))
