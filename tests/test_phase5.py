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


if __name__ == '__main__':
    test_skywhale_is_longer_than_it_is_chunky()
    print('ok skywhale silhouette is long and flat')
    test_wanderer_has_a_face()
    print('ok wanderer front view has a face')
    print('ALL PHASE5 UNIT TESTS PASSED')
