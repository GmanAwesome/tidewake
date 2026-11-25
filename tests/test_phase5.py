"""Phase 5 cohesion checks."""
from tidewake import models as MD


def test_skywhale_is_longer_than_it_is_chunky():
    v = MD._creature('skywhale', 0.0, False)
    assert len(v) > 0
    p = v['p']
    span_x = float(p[:, 0].max() - p[:, 0].min())
    span_y = float(p[:, 1].max() - p[:, 1].min())
    span_z = float(p[:, 2].max() - p[:, 2].min())
    # a whale silhouette is long and relatively flat, not a stacked barrel
    assert span_z > span_x * 1.15, (span_x, span_y, span_z)
    assert span_z > span_y * 1.35, (span_x, span_y, span_z)




def test_wanderer_has_a_face():
    v = MD.wanderer(0.0, False)
    p = v['p']
    # eyes and mouth live on the front (-z) of the head
    head = p[(p[:, 1] > 1.08) & (p[:, 1] < 1.50)]
    front = head[head[:, 2] < -0.08]
    assert len(front) > 0, 'looking-at-you view had no front-of-head geometry'
    # some of that front geometry is darker than skin (eyes)
    import numpy as np
    cols = v['c']
    front_idx = np.where((p[:, 1] > 1.08) & (p[:, 1] < 1.50) & (p[:, 2] < -0.08))[0]
    dark = 0
    for i in front_idx:
        r, g, b = cols[i][0] / 255.0, cols[i][1] / 255.0, cols[i][2] / 255.0
        if r + g + b < 1.0:
            dark += 1
    assert dark > 0, 'front of the head had no darker eye or mouth marks'




def test_buried_chamber_is_lit():
    from tidewake import materials as MT
    from tidewake.config import LAYERS
    from tidewake.hexgrid import CHUNK
    from tidewake.structures import Stamp, build_chamber, INTACT
    import numpy as np
    W = CHUNK
    cells = np.zeros((W, LAYERS, W), dtype=np.uint8)
    meta = np.zeros_like(cells)
    cells[:, 8:30, :] = MT.ID['stone']
    top = np.full((W, W), 29, dtype=np.int32)
    bot = np.full((W, W), 8, dtype=np.int32)
    land = np.ones((W, W), dtype=bool)
    realm = np.zeros((W, W), dtype=np.int32)
    pal = dict(brick=MT.ID['stone_bricks'], tile=MT.ID['stone_tiles'],
               stone=MT.ID['stone'], lamp=MT.ID['ember_lamp'], planks=MT.ID['planks'],
               log=MT.ID['heartwood'], cloth=MT.ID['linen'], cobble=MT.ID['cobble'])
    st = Stamp(cells, meta, top, bot, land, realm, 0, 0,
               __import__('random').Random(1), INTACT, pal)
    q, r = W // 2, W // 2
    build_chamber(st, q, r, 29)
    room = cells[q-2:q+3, :, r-2:r+3]
    lamps = int((room == MT.ID['lumen_lamp']).sum() + (room == MT.ID['ember_lamp']).sum())
    assert lamps >= 2, f'chamber only had {lamps} lamps; it would still read as a dark pit'




def _cave_stats(settings, seed=7, n=5):
    import numpy as np
    from tidewake.generator import Generator
    gen = Generator(seed, settings)
    chunks = [(-20, -11), (8, -3), (0, 4), (-14, 6), (4, 0)]
    surface_gaps = solid_cols = mouths = cave_cells = body_cells = 0
    for cq, cr in chunks[:n]:
        cells, _, _ = gen.generate(cq, cr)
        A, Y, B = cells.shape
        for a in range(A):
            for b in range(B):
                col = cells[a, :, b]
                ys = np.where(col > 0)[0]
                if len(ys) == 0:
                    continue
                top = int(ys.max())
                solid_cols += 1
                if (cells[a, max(0, top - 3):top, b] == 0).any():
                    surface_gaps += 1
                # body cells below a 5-layer roof
                body = col[max(0, top - 20):max(0, top - 5)]
                body_cells += int((body > 0).sum() + (body == 0).sum())
                cave_cells += int((body == 0).sum())
                # cliff mouth: an air cell under the roof that has a neighbor column
                # with no solid at that height and no solid above it (open sky beside)
                for y in range(max(1, top - 14), max(1, top - 4)):
                    if col[y] != 0:
                        continue
                    for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        aa, bb = a + da, b + db
                        if not (0 <= aa < A and 0 <= bb < B):
                            continue
                        nb = cells[aa, :, bb]
                        if (nb[y:] == 0).all():
                            mouths += 1
                            break
    return {
        'surface': surface_gaps / max(1, solid_cols),
        'mouths_per_col': mouths / max(1, solid_cols),
        'cave_frac': cave_cells / max(1, body_cells),
        'solid': solid_cols,
    }


def test_max_caves_do_not_swiss_cheese_islands():
    mid = _cave_stats({})
    hi = _cave_stats({'cave_amount': 100, 'cave_size': 100})
    lo = _cave_stats({'cave_amount': 0, 'cave_size': 0})
    assert mid['solid'] > 100 and hi['solid'] > 100
    assert hi['surface'] < 0.03, f'max caves still punch the walking surface: {hi}'
    assert mid['surface'] < 0.02, f'default caves punch the walking surface: {mid}'
    # max still makes more cave, just not a lace of cliff holes
    assert hi['cave_frac'] > lo['cave_frac'] * 1.15, (lo, hi)
    assert hi['mouths_per_col'] < 0.55, f'max caves lace the cliffs: {hi}'


if __name__ == '__main__':
    test_skywhale_is_longer_than_it_is_chunky()
    print('ok skywhale silhouette is long and flat')
    test_wanderer_has_a_face()
    print('ok wanderer front view has a face')
    test_buried_chamber_is_lit()
    print('ok buried chamber is lit')
    test_max_caves_do_not_swiss_cheese_islands()
    print('ok max caves keep a solid shell')
    print('ALL PHASE5 UNIT TESTS PASSED')
