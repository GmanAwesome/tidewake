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


if __name__ == '__main__':
    test_skywhale_is_longer_than_it_is_chunky()
    print('ok skywhale silhouette is long and flat')
    print('ALL PHASE5 UNIT TESTS PASSED')
