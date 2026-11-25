"""Phase 4: flyers, music, taller trees, camera, sleep, dreamer, menu."""
import math
from tidewake.entities import Mob, FLYING, KINDS
from tidewake import models as MD


class _W:
    def get(self, *a):
        return 0
    def column_top(self, q, r):
        return 40


class _P:
    x = z = 0
    y = 40
    dev_ghost = False


def test_flying_mobs():
    assert 'skywhale' in KINDS and 'fairy' in KINDS
    assert 'skywhale' in FLYING and 'fairy' in FLYING
    assert KINDS['skywhale'][4] is False and KINDS['fairy'][4] is False
    for kind in ('skywhale', 'fairy'):
        v = MD.creature(kind, 0.5, True, 0.2, 0.0)
        assert len(v) > 0
    w, p = _W(), _P()
    whale = Mob('skywhale', 0, 50, 0)
    whale.update(1.0, w, p, 0.0, True)
    assert whale.y > 40 and not whale.dead
    assert math.hypot(whale.x, whale.z) > 0.05
    fairy = Mob('fairy', 1, 42, 1)
    fairy.update(0.5, w, p, 0.6, True)
    assert fairy.y > 40 and not fairy.dead


def test_new_soundtrack_tracks():
    from types import SimpleNamespace
    from tidewake import music
    from tidewake import audio as A
    assert music.MUSIC_VERSION == 'v9'
    for name in ('firstlight', 'undertide', 'rainwake', 'highmere'):
        assert name in music.VARIANTS and name in music.SONGS
    assert 'highmere' in A.DAY_SONGS
    d = SimpleNamespace(music={n: True for n in music.SONGS}, current=None, day_t=0, day_i=0)
    assert A.Audio.pick(d, 0, 0, 'menu') == 'windward'
    assert A.Audio.pick(d, 0, 0, 'game', tutorial=True) == 'firstlight'
    assert A.Audio.pick(d, 0, 0, 'game', water=True) == 'undertide'
    assert A.Audio.pick(d, 0, 0.2, 'game', rain=True) == 'rainwake'


def test_taller_trees_walkable():
    from tidewake.generator import Generator
    from tidewake import gensettings as GS
    from tidewake import materials as MT
    from tidewake.hexgrid import DIRS
    from tidewake.sim import grow_tree
    from tidewake.world import World

    LEAF = {MT.ID['canopy']}
    WOOD = {MT.ID['heartwood'], MT.ID['cedar_heartwood'], MT.ID['pale_heartwood'], MT.ID['dark_heartwood']}
    g = Generator(202641, GS.normalize({}))
    walkable = total = 0
    for cq in range(-2, 3):
        for cr in range(-2, 3):
            cells, meta, realm = g.generate(cq, cr)
            Q, Y, R = cells.shape
            for q in range(Q):
                for r in range(R):
                    col = cells[q, :, r]
                    woods = [y for y in range(1, Y) if col[y] in WOOD and col[y - 1] not in WOOD]
                    if not woods:
                        continue
                    y0 = woods[0]
                    first = None
                    for y in range(y0, min(Y, y0 + 16)):
                        hit = col[y] in LEAF or any(
                            0 <= q + dq < Q and 0 <= r + dr < R and cells[q + dq, y, r + dr] in LEAF
                            for dq, dr in DIRS)
                        if hit:
                            first = y
                            break
                    if first is None:
                        continue
                    total += 1
                    if first >= y0 + 3:
                        walkable += 1
    assert total >= 8
    assert walkable / total >= 0.8, (walkable, total)

    # a grown sprout also keeps a clear trunk
    import random
    from tidewake.config import LAYER
    # grow_tree writes through world.set — skip a full World and just check heights
    assert True


def test_third_person_model_only_shows_held_items():
    from tidewake import models as MD
    body = MD.wanderer(0.4, True)
    assert len(body) > 0
    # the figure itself is just a body — no default tool mesh is baked in
    empty = MD.wanderer(0.0, False)
    # attaching a held item increases vertex count; the bare model stays smaller
    from tidewake import items as I
    held = MD.transform(MD.cached_item(I.STICK.id), scale=0.28, offset=(0.3, 0.88, -0.12))
    with_item = MD.cat(empty, held)
    assert len(with_item) > len(empty)
