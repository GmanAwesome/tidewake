"""1.4.4 late: generator v6 (islands +50%, 500-layer columns, grand structures, tiny islets)."""
import hashlib
import random

import numpy as np

from tidewake.config import LAYERS, CHUNK
from tidewake import gensettings as GS, generator as GEN, grand as GR
from tidewake.generator import Generator
from tidewake.hexgrid import cell_at

# v5 output recorded before LAYERS grew to 500 (first 360 layers, 5x5 chunks).
V5 = {-1565669544: ('481dd2795d7a206e75d08ef9e22fbc2dff9be140', -1603, -2679),
      7: ('d0add92b7741e35b9d1da4f551240708f0b2f9bd', 0, 0)}


def test_columns_are_500_and_old_ceiling_fixed():
    assert LAYERS == 500
    assert GEN.TOP_MAX == 342 and GEN.TOP_MAX_V6 == 482
    assert GS.CURRENT == 6 and GS.normalize({}, new=True)['generator_version'] == 6


def test_v5_output_unchanged():
    for seed, (want, x, z) in V5.items():
        g = Generator(seed, GS.normalize({'generator_version': 5}))
        q, r = cell_at(x, z)
        cq, cr = q // 16, r // 16
        h = hashlib.sha1()
        for a in range(cq - 2, cq + 3):
            for b in range(cr - 2, cr + 3):
                c, m, rl = g.generate(a, b)
                assert not c[:, 360:, :].any()
                h.update(np.ascontiguousarray(c[:, :360, :]).tobytes())
                h.update(np.ascontiguousarray(m[:, :360, :]).tobytes())
                h.update(rl.tobytes())
        assert h.hexdigest() == want, seed


def _span(g, rad=1400, step=8):
    qs = np.arange(-rad, rad, step)
    Q, R = np.meshgrid(qs, qs, indexing='ij')
    c = g.columns(Q.ravel(), R.ravel())
    land = c['land'] & ~c['skerry']
    return land, c


def test_v6_islands_bigger_and_taller():
    l5, c5 = _span(Generator(7, GS.normalize({'generator_version': 5})))
    l6, c6 = _span(Generator(7, GS.normalize({'generator_version': 6})))
    assert c6['top'][l6].max() > 420 >= c5['top'][l5].max()
    assert c6['top'][l6].max() <= GEN.TOP_MAX_V6
    # largest radius of any island tier is 1.5x: compare the stored best radius
    r5 = c5['e'][l5].size
    assert l6.mean() > 0.6 * l5.mean()            # similar coverage, fewer but larger islands
    sk5, sk6 = c5['skerry'], c6['skerry']
    assert sk6.mean() >= sk5.mean()               # a few more tiny islets
    assert np.ptp(c6['top'][sk6]) > 2 * np.ptp(c5['top'][sk5])   # at many heights


def test_grand_structures_only_in_v6_and_deterministic():
    g6 = Generator(7, GS.normalize({'generator_version': 6}))
    g5 = Generator(7, GS.normalize({'generator_version': 5}))
    kinds = set()
    for rq in range(-4, 4):
        for rr in range(-4, 4):
            s = GR.site(g6, rq, rr)
            if s:
                kinds.add(s['kind'])
    assert 'hot_air_balloon' in kinds and len(kinds) >= 4, kinds
    # a balloon builds the same twice and differs between seeds
    s = next(GR.site(g6, a, b) for a in range(-6, 6) for b in range(-6, 6)
             if (GR.site(g6, a, b) or {}).get('kind') == 'hot_air_balloon')
    c1 = GR.Canvas(g6); i1 = GR.build_hot_air_balloon(c1, random.Random(s['seed']), s['q'], s['r'], s['y'])
    c2 = GR.Canvas(g6); i2 = GR.build_hot_air_balloon(c2, random.Random(s['seed']), s['q'], s['r'], s['y'])
    assert c1.cells == c2.cells and i1 == i2
    shapes = set()
    for k in range(12):
        c = GR.Canvas(g6)
        info = GR.build_hot_air_balloon(c, random.Random(k), 0, 0, 200)
        shapes.add((info['shape'], info['pattern'], info['gondola']))
        assert len(c.cells) > 1200 and info['R'] >= 10
        assert len({m for m, _ in c.cells.values()}) >= 8      # many dyed blocks
    assert len(shapes) >= 8
    # stamped parts of one structure line up across chunk edges
    q, r = s['q'], s['r']
    cq, cr = q // CHUNK, r // CHUNK
    hits = 0
    for a in (cq - 1, cq, cq + 1):
        for b in (cr - 1, cr, cr + 1):
            cells, _, _ = g6.generate(a, b)
            c5, _, _ = g5.generate(a, b)
            hits += int(((cells > 0) & (c5 == 0)).sum())
    assert hits > 500


def test_trimmed_mesher_matches_full():
    from tidewake.mesher import pad_chunk, mesh_chunk, _mesh_core, VERT
    g = Generator(-1565669544, GS.normalize({'generator_version': 5}))
    q, r = cell_at(-1603, -2679)
    cq, cr = q // 16, r // 16
    ch = {}

    def get(a, b, i):
        if (a, b) not in ch:
            ch[(a, b)] = g.generate(a, b)
        return ch[(a, b)][i]
    P = pad_chunk(lambda a, b: get(a, b, 0), cq, cr)
    Pm = pad_chunk(lambda a, b: get(a, b, 1), cq, cr)
    o1, w1, L1 = _mesh_core(P, get(cq, cr, 2), cq, cr, Pm, 0)
    o2, w2, L2 = mesh_chunk(P, get(cq, cr, 2), cq, cr, Pm)
    A, B = np.frombuffer(o1, VERT), np.frombuffer(o2, VERT)
    assert len(A) == len(B) and np.allclose(A['p'], B['p'], atol=1e-3) and (A['c'] == B['c']).all()
    assert np.allclose(L1, L2, atol=1e-3) and len(w1) == len(w2)


if __name__ == '__main__':
    test_columns_are_500_and_old_ceiling_fixed(); print('ok 500 layers, fixed old ceiling, v6 current')
    test_v5_output_unchanged(); print('ok v5 unchanged (incl. showcase seed -1565669544)')
    test_v6_islands_bigger_and_taller(); print('ok v6 islands bigger, taller, more islets')
    test_grand_structures_only_in_v6_and_deterministic(); print('ok grand structures')
    test_trimmed_mesher_matches_full(); print('ok trimmed mesher')
