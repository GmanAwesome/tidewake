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


if __name__ == '__main__':
    test_skywhale_is_longer_than_it_is_chunky()
    print('ok skywhale silhouette is long and flat')
    test_wanderer_has_a_face()
    print('ok wanderer front view has a face')
    test_buried_chamber_is_lit()
    print('ok buried chamber is lit')
    print('ALL PHASE5 UNIT TESTS PASSED')
