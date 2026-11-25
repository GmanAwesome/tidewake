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

if __name__ == '__main__':
    test_tutorial_dialog_only_after_talk()
    print('ok tutorial dialog only after right-click')
    print('ALL 1.4.1 UNIT TESTS PASSED')
