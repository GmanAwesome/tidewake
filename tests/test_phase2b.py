"""Phase 2b checks, starting with the near-surface arch fix."""
import numpy as np
from tidewake.generator import Generator


def _gap_rate(gen, n=5):
    chunks = [(-20, -11), (8, -3), (0, 4), (-14, 6), (4, 0)]
    gaps = solid = 0
    for cq, cr in chunks[:n]:
        cells, _, _ = gen.generate(cq, cr)
        for a in range(16):
            for b in range(16):
                ys = np.where(cells[a, :, b] > 0)[0]
                if len(ys) == 0:
                    continue
                top = int(ys.max())
                solid += 1
                if (cells[a, max(0, top - 3):top, b] == 0).any():
                    gaps += 1
    return gaps / max(1, solid), solid


def test_v2_surface_is_solid():
    rate, solid = _gap_rate(Generator(7, {}))
    assert solid > 100
    assert rate < 0.02, f'new worlds still holey at the surface: {rate:.3f}'


def test_v1_unchanged_can_still_arch():
    # old generator path is still allowed to carve shallow arches
    rate, solid = _gap_rate(Generator(7))
    assert solid > 100
    # just a sanity bound — v1 should not be empty land
    assert rate < 0.6
