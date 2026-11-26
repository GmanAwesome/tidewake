"""1.4.2: generator v3 shelves, sheer-cliff reduction, height range, old-save padding."""
import time
import numpy as np

from tidewake.generator import Generator
from tidewake import gensettings as GS
from tidewake.config import LAYERS, V2_LAYERS
from tidewake.generator import V2_TOP_MAX
from tidewake.hexgrid import cell_at
from tidewake.storage import pad_layers


PLAY_SEED = -1740201319
SITES = {
    'chalk_barrens': (-3246, -1298),
    'cinder_spires': (-2296, 223),
    'rose_mesas': (1376, 1522),
    'lumen_grove': (1383, 1647),
    'cloudstep_isles': (411, 2057),
}
THRESH = 6


def _gen(seed, ver):
    if ver == 1:
        return Generator(seed, None)
    if ver == 2:
        return Generator(seed, GS.normalize({}))
    return Generator(seed, GS.normalize({'generator_version': 3}))


def sheer_metric(gen, q0=0, r0=0, radius=160, thresh=THRESH):
    """Count neighbouring land columns whose surface differs by more than `thresh` layers."""
    qs, rs = np.meshgrid(
        np.arange(q0 - radius, q0 + radius + 1),
        np.arange(r0 - radius, r0 + radius + 1),
        indexing='ij',
    )
    c = gen.columns(qs, rs)
    land = c['land'] & ~c['skerry']
    top = c['top']
    seams = pairs = 0
    maxdt = 0
    for di, dj in ((1, 0), (0, 1)):
        both = land[:-di or None, :-dj or None] & land[di:, dj:]
        dt = np.abs(top[:-di or None, :-dj or None] - top[di:, dj:])
        pairs += int(both.sum())
        seams += int((both & (dt > thresh)).sum())
        if both.any():
            maxdt = max(maxdt, int(dt[both].max()))
    tops = top[land]
    return {
        'land': int(land.sum()),
        'pairs': pairs,
        'seams': seams,
        'rate': (seams / pairs) if pairs else 0.0,
        'maxdt': maxdt,
        'tmin': int(tops.min()) if tops.size else None,
        'tmax': int(tops.max()) if tops.size else None,
    }


def test_versions_keep_old_skies_on_v2():
    assert Generator(7, None).version == 1
    assert Generator(7, GS.normalize({})).version == 2
    assert Generator(7, GS.normalize({}, new=True)).version == 4
    assert 'generator_version' not in GS.normalize({})
    assert GS.normalize({}, new=True)['generator_version'] == 4
    # a 1.4.1 save (sliders, no version field) fingerprints as v2
    assert GS.fingerprint({})[0] == 2
    assert GS.fingerprint(GS.normalize({}))[0] == 2
    assert GS.fingerprint(GS.normalize({}, new=True))[0] == 4


def test_v2_stays_under_old_ceiling():
    g = _gen(7, 2)
    qs, rs = np.meshgrid(np.arange(-40, 41), np.arange(-40, 41), indexing='ij')
    c = g.columns(qs, rs)
    tops = c['top'][c['land']]
    assert int(tops.max()) <= V2_TOP_MAX
    assert int(V2_LAYERS) == 128
    assert int(LAYERS) >= 360


def test_pad_layers_grows_old_chunks():
    old = np.arange(16 * V2_LAYERS * 16, dtype=np.uint8).reshape(16, V2_LAYERS, 16)
    meta = np.ones_like(old)
    cells, meta2 = pad_layers(old, meta)
    assert cells.shape == (16, LAYERS, 16)
    assert meta2.shape == cells.shape
    assert np.array_equal(cells[:, :V2_LAYERS], old)
    assert np.all(cells[:, V2_LAYERS:] == 0)
    same, _ = pad_layers(cells, meta2)
    assert same.shape[1] == LAYERS


def test_sheer_cliffs_at_least_90_percent_rarer():
    """Large-area and playtest-site comparison of adjacent |Δtop| > 6."""
    report = []
    # two seeds, a wide origin window
    v2_seams = v3_seams = 0
    for seed in (7, PLAY_SEED):
        m2 = sheer_metric(_gen(seed, 2), radius=180)
        m3 = sheer_metric(_gen(seed, 3), radius=180)
        v2_seams += m2['seams']
        v3_seams += m3['seams']
        report.append(f"origin seed={seed} v2={m2} v3={m3}")
        assert m3['maxdt'] <= 6, f"v3 still has a steep step: {m3}"
    # the five 1.4.1 playtest sites
    g2, g3 = _gen(PLAY_SEED, 2), _gen(PLAY_SEED, 3)
    for name, (x, z) in SITES.items():
        q, r = cell_at(x, z)
        m2 = sheer_metric(g2, q, r, radius=80)
        m3 = sheer_metric(g3, q, r, radius=80)
        v2_seams += m2['seams']
        v3_seams += m3['seams']
        report.append(f"{name} v2={m2} v3={m3}")
        assert m3['maxdt'] <= 6, f"{name} v3 still has a steep step: {m3}"
    assert v2_seams > 0, 'v2 fixture produced no seams; the metric is not comparing real walls'
    reduction = 1.0 - (v3_seams / v2_seams)
    print('CLIFF METRIC')
    for line in report:
        print(line)
    print(f'TOTAL v2_seams={v2_seams} v3_seams={v3_seams} reduction={reduction*100:.1f}%')
    assert reduction >= 0.90, f'sheer-cliff reduction {reduction*100:.1f}% is under 90% (v2={v2_seams} v3={v3_seams})'


def test_v3_surfaces_reach_300_with_a_wide_spread():
    highs = []
    lows = []
    for seed in (7, PLAY_SEED, 99, 4096):
        g = _gen(seed, 3)
        qs, rs = np.meshgrid(np.arange(-600, 601, 5), np.arange(-600, 601, 5), indexing='ij')
        c = g.columns(qs, rs)
        tops = c['top'][c['land'] & ~c['skerry']]
        assert tops.size > 100
        lows.append(int(tops.min()))
        highs.append(int(tops.max()))
        print(f'height seed={seed} {int(tops.min())}-{int(tops.max())} mean={tops.mean():.0f} '
              f'p10={np.percentile(tops,10):.0f} p90={np.percentile(tops,90):.0f} '
              f'n>=300={int((tops>=300).sum())} n>=290={int((tops>=290).sum())}')
    assert max(highs) >= 300, f'no seed reached layer 300 (highs={highs})'
    assert min(lows) <= 40, f'no low islands remained (lows={lows})'
    # at least two seeds should climb to the high two-nineties
    assert sum(h >= 290 for h in highs) >= 2


def test_v3_spawn_picks_a_mid_island():
    from tidewake.session import find_spawn
    g = _gen(PLAY_SEED, 3)
    q, r, top, _sp = find_spawn(g)
    print(f'spawn q={q} r={r} top={top}')
    assert 80 <= top <= 170, f'spawn surface {top} is not in the mid window'


if __name__ == '__main__':
    t0 = time.perf_counter()
    test_versions_keep_old_skies_on_v2()
    test_v2_stays_under_old_ceiling()
    test_pad_layers_grows_old_chunks()
    test_sheer_cliffs_at_least_90_percent_rarer()
    test_v3_surfaces_reach_300_with_a_wide_spread()
    test_v3_spawn_picks_a_mid_island()
    print(f'all 1.4.2 tests passed in {time.perf_counter()-t0:.2f}s')
