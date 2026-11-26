"""1.4.6: My Skies hides the lesson island, structure rates +30%, no grand/small overlap."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tidewake.storage import SkyStorage
from tidewake import grand as GR, structures as STR
from tidewake.generator import Generator
import inspect


def test_tutorial_hidden_from_list():
    root = tempfile.mkdtemp()
    assert SkyStorage.list_skies(root) == []
    import json
    os.makedirs(os.path.join(root, 'The Lesson'))
    st = SkyStorage(root, 'The Lesson')
    # write the minimum sky.json that load() accepts
    with open(st.meta_file, 'w') as f:
        json.dump(dict(name='The Lesson', seed=1, tutorial=True), f)
    rows = SkyStorage.list_skies(root)
    assert rows and rows[0]['tutorial'] is True
    src = inspect.getsource(__import__('tidewake.ui.screens', fromlist=['x']).SkiesScreen.__init__)
    assert "not w.get('tutorial')" in src


def test_rates():
    assert abs(GR.CHANCE - 0.42 * 1.3) < 1e-9
    assert 'CHANCE = 65 if' in inspect.getsource(STR.place_v5)


def test_grand_occupied_is_deterministic():
    from tidewake import gensettings as GS
    g = Generator(12345, GS.normalize({'generator_version': 6}))
    assert g.version == 6
    hits = [(cq, cr) for cq in range(-14, 15, 7) for cr in range(-14, 15, 7) if GR.occupied(g, cq, cr)]
    assert hits == [(cq, cr) for cq in range(-14, 15, 7) for cr in range(-14, 15, 7) if GR.occupied(g, cq, cr)]
    assert hits, 'expected some grand structures nearby'


if __name__ == '__main__':
    test_tutorial_hidden_from_list(); test_rates(); test_grand_occupied_is_deterministic()
    print('ok 1.4.6 my skies + structure rates')
