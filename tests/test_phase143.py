"""1.4.3: straight-cut / overlapping-island detection, and unclothed wanderer."""
import math
import time

import numpy as np

from tidewake.generator import Generator
from tidewake import gensettings as GS
from tidewake.hexgrid import cell_at
from tidewake import models as MD


REPORT_SEED = -857535443
# player-reported cutoff sites (world x, z) on seed -857535443
SITES = {
    'cedar_highlands': (-29.99, -46.92),
    'frostglass': (-245.28, 43.43),
    'chalk_barrens_near': (-264.17, -23.51),
    'cloudstep_isles_far': (2512.22, -1386.21),
    'chalk_barrens_high': (2415.93, -1112.58),
    'cloudstep_low': (97.86, -107.82),
    'verdigris_canyons': (-4.06, -61.76),
}


def _v3(seed):
    return Generator(seed, GS.normalize({'generator_version': 3}))


def straight_cut_runs(land, top, bottom, min_run=10):
    """Colinear land-to-air (or huge step) faces along the three hex axes."""
    H, W = land.shape
    found = []
    faces = [
        ((1, 0), (0, 1), 'q+'),
        ((-1, 0), (0, 1), 'q-'),
        ((0, 1), (1, 0), 'r+'),
        ((0, -1), (1, 0), 'r-'),
        ((1, -1), (1, 1), 's+'),
        ((-1, 1), (1, 1), 's-'),
    ]
    for (dq, dr), (wq, wr), axis in faces:
        vis = np.zeros(land.shape, bool)
        for i in range(H):
            for j in range(W):
                if vis[i, j] or not land[i, j]:
                    continue
                ni, nj = i + dq, j + dr
                if not (0 <= ni < H and 0 <= nj < W):
                    continue
                nland = land[ni, nj]
                step = abs(int(top[i, j]) - int(top[ni, nj])) if nland else 99
                if nland and step <= 6:
                    continue
                run = [(i, j)]
                ci, cj = i + wq, j + wr
                while 0 <= ci < H and 0 <= cj < W and land[ci, cj]:
                    nci, ncj = ci + dq, cj + dr
                    if not (0 <= nci < H and 0 <= ncj < W):
                        break
                    nl = land[nci, ncj]
                    st = abs(int(top[ci, cj]) - int(top[nci, ncj])) if nl else 99
                    if nl and st <= 6:
                        break
                    run.append((ci, cj))
                    ci += wq
                    cj += wr
                if len(run) < min_run:
                    continue
                for a, b in run:
                    vis[a, b] = True
                kind = 'sheer_edge'
                for a, b in run:
                    for k in range(2, 8):
                        ii, jj = a + dq * k, b + dr * k
                        if 0 <= ii < H and 0 <= jj < W and land[ii, jj]:
                            kind = 'canyon'
                            break
                    if kind == 'canyon':
                        break
                bots = [int(bottom[a, b]) for a, b in run]
                found.append({'len': len(run), 'kind': kind, 'axis': axis,
                              'ij0': run[0], 'ij1': run[-1],
                              'flat_bot': (max(bots) - min(bots)) <= 2})
    return found


def volume_overlaps(c, rad=3):
    """Nearby different-band land columns whose [bottom, top] ranges collide."""
    land, band, top, bot = c['land'], c['band'], c['top'], c['bottom']
    H, W = land.shape
    hits = 0
    idx = np.argwhere(land)
    for i, j in idx[::3]:
        t1, b1, bd1 = int(top[i, j]), int(bot[i, j]), int(band[i, j])
        for di in range(-rad, rad + 1):
            for dj in range(-rad, rad + 1):
                if di == 0 and dj == 0 or abs(di) + abs(dj) > rad + 1:
                    continue
                ii, jj = i + di, j + dj
                if not (0 <= ii < H and 0 <= jj < W) or not land[ii, jj]:
                    continue
                if int(band[ii, jj]) == bd1:
                    continue
                t2, b2 = int(top[ii, jj]), int(bot[ii, jj])
                if not (t1 < b2 - 8 or t2 < b1 - 8):
                    hits += 1
    return hits


def _window(gen, q0, r0, rad=90):
    qs, rs = np.meshgrid(np.arange(q0 - rad, q0 + rad + 1),
                         np.arange(r0 - rad, r0 + rad + 1), indexing='ij')
    return qs, rs, gen.columns(qs, rs)


def test_reported_sites_have_no_long_straight_cuts():
    """Seed -857535443 had 25- and 18-cell Voronoi-edge walls at these sites.

    After 1.4.3, overlapping shelves are cleared by a noisy sky gap (no
    interpenetrating volumes) and coastlines are nibbled so a zero-contour
    cannot run as a long hex-axis cut plane.
    """
    gen = _v3(REPORT_SEED)
    long_cuts = []
    canyons = []
    overlaps = 0
    for name, (x, z) in SITES.items():
        q, r = cell_at(x, z)
        qs, rs, c = _window(gen, q, r, 90)
        runs = straight_cut_runs(c['land'], c['top'], c['bottom'], min_run=10)
        ov = volume_overlaps(c)
        overlaps += ov
        for d in runs:
            rec = (name, d)
            if d['len'] >= 18:
                long_cuts.append(rec)
            if d['kind'] == 'canyon' and d['len'] >= 16:
                canyons.append(rec)
        print(f"{name} land={int(c['land'].sum())} runs>={10}={len(runs)} "
              f"max={max((d['len'] for d in runs), default=0)} overlaps={ov}")
        for d in sorted(runs, key=lambda x: -x['len'])[:4]:
            print(f"  {d['len']:3d} {d['kind']:12s} {d['axis']}")
    assert overlaps == 0, f'overlapping shelf volumes still present: {overlaps}'
    assert not long_cuts, f'straight cut walls of 18+ cells remain: {long_cuts}'
    assert not canyons, f'straight canyon cuts of 12+ cells remain: {canyons}'


def test_other_seeds_have_no_ruler_cuts_or_overlaps():
    gen_sites = [(7, 0, 0), (-1740201319, 0, 0), (99, 80, -40)]
    bad = []
    for seed, q, r in gen_sites:
        qs, rs, c = _window(_v3(seed), q, r, 80)
        runs = straight_cut_runs(c['land'], c['top'], c['bottom'], min_run=18)
        ov = volume_overlaps(c)
        long = [d for d in runs if d['len'] >= 18]
        print(f'seed={seed} long18={len(long)} max={max((d["len"] for d in runs), default=0)} overlaps={ov}')
        if ov or long:
            bad.append((seed, ov, long))
    assert not bad, f'ruler cuts or overlaps on other seeds: {bad}'


def test_wanderer_is_unclothed_base_body():
    """The third-person figure is a uniform skin tone with no outfit colours."""
    from tidewake.mesher import VERT
    v = MD.wanderer(0.0, walking=False)
    assert v.dtype == VERT
    assert len(v) > 0
    rgb = v['c'][:, :3].astype(int)
    # old default outfit was a blue-grey cloth (0.46, 0.52, 0.62)
    cloth = ((rgb[:, 0] - 117) ** 2 + (rgb[:, 1] - 132) ** 2 + (rgb[:, 2] - 158) ** 2) < 40 ** 2
    assert int(cloth.sum()) == 0, f'{int(cloth.sum())} verts still use the old outfit colour'
    # most of the body is the neutral skin tone (0.90, 0.74, 0.62) ~= (229, 189, 158)
    body = (rgb[:, 0] > rgb[:, 2]) & (rgb[:, 1] > 80) & (rgb[:, 0] > 120)
    assert body.mean() > 0.6, f'warm body-tone fraction {body.mean():.2f} is too low'
    # two hip-cheek blocks sit on the back (+z) around hip height
    back_hips = (v['p'][:, 2] > 0.10) & (v['p'][:, 1] > 0.40) & (v['p'][:, 1] < 0.70)
    assert int(back_hips.sum()) > 0, 'missing the cartoony hip-cheek blocks'
    v2 = MD.wanderer(0.4, walking=True)
    assert len(v2) >= len(v)
    assert MD.wanderer(0.0, walking=False) is v


if __name__ == '__main__':
    t0 = time.perf_counter()
    test_reported_sites_have_no_long_straight_cuts()
    test_other_seeds_have_no_ruler_cuts_or_overlaps()
    test_wanderer_is_unclothed_base_body()
    print(f'all 1.4.3 tests passed in {time.perf_counter()-t0:.2f}s')
