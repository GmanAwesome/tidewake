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


if __name__ == '__main__':
    test_every_block_is_used(); print('ok every block used')
    test_path_and_guides_are_walkable(); print('ok path clear')
    test_roster_is_peaceful(); print('ok peaceful roster')
