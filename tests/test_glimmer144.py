"""1.4.4: the Glimmer Font is now the Tidewell, and the Glimmer loop is explained and works end to end."""
import types

from tidewake import materials as MT, items as I, glimmer as G, achievements as A
from tidewake import tutorial as T
from tidewake.inventory import Inventory


def test_rename_keeps_saves():
    assert MT.ID['tidewell'] == 117 == MT.ID['glimmer_font']
    assert MT.NAMES[117] == 'Tidewell'
    assert MT.ID['tidewell'] in MT.LIGHTS
    assert any(r[1][0] == MT.ID['tidewell'] for r in I.RECIPES)
    assert A.BY_ID['font'][1] == 'Tidewell gift'      # node id kept for old saves
    assert 'Tidewell' in A.BY_ID['font'][5]


def test_costs_are_sensible():
    costs = [c for _, _, c, _ in G.ATTUNEMENTS]
    assert costs == sorted(costs) and min(costs) == 2 and max(costs) <= 4
    assert G.WAYSTONE_COST == 1
    # the lesson chest plus a couple of motes pays for two waystones and a first gift
    chest = dict(T.CHESTS[(5, -31, T.SURF + 1)])
    assert chest[I.GLIMMER.id] + 1 >= 2 * G.WAYSTONE_COST + min(costs)


class _Audio:
    def play(self, *a, **k):
        pass


def _fake_session():
    from tidewake.session import Session
    s = Session.__new__(Session)
    s.inv = Inventory(36)
    s.attune, s.waystones, s.achieved = [], {}, []
    s.stats = {'mined': 0, 'placed': 0, 'motes': 0, 'crafted': 0}
    s.dev = False
    s.play_time = 0
    s.awakened = []
    s.toasts = []
    s.toast = lambda *a, **k: s.toasts.append(a)
    s.app = types.SimpleNamespace(audio=_Audio(), set_screen=lambda sc: None)
    s.player = types.SimpleNamespace(speed_mul=1.0, x=0, y=0, z=0, vx=0, vy=0, vz=0, last_safe=None)
    s.hold = False
    s._waystone_name = lambda q, r: f'Stone {q},{r}'
    return s


def test_loop_end_to_end():
    s = _fake_session()
    # empty-handed: the waystone explains how to get Glimmer
    s._use_waystone(8, -32, T.SURF + 1)
    assert 'walk into' in s.toasts[-1][1]
    s.inv.add(I.GLIMMER.id, 4)                      # Lumen's chest
    s._use_waystone(8, -32, T.SURF + 1)
    s._use_waystone(10, -58, T.SURF + 4)
    assert sum(v['attuned'] for v in s.waystones.values()) == 2
    assert s.inv.count(I.GLIMMER.id) == 2
    assert s.travel_to_waystone(G.key(8, -32, T.SURF + 1))
    assert s.buy_attunement('sense')
    assert 'sense' in s.attune and s.inv.count(I.GLIMMER.id) == 0
    assert not s.buy_attunement('reach')
    assert 'more' in s.toasts[-1][1]


def test_tutorial_has_mote_courts_and_tidewell_line():
    courts = T.mote_courts()
    assert len(courts) == 2
    lumen = next(n for n in T.NPCS if n[2] == 'Lumen')
    text = ' '.join(lumen[4])
    assert 'Tidewell' in text and 'walk into' in text and 'free' in text


if __name__ == '__main__':
    test_rename_keeps_saves(); print('ok rename keeps saves')
    test_costs_are_sensible(); print('ok costs')
    test_loop_end_to_end(); print('ok glimmer loop end to end')
    test_tutorial_has_mote_courts_and_tidewell_line(); print('ok tutorial lines')
