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


def test_new_block_roster():
    from tidewake import materials as MT
    from tidewake import items as I
    # appended after door/ladder, never reshuffled
    assert MT.NAMES[43] == 'Door' and MT.NAMES[44] == 'Ladder'
    assert MT.N >= 100
    assert MT.IS_SLAB[MT.ID['stone_slab']] and MT.KIND[MT.ID['stone_slab']] == 'slab'
    for name in ('cedar_planks', 'chalk', 'sandstone', 'cinder', 'starstone', 'heather',
                 'ember_lamp', 'green_glass', 'thatch', 'stone_bricks', 'violet_glass'):
        assert name in MT.ID, name
        assert MT.ID[name] in I.ITEMS


def test_new_recipes():
    from tidewake import materials as MT
    from tidewake import items as I
    results = {r[1][0] for r in I.RECIPES}
    for name in ('cedar_planks', 'stone_bricks', 'ember_lamp', 'green_glass', 'stone_slab', 'thatch'):
        assert MT.ID[name] in results, name


def test_slab_collision():
    from tidewake import materials as MT
    from tidewake.player import Player
    from tidewake.config import LAYER

    class W:
        def __init__(self):
            self.c = {}
        def get(self, q, r, y):
            return self.c.get((q, r, y), 0)

    w = W()
    w.c[(0, 0, 10)] = MT.ID['stone_slab']
    p = Player(0.0, 10 * LAYER, 0.0)
    assert p.collides(w, 0.0, 10 * LAYER + 0.01, 0.0)
    assert not p.collides(w, 0.0, 10.5 * LAYER + 0.001, 0.0)
    w.c[(0, 0, 10)] = MT.ID['stone']
    assert p.collides(w, 0.0, 10.6 * LAYER, 0.0)
    assert not p.collides(w, 0.0, 11 * LAYER + 0.001, 0.0)


def test_new_biome_blocks():
    import numpy as np
    from tidewake import materials as MT
    from tidewake.generator import Generator
    seen = set()
    want = {MT.ID[k] for k in ('chalk', 'sandstone', 'cinder', 'starstone', 'heather',
                               'cedar_heartwood', 'pale_heartwood', 'salt_block')}
    for seed in (7, 21, 42):
        g = Generator(seed, {})
        for cq in range(-20, 21, 5):
            for cr in range(-20, 21, 5):
                cells, _, _ = g.generate(cq, cr)
                seen.update(int(x) for x in np.unique(cells))
                if want <= seen:
                    return
    missing = [MT.NAMES[i] for i in want if i not in seen]
    raise AssertionError(f'missing biome blocks: {missing}')


def test_tinted_glass_is_glass():
    from tidewake import materials as MT
    for name in ('glass', 'green_glass', 'amber_glass', 'violet_glass'):
        assert MT.IS_GLASS[MT.ID[name]]
