"""1.4.1 cohesion checks."""

def test_tutorial_dialog_only_after_talk():
    from types import SimpleNamespace
    from tidewake.session import Session

    # a slim stand-in with just the talk helpers
    class T:
        pass
    t = T()
    t.npcs = [
        {'name': 'Willow', 'x': 0, 'y': 40, 'z': 0, 'lines': ('Hello', 'More')},
        {'name': 'Bram', 'x': 20, 'y': 40, 'z': 0, 'lines': ('Wood',)},
    ]
    t.player = SimpleNamespace(x=0.4, y=40, z=0.2)
    t.talk = None
    t._npc_dist = Session._npc_dist.__get__(t)
    t.closest_npc = Session.closest_npc.__get__(t)
    t.nearby_talk = Session.nearby_talk.__get__(t)
    assert t.closest_npc().get('name') == 'Willow'
    assert t.nearby_talk() is None  # no popup until you talk
    t.app = SimpleNamespace(audio=SimpleNamespace(play=lambda *a, **k: None))
    Session.talk_npc(t, t.closest_npc())
    assert t.talk == 'Willow'
    assert t.nearby_talk()['name'] == 'Willow'
    t.player.x, t.player.z = 80, 80
    assert t.nearby_talk() is None
    assert t.talk is None


def test_title_showcase_launch_avoids_last():
    from tidewake import showcase as SC
    keys = SC.catalog_keys()
    assert len(keys) >= 2
    last = keys[0]
    seen = set()
    for _ in range(30):
        k = SC.choose_launch(last)
        assert k in keys
        assert k != last
        seen.add(k)
        last = k
    # over many launches we should visit more than one showcase
    assert len(seen) >= 2
    # rotation after a launch pick still walks the list
    start = SC._index
    SC.pick(advance=True)
    assert SC._index == start + 1


def test_mob_y_trace_does_not_shake():
    """Frame-by-frame y of a woolhop on flat ground must settle and stay put."""
    from tidewake.config import LAYER, LAYERS
    from tidewake.hexgrid import center
    from tidewake.entities import Mob
    from tidewake import materials as MT

    class World:
        def __init__(self):
            self.cells = {}
        def get(self, q, r, y):
            if y < 0 or y >= LAYERS:
                return 0
            return self.cells.get((q, r, y), 0)
        def get_meta(self, q, r, y):
            return 0
        def set(self, q, r, y, mat):
            self.cells[q, r, y] = mat

    w = World()
    for q in range(-8, 9):
        for r in range(-8, 9):
            w.set(q, r, 20, MT.ID['turf'])
    x, z = center(0, 0)
    floor = 21 * LAYER

    class P:
        def __init__(self):
            self.x, self.z, self.y = x + 12, z, floor
            self.dev_ghost = True

    traces = {}
    for label, dt, start_y in (
        ('60fps', 1 / 60, floor + 0.01),
        ('144fps', 1 / 144, floor + 0.01),
        ('30fps', 1 / 30, floor + 0.01),
        ('inside', 1 / 60, floor - 0.04),
        ('drop', 1 / 60, floor + 2.5),
    ):
        mob = Mob('woolhop', x, start_y, z)
        ys = []
        for i in range(180):
            mob.update(dt, w, P(), 0.0, True)
            ys.append(mob.y)
        traces[label] = ys
        tail = ys[-60:]
        span = max(tail) - min(tail)
        assert mob.on_ground, (label, 'never landed', ys[-5:])
        assert abs(tail[-1] - floor) < 0.02, (label, tail[-1], floor)
        assert span < 0.003, (label, 'still shaking', span, tail[0], tail[-1])
    # walking on flat ground must not bob the body
    mob = Mob('woolhop', x, floor + 0.01, z)
    mob.walking = True
    ys = []
    for i in range(180):
        mob.vx, mob.vz = 0.8, 0.3
        mob.update(1 / 60, w, P(), 0.0, True)
        ys.append(mob.y)
    tail = ys[-60:]
    span = max(tail) - min(tail)
    assert mob.on_ground and span < 0.003, ('walk shake', span, tail[0], tail[-1])
    traces['walk'] = ys
    return traces


def test_lamps_are_kept_among_many_glowcaps():
    import numpy as np
    from tidewake.config import CHUNK, LAYERS
    from tidewake import materials as MT
    from tidewake.mesher import mesh_chunk
    from tidewake.renderer import LIGHT_RAD
    from tidewake.world import World

    P = np.zeros((CHUNK + 2, LAYERS, CHUNK + 2), np.uint8)
    # a stone room with a roof, packed with glowcaps, and one lumen lamp in the corner
    P[:, 10, :] = MT.ID['stone']
    P[:, 14, :] = MT.ID['stone']
    P[:, 11:14, :] = 0
    n = 0
    for a in range(1, CHUNK + 1):
        for b in range(1, CHUNK + 1):
            if n < 60 and (a + b) % 2 == 0:
                P[a, 11, b] = MT.ID['glowcap']
                n += 1
    P[2, 12, 2] = MT.ID['lumen_lamp']
    realm = np.zeros((CHUNK, CHUNK), np.int32)
    _o, _w, L = mesh_chunk(P, realm, 0, 0)
    mids = [int(m) for m in L[:, 3]]
    assert MT.ID['lumen_lamp'] in mids, ('lamp dropped from the chunk light list', mids[:10], len(mids))

    # shader picker: a lantern a little farther than a crowd of glowcaps must still be selected
    lamp = MT.ID['lantern']
    cap = MT.ID['glowcap']
    A = []
    for i in range(40):
        A.append((0.4 + i * 0.05, 0, 0, cap))
    A.append((3.2, 0, 0, lamp))  # farther than the glowcaps, but a real lamp
    A = np.array(A, dtype=np.float64)
    d = np.linalg.norm(A[:, :3], axis=1)
    rad = np.array([LIGHT_RAD.get(int(m), 6.0) for m in A[:, 3]])
    score = d / np.maximum(rad, 1.0)
    sel = np.argsort(score)[:32]
    assert lamp in A[sel, 3], ('lantern lost to glowcaps', A[sel, 3][:8], score[-1], score[0])

    # placing a lamp dirties every chunk its light can reach
    keys = World._chunks_within(None, 2, 2, 13.0)
    assert (0, 0) in keys and len(keys) >= 4

if __name__ == '__main__':
    test_tutorial_dialog_only_after_talk()
    print('ok tutorial dialog only after right-click')
    test_title_showcase_launch_avoids_last()
    print('ok title showcase shuffles at launch')
    test_mob_y_trace_does_not_shake()
    print('ok mob y-trace is stable on the ground')
    test_lamps_are_kept_among_many_glowcaps()
    print('ok lamps stay in the light list')
    print('ALL 1.4.1 UNIT TESTS PASSED')
