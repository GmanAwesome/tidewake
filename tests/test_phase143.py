"""1.4.3: v4 discrete islands (no 12-cell cuts or intersections) and wanderer hips."""
import math
import time

import numpy as np

from tidewake.generator import Generator
from tidewake import gensettings as GS
from tidewake.hexgrid import cell_at
from tidewake import models as MD


REPORT_SEED = -857535443
SITES = {
    'cedar_highlands': (-29.99, -46.92),
    'frostglass': (-245.28, 43.43),
    'chalk_barrens_near': (-264.17, -23.51),
    'cloudstep_isles_far': (2512.22, -1386.21),
    'chalk_barrens_high': (2415.93, -1112.58),
    'cloudstep_low': (97.86, -107.82),
    'verdigris_canyons': (-4.06, -61.76),
}
MANY_SEEDS = [
    REPORT_SEED, 7, -1740201319, 99, 12345, -99, 2026, 42, 1001, -555,
    314159, -777, 88, 123, -2024, 555, 999, -8,
]


def _v4(seed):
    return Generator(seed, GS.normalize({'generator_version': 4}))


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


def underside_flat_runs(land, bottom, min_run=12):
    """Long colinear underside silhouette with a nearly constant bottom."""
    H, W = land.shape
    found = []
    faces = [
        ((1, 0), (0, 1), 'q+'),
        ((0, 1), (1, 0), 'r+'),
        ((1, -1), (1, 1), 's+'),
    ]
    for (dq, dr), (wq, wr), axis in faces:
        vis = np.zeros(land.shape, bool)
        for i in range(H):
            for j in range(W):
                if vis[i, j] or not land[i, j]:
                    continue
                ni, nj = i + dq, j + dr
                if not (0 <= ni < H and 0 <= nj < W) or land[ni, nj]:
                    continue
                run = [(i, j)]
                ci, cj = i + wq, j + wr
                while 0 <= ci < H and 0 <= cj < W and land[ci, cj]:
                    nci, ncj = ci + dq, cj + dr
                    if not (0 <= nci < H and 0 <= ncj < W) or land[nci, ncj]:
                        break
                    if abs(int(bottom[ci, cj]) - int(bottom[run[0][0], run[0][1]])) > 2:
                        break
                    run.append((ci, cj))
                    ci += wq
                    cj += wr
                if len(run) < min_run:
                    continue
                for a, b in run:
                    vis[a, b] = True
                found.append({'len': len(run), 'axis': axis, 'ij0': run[0]})
    return found


def volume_overlaps(c, rad=1):
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


def _metrics(gen, q0, r0, radius=160):
    qs, rs = np.meshgrid(np.arange(q0 - radius, q0 + radius + 1),
                         np.arange(r0 - radius, r0 + radius + 1), indexing='ij')
    c = gen.columns(qs, rs)
    land, top = c['land'], c['top']
    seams = 0
    maxdt = 0
    for axis in ('q', 'r', 's'):
        if axis == 'q':
            L1, L2, T1, T2 = land[:-1, :], land[1:, :], top[:-1, :], top[1:, :]
        elif axis == 'r':
            L1, L2, T1, T2 = land[:, :-1], land[:, 1:], top[:, :-1], top[:, 1:]
        else:
            L1, L2, T1, T2 = land[:-1, 1:], land[1:, :-1], top[:-1, 1:], top[1:, :-1]
        both = L1 & L2
        dt = np.abs(T1.astype(int) - T2.astype(int))
        if both.any():
            maxdt = max(maxdt, int(dt[both].max()))
            seams += int((both & (dt > 6)).sum())
    tmax = int(top[land].max()) if land.any() else 0
    return c, seams, maxdt, tmax


def test_reported_sites_have_no_long_straight_cuts():
    """v4 at the seven 1.4.3 report sites: no 12-cell walls, coasts, or undersides."""
    gen = _v4(REPORT_SEED)
    long_cuts = []
    unders = []
    overlaps = 0
    for name, (x, z) in SITES.items():
        q, r = cell_at(x, z)
        qs, rs, c = _window(gen, q, r, 90)
        runs = straight_cut_runs(c['land'], c['top'], c['bottom'], min_run=12)
        und = underside_flat_runs(c['land'], c['bottom'], min_run=12)
        ov = volume_overlaps(c, rad=1)
        overlaps += ov
        long_cuts.extend((name, d) for d in runs)
        unders.extend((name, d) for d in und)
        print(f"{name} land={int(c['land'].sum())} runs12={len(runs)} "
              f"under12={len(und)} max={max((d['len'] for d in runs), default=0)} overlaps={ov}")
    assert overlaps == 0, f'overlapping island volumes still present: {overlaps}'
    assert not long_cuts, f'straight cut runs of 12+ cells remain: {long_cuts}'
    assert not unders, f'flat underside cuts of 12+ cells remain: {unders}'


def test_many_seeds_have_no_ruler_cuts_or_overlaps():
    bad = []
    for seed in MANY_SEEDS:
        for q, r in ((0, 0), (1800, -800)):
            qs, rs, c = _window(_v4(seed), q, r, 90)
            runs = straight_cut_runs(c['land'], c['top'], c['bottom'], min_run=12)
            und = underside_flat_runs(c['land'], c['bottom'], min_run=12)
            ov = volume_overlaps(c, rad=1)
            print(f'seed={seed} qr=({q},{r}) runs12={len(runs)} under12={len(und)} '
                  f'max={max((d["len"] for d in runs+und), default=0)} overlaps={ov}')
            if ov or runs or und:
                bad.append((seed, q, r, ov, runs, und))
    assert not bad, f'ruler cuts or overlaps on v4 seeds: {bad}'


def test_v4_is_walkable_and_reaches_300():
    """Keep the 1.4.2 goals: neighbour steps <= 6, tops up to about 300."""
    peak = 0
    for seed in MANY_SEEDS:
        gen = _v4(seed)
        c, seams, maxdt, tmax = _metrics(gen, 0, 0, 180)
        c2, s2, m2, t2 = _metrics(gen, 1800, -800, 140)
        peak = max(peak, tmax, t2)
        print(f'seed={seed} seams={seams+s2} maxdt={max(maxdt, m2)} tmax={max(tmax, t2)}')
        assert seams + s2 == 0 and max(maxdt, m2) <= 6, f'v4 sheer on {seed}: seams={seams+s2} maxdt={max(maxdt,m2)}'
    assert peak >= 298, f'v4 peaks only reach {peak}, want about 300'


def test_old_versions_and_tutorial_stay_pinned():
    assert Generator(7, None).version == 1
    assert Generator(7, GS.normalize({})).version == 2
    assert Generator(7, GS.normalize({'generator_version': 3})).version == 3
    assert Generator(7, GS.normalize({}, new=True)).version == 4
    # lesson island dispatch is unchanged (tutorial flag, not the generator class)
    from tidewake import tutorial as TUT
    assert hasattr(TUT, 'generate_chunk')


def test_wanderer_is_unclothed_base_body():
    """Uniform skin tone, cheeks sunk 40–60% into the hips, centre cleft, no outfit colours."""
    from tidewake.mesher import VERT
    v = MD.wanderer(0.0, walking=False)
    assert v.dtype == VERT
    assert len(v) > 0
    rgb = v['c'][:, :3].astype(int)
    cloth = ((rgb[:, 0] - 117) ** 2 + (rgb[:, 1] - 132) ** 2 + (rgb[:, 2] - 158) ** 2) < 40 ** 2
    assert int(cloth.sum()) == 0, f'{int(cloth.sum())} verts still use the old outfit colour'
    body = (rgb[:, 0] > rgb[:, 2]) & (rgb[:, 1] > 80) & (rgb[:, 0] > 120)
    assert body.mean() > 0.6, f'warm body-tone fraction {body.mean():.2f} is too low'
    hips = (v['p'][:, 1] > 0.44) & (v['p'][:, 1] < 0.76)
    sunk = hips & (v['p'][:, 2] > 0.08) & (v['p'][:, 2] < 0.22)
    lift = hips & (v['p'][:, 2] > 0.22)
    assert int(sunk.sum()) > 0, 'cheeks are not sunk into the lower torso'
    assert int(lift.sum()) > 0, 'missing the rounded back lift'
    # stay within the hip width; do not hang as separate side boxes below the torso
    cheek = hips & (v['p'][:, 2] > 0.16)
    assert float(np.abs(v['p'][cheek, 0]).max()) <= 0.17, 'cheeks stick out past the hips'
    assert float(v['p'][cheek, 1].min()) >= 0.44, 'cheeks hang below the base of the torso'
    cleft = hips & (np.abs(v['p'][:, 0]) < 0.06) & (v['p'][:, 2] > 0.10)
    assert int(cleft.sum()) > 0, 'missing the centre cleft'
    v2 = MD.wanderer(0.4, walking=True)
    assert len(v2) >= len(v)
    assert MD.wanderer(0.0, walking=False) is v


def test_v4_has_large_and_small_islands():
    """v4 skies mix continent-scale landmasses with medium and small islands."""
    spans = []
    smalls = 0
    for seed in (REPORT_SEED, 7, 99, -8, 42):
        gen = _v4(seed)
        qs, rs, c = _window(gen, 0, 0, 200)
        land, band = c['land'], c['band']
        for bid in np.unique(band[land]):
            if bid < 0:
                continue
            mask = land & (band == bid)
            n = int(mask.sum())
            if n < 4:
                continue
            ii, jj = np.where(mask)
            span = max(int(qs[ii, jj].max() - qs[ii, jj].min()),
                       int(rs[ii, jj].max() - rs[ii, jj].min()))
            spans.append((seed, int(bid), n, span))
            if n <= 80:
                smalls += 1
        print(f'seed={seed} islands={sum(1 for s in spans if s[0]==seed)} '
              f'maxspan={max((s[3] for s in spans if s[0]==seed), default=0)} '
              f'maxcells={max((s[2] for s in spans if s[0]==seed), default=0)}')
    max_span = max((s[3] for s in spans), default=0)
    assert max_span >= 80, f'no large island (max span {max_span} cells); want hundreds across'
    assert smalls >= 3, f'only {smalls} small islands; want a size mix'


def test_title_showcases_stay_on_v3():
    """Hand-built title scenes keep the v3 land they were sited on."""
    from tidewake.showcase import catalog, Showcase
    from tidewake import showcase as SH
    for spec in SH.SEED_SHOWS:
        data = dict(spec)
        data.setdefault('kind', 'seed')
        data.setdefault('blocks', [])
        if data.get('gen') is None:
            data['gen'] = GS.normalize({'generator_version': 3})
        sc = Showcase(data)
        assert int(sc.gen['generator_version']) == 3, f"{spec['name']} drifted off v3"
    import json
    from pathlib import Path
    for path in Path('assets/showcase').glob('*.json'):
        sc = Showcase.load(path)
        assert int(sc.gen['generator_version']) == 3, f'{path.name} drifted off v3'


if __name__ == '__main__':

    t0 = time.perf_counter()
    test_old_versions_and_tutorial_stay_pinned()
    test_wanderer_is_unclothed_base_body()
    test_reported_sites_have_no_long_straight_cuts()
    test_many_seeds_have_no_ruler_cuts_or_overlaps()
    test_v4_is_walkable_and_reaches_300()
    test_v4_has_large_and_small_islands()
    test_title_showcases_stay_on_v3()
    print(f'all 1.4.3 tests passed in {time.perf_counter()-t0:.2f}s')
