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
