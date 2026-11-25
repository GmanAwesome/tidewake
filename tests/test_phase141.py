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

def _hex_uv(x, z):
    """Same mapping the chunk shader uses for a top face."""
    from tidewake.hexgrid import cell_at, center
    q, r = cell_at(x, z)
    cx, cz = center(q, r)
    return (x - cx) / (3 ** 0.5) + 0.5, (z - cz) * 0.5 + 0.5


def test_top_uvs_are_hex_centered():
    from tidewake.hexgrid import center, CORNERS
    for q, r in ((0, 0), (3, -2), (-4, 7), (11, 11)):
        cx, cz = center(q, r)
        u, v = _hex_uv(cx, cz)
        assert abs(u - 0.5) < 1e-9 and abs(v - 0.5) < 1e-9, (q, r, u, v)
        for dx, dz in CORNERS:
            u, v = _hex_uv(cx + dx, cz + dz)
            assert 0.0 - 1e-9 <= u <= 1.0 + 1e-9
            assert 0.0 - 1e-9 <= v <= 1.0 + 1e-9
        # a point halfway to a neighbour stays inside this tile (no mid-hex wrap)
        u, v = _hex_uv(cx + 0.4, cz)
        assert 0.0 < u < 1.0 and 0.0 < v < 1.0, (q, r, u, v)


def test_side_faces_carry_a_vertical_v():
    import numpy as np
    from tidewake.mesher import _faces_side
    from tidewake.config import LAYER
    out = _faces_side(
        np.array([0.0]), np.array([0.0]),
        np.array([2 * LAYER]), np.array([3 * LAYER]),
        np.array([1.0]), 0,
        np.array([[1.0, 1.0, 1.0]]), np.array([[1.0, 1.0, 1.0]]),
        np.array([0.0]),
    )
    v = out['n'][:, 3]
    y = out['p'][:, 1]
    assert set(v.tolist()) == {0, 255}
    assert np.all(v[y == 2 * LAYER] == 0)
    assert np.all(v[y == 3 * LAYER] == 255)


def test_heartwood_rings_are_centered_on_the_hex():
    import numpy as np
    from tidewake.texpack import tile, T
    tex = np.asarray(tile(9, False), dtype=np.float64)
    if tex.ndim == 3:
        tex = tex[..., 0]
    # the pattern is rings around the hex centre, so a small disc at the centre
    # should be almost one constant, and a ring around it should vary with angle less than with radius
    cy = cx = T // 2
    disc = tex[cy - 2:cy + 3, cx - 2:cx + 3]
    ring = []
    for a in range(0, 360, 15):
        rad = np.radians(a)
        # a world-space circle of radius 0.4 (inside the hex)
        x = int(round((0.5 + 0.4 / np.sqrt(3.0) * np.cos(rad)) * T))
        y = int(round((0.5 + 0.4 / 2.0 * np.sin(rad)) * T))
        x = min(T - 1, max(0, x))
        y = min(T - 1, max(0, y))
        ring.append(tex[y, x])
    # centre-of-mass of contrast should sit near the middle of the tile
    w = (tex - tex.mean()) ** 2
    ys, xs = np.indices(tex.shape)
    wsum = w.sum() + 1e-9
    com_x = (xs * w).sum() / wsum / (T - 1)
    com_y = (ys * w).sum() / wsum / (T - 1)
    assert abs(com_x - 0.5) < 0.08 and abs(com_y - 0.5) < 0.08, (com_x, com_y, disc.mean(), np.std(ring))



def _mesh_door(face, opened, q=2, r=2, y=10):
    import numpy as np
    from tidewake.config import CHUNK, LAYERS
    from tidewake import materials as MT
    from tidewake.mesher import mesh_chunk, pad_chunk, VERT
    from tidewake.hexgrid import center
    cells = np.zeros((CHUNK, LAYERS, CHUNK), np.uint8)
    meta = np.zeros((CHUNK, LAYERS, CHUNK), np.uint8)
    cells[q, y, r] = MT.ID['door']
    cells[q, y + 1, r] = MT.ID['door']
    bit = face | (8 if opened else 0)
    meta[q, y, r] = bit
    meta[q, y + 1, r] = bit | 16
    empty = lambda a, b, src: src if (a, b) == (0, 0) else None
    o, _w, _L = mesh_chunk(
        pad_chunk(lambda a, b: empty(a, b, cells), 0, 0),
        np.zeros((CHUNK, CHUNK), np.int32), 0, 0,
        Pm=pad_chunk(lambda a, b: empty(a, b, meta), 0, 0),
    )
    return np.frombuffer(o, dtype=VERT), center(q, r)


def test_doors_are_a_mid_hex_double_leaf():
    import numpy as np
    from tidewake.config import LAYER
    from tidewake.hexgrid import DIR_NORMALS
    from tidewake import materials as MT
    from tidewake.world import World
    from tidewake.materials import is_blocking, overlaps_solid

    for face in (0, 2, 5):
        nx, nz = DIR_NORMALS[face]
        tx, tz = -nz, nx
        closed, (cx, cz) = _mesh_door(face, False)
        opened, _ = _mesh_door(face, True)
        assert len(closed) > 100 and len(opened) > 100
        def along(v):
            p = v['p']
            return (p[:, 0] - cx) * nx + (p[:, 2] - cz) * nz, (p[:, 0] - cx) * tx + (p[:, 2] - cz) * tz
        cn, ct = along(closed)
        on, ot = along(opened)
        # closed: a thin plane through the middle, spanning nearly the full hex
        assert np.abs(cn).max() < 0.12, (face, cn.min(), cn.max())
        assert ct.min() < -0.8 and ct.max() > 0.8, (face, ct.min(), ct.max())
        # open: leaves swing back, leaving a walkable gap down the middle
        assert on.min() < -0.7 and on.max() <= 0.05, (face, on.min(), on.max())
        mid = (np.abs(on) < 0.15) & (np.abs(ot) < 0.25)
        assert mid.sum() == 0, (face, 'open door still occupies the path', mid.sum())

    # interaction and collision are unchanged: closed blocks, open is a walkable path
    w = World.__new__(World)
    w.chunks = {}
    from tidewake.config import CHUNK, LAYERS
    import numpy as np
    from tidewake.world import Chunk
    cells = np.zeros((CHUNK, LAYERS, CHUNK), np.uint8)
    meta = np.zeros((CHUNK, LAYERS, CHUNK), np.uint8)
    cells[1, 8, 1] = MT.ID['door']
    cells[1, 9, 1] = MT.ID['door']
    meta[1, 8, 1] = 0
    meta[1, 9, 1] = 16
    w.chunks[(0, 0)] = Chunk(0, 0, cells, meta, np.zeros((CHUNK, CHUNK), np.int32))
    assert is_blocking(w, 1, 1, 8) and is_blocking(w, 1, 1, 9)
    assert overlaps_solid(w, 1, 1, 8 * LAYER + 0.1, 8 * LAYER + 1.2, LAYER)
    meta[1, 8, 1] = 8
    meta[1, 9, 1] = 8 | 16
    assert not is_blocking(w, 1, 1, 8) and not is_blocking(w, 1, 1, 9)
    assert not overlaps_solid(w, 1, 1, 8 * LAYER + 0.1, 8 * LAYER + 1.2, LAYER)



def test_v2_islands_have_wide_altitude_bands_and_teardrop_hulls():
    import numpy as np
    from tidewake.generator import Generator, CLOUD_SEA, TOP_MAX
    Q, R = np.mgrid[-120:120:3, -120:120:3]
    c = Generator(7, {}).columns(Q, R)
    land = c['land'] & ~c['skerry']
    com = c['com'][land]
    assert com.max() - com.min() > 40, (com.min(), com.max())
    # within a long view, at least some seeds show more than one altitude band
    Q2, R2 = np.mgrid[-90:90:3, -90:90:3]
    spans = []
    for seed in (7, 11, 29, 41, 100):
        c2 = Generator(seed, {}).columns(Q2, R2)
        land2 = c2['land'] & ~c2['skerry']
        if land2.any():
            com2 = c2['com'][land2]
            spans.append(float(com2.max() - com2.min()))
    assert spans and max(spans) > 30 and sorted(spans)[len(spans)//2] > 12, spans
    e, top, bot = c['e'][land], c['top'][land], c['bottom'][land]
    depth = top - bot
    rim = depth[e < 0.05]
    core = depth[e > 0.18]
    assert len(rim) and len(core), (len(rim), len(core))
    assert core.mean() > rim.mean() * 1.8, (rim.mean(), core.mean())
    assert rim.mean() < 16, rim.mean()
    # spawn stays in a sensible mid band
    from tidewake.session import find_spawn
    for seed in (7, 11, 29, 100):
        q, r, top, _sp = find_spawn(Generator(seed, {}))
        assert 32 <= top <= 92, (seed, q, r, top)


def test_v2_caves_only_open_at_framed_mouths():
    import numpy as np
    from tidewake.generator import Generator, CHUNK
    from tidewake import materials as MT
    gen = Generator(7, {'cave_amount': 80, 'cave_size': 80})
    cobble = MT.ID['cobble']
    canopy = MT.ID['canopy']
    breaches = mouths = cols = surface = 0
    HEX_N = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1))
    for cq, cr in ((8, -3), (0, 4), (-14, 6), (4, 0)):
        cells, _, _ = gen.generate(cq, cr)
        A, Y, B = cells.shape
        for a in range(A):
            for b in range(B):
                ground = cells[a, :, b].copy()
                ground[ground == canopy] = 0
                ys = np.where(ground > 0)[0]
                if len(ys) == 0:
                    continue
                top, bot = int(ys.max()), int(ys.min())
                cols += 1
                if (ground[max(bot, top - 3):top] == 0).any():
                    surface += 1
                for y in range(bot + 2, top - 4):
                    if cells[a, y, b] != 0:
                        continue
                    # a framed mouth sits next to its cobble jamb or lintel
                    framed = cells[a, y, b] == cobble
                    for dy in (-1, 0, 1, 2):
                        ny = y + dy
                        if ny < 0 or ny >= Y:
                            continue
                        if cells[a, ny, b] == cobble:
                            framed = True
                        for da, db in HEX_N:
                            na, nb = a + da, b + db
                            if 0 <= na < A and 0 <= nb < B and cells[na, ny, nb] == cobble:
                                framed = True
                    if framed:
                        mouths += 1
                        continue
                    # unframed breach: the hole opens onto a column that is empty to the sky
                    opens = False
                    for da, db in HEX_N:
                        na, nb = a + da, b + db
                        if not (0 <= na < A and 0 <= nb < B):
                            continue
                        if (cells[na, y:, nb] == 0).all():
                            opens = True
                            break
                    if opens:
                        breaches += 1
    assert cols > 80
    assert surface / cols < 0.02, ('walking surface still opens into caves', surface, cols)
    assert breaches / cols < 0.08, ('unframed cave breaches on the flanks', breaches, mouths, cols)
    assert mouths > 0, ('no framed mouths were placed', mouths, breaches, cols)



def test_v2_biomes_have_richer_ground_cover():
    from collections import Counter
    from tidewake.generator import Generator
    from tidewake import materials as MT
    kinds = ('grass', 'wildflower', 'mushroom', 'pebble', 'shrub', 'reeds', 'petals',
             'sprout', 'bloom', 'berry_bush', 'glowcap', 'crystal', 'vine', 'heather')
    c = Counter()
    for cq in range(-3, 4):
        for cr in range(-3, 4):
            cells, _, _ = Generator(7, {}).generate(cq, cr)
            for k in kinds:
                c[k] += int((cells == MT.ID[k]).sum())
    present = [k for k, n in c.items() if n > 0]
    assert sum(c.values()) > 200, dict(c)
    assert len(present) >= 8, present
    # the new plants actually appear
    assert c['grass'] > 0 and c['pebble'] > 0


def test_tutorial_is_larger_and_npcs_stand_in_the_open():
    from tidewake.generator import Generator
    from tidewake import materials as MT, tutorial as T
    from tidewake.config import CHUNK
    assert T.RADIUS >= 26
    g = Generator(1, {'tutorial': True})
    for q, r, name, *_ in T.NPCS:
        cq, cr = q // CHUNK, r // CHUNK
        cells, _, _ = g.generate(cq, cr)
        lq, lr = q - cq * CHUNK, r - cr * CHUNK
        stand = int(cells[lq, T.SURF + 1, lr])
        under = int(cells[lq, T.SURF, lr])
        assert under != 0, (name, 'has no floor')
        assert stand == 0, (name, 'is inside', MT.NAMES[stand] if stand else 'air')
    # signposts mark the path, and the lesson still has its stations
    signs = 0
    for cq in range(-3, 4):
        for cr in range(-3, 4):
            cells, _, _ = g.generate(cq, cr)
            signs += int((cells == MT.ID['signpost']).sum())
    assert signs >= 4



def test_showcase_camera_paths_stay_clear():
    """Every title-showcase orbit stays out of solids (including leaves) and does not hide the subject for long."""
    from tidewake import showcase as SC
    from tidewake import gensettings as GS
    items = SC.catalog()
    builds = 0
    for kind, payload in items:
        if kind == 'json':
            sc = SC.Showcase.load(payload)
            builds += 1
            assert sc.gen is not None, sc.name + ' must ship a generator setting'
            assert int(sc.gen.get('generator_version') or 0) == 3, sc.name + ' must use generator v3'
        else:
            data = dict(payload)
            data.setdefault('kind', 'seed')
            data.setdefault('blocks', [])
            if data.get('gen') is None:
                data['gen'] = GS.normalize({}, new=True)
            sc = SC.Showcase(data)
        world = SC.stamped_world(sc)
        rep = SC.path_report(sc, world, n=96)
        assert not rep['clips'], f"{sc.name} camera clips solids at angles {rep['clips'][:6]}"
        limit = max(2, 0.22 * rep['n'])
        assert len(rep['hides']) <= limit, f"{sc.name} hidden behind terrain for {len(rep['hides'])}/{rep['n']} samples"
    assert builds >= 6, f'need at least 6 player builds, found {builds}'


if __name__ == '__main__':
    test_tutorial_dialog_only_after_talk()
    print('ok tutorial dialog only after right-click')
    test_title_showcase_launch_avoids_last()
    print('ok title showcase shuffles at launch')
    test_showcase_camera_paths_stay_clear()
    print('ok showcase camera paths stay clear of solids')
    test_mob_y_trace_does_not_shake()
    print('ok mob y-trace is stable on the ground')
    test_lamps_are_kept_among_many_glowcaps()
    print('ok lamps stay in the light list')
    test_top_uvs_are_hex_centered()
    print('ok top UVs are centred on the hex')
    test_side_faces_carry_a_vertical_v()
    print('ok side faces carry a per-layer V')
    test_heartwood_rings_are_centered_on_the_hex()
    print('ok heartwood rings are centred on the hex')
    test_doors_are_a_mid_hex_double_leaf()
    print('ok doors are a mid-hex double leaf')
    test_v2_islands_have_wide_altitude_bands_and_teardrop_hulls()
    print('ok island altitude and teardrop hulls')
    test_v2_caves_only_open_at_framed_mouths()
    print('ok caves open only at framed mouths')
    test_v2_biomes_have_richer_ground_cover()
    print('ok biomes have richer ground cover')
    test_tutorial_is_larger_and_npcs_stand_in_the_open()
    print('ok tutorial is larger and NPCs stand in the open')
    print('ALL 1.4.1 UNIT TESTS PASSED')
