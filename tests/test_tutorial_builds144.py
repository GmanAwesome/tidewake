"""1.4.4 lesson island showpieces: every placeable block appears, the path stays clear."""
from tidewake import tutorial as T, tutorial_builds as TB, materials as MT
from tidewake.hexgrid import DIRS


def test_every_block_is_used():
    import importlib.util, os
    spec = importlib.util.spec_from_file_location(
        'tbu', os.path.join(os.path.dirname(__file__), '..', 'tools', 'tutorial_block_usage.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    missing, _ = mod.unused()
    assert missing == [], missing


def _blocked():
    bad = set()
    for q, r in T.path_cells():
        cq, cr = q // 16, r // 16
        cells, _, _ = T.generate_chunk(cq, cr)
        lq, lr = q - cq * 16, r - cr * 16
        for y in range(T.SURF + 1, T.SURF + 3):
            m = int(cells[lq, y, lr])
            if m and MT.SOLID[m]:
                bad.add((q, r, y))
    return bad


def test_path_and_guides_are_walkable():
    """The showpieces never add an obstacle on the lesson path (stations sit on it by design)."""
    with_builds = _blocked()
    real = TB.apply
    TB.apply = lambda *a: None
    try:
        base = _blocked()
    finally:
        TB.apply = real
    assert with_builds <= base, sorted(with_builds - base)[:10]


def test_roster_is_peaceful():
    from tidewake.entities import KINDS
    assert len(TB.MOBS) >= 12
    assert all(not KINDS[k][4] for k, *_ in TB.MOBS)



def test_station_blocks_constant_matches_source():
    assert sorted(TB.STATION_BLOCK_NAMES) == TB.station_blocks_from_source(), \
        sorted(set(TB.station_blocks_from_source()) ^ set(TB.STATION_BLOCK_NAMES))


def test_lesson_builds_without_source_files():
    """Frozen builds ship bytecode only: the lesson island must build with no .py file readable."""
    import builtins
    from tidewake import tutorial as T
    from tidewake.generator import Generator
    from tidewake import gensettings as GS
    real_open = builtins.open

    def no_py(path, *a, **k):
        if str(path).endswith('.py'):
            raise FileNotFoundError(path)
        return real_open(path, *a, **k)
    TB._CACHE.clear()
    builtins.open = no_py
    try:
        buckets = TB.plan()
        assert len(buckets) > 10
        n = 0
        for cq in range(-3, 4):
            for cr in range(-3, 4):
                out = T.generate_chunk(cq, cr)
                n += int((out[0] > 0).sum())
        assert n > 1000, n
    finally:
        builtins.open = real_open


if __name__ == '__main__':
    test_every_block_is_used(); print('ok every block used')
    test_path_and_guides_are_walkable(); print('ok path clear')
    test_roster_is_peaceful(); print('ok peaceful roster')
    test_station_blocks_constant_matches_source(); print('ok station blocks constant')
    test_lesson_builds_without_source_files(); print('ok lesson builds with no .py sources (frozen)')
