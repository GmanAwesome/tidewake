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

if __name__ == '__main__':
    test_tutorial_dialog_only_after_talk()
    print('ok tutorial dialog only after right-click')
    test_title_showcase_launch_avoids_last()
    print('ok title showcase shuffles at launch')
    print('ALL 1.4.1 UNIT TESTS PASSED')
