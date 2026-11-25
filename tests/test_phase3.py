"""1.4 Phase 3 systems: Glimmer rarity, waystones, fonts, attunements."""
from tidewake import materials as MT, items as I, glimmer as G
from tidewake.generator import Generator


def test_glimmer_is_rarer():
    mid = Generator(1, {})
    rare = Generator(2, {'glimmer_rarity': 100})
    common = Generator(3, {'glimmer_rarity': 0})
    assert mid.version == 2
    assert abs(mid.glimmer_mul - 0.32) < 0.02
    assert rare.glimmer_mul < mid.glimmer_mul < common.glimmer_mul
    # old mid was 1.0; mid is now about a third as many
    assert mid.glimmer_mul < 0.5


def test_waystone_and_font_exist():
    assert MT.ID['waystone'] == 116
    assert MT.ID['glimmer_font'] == 117
    assert bool(MT.SOLID[116]) and bool(MT.SOLID[117])
    assert any(r[1][0] == MT.ID['waystone'] for r in I.RECIPES)
    assert any(r[1][0] == MT.ID['glimmer_font'] for r in I.RECIPES)


def test_attunements_are_priced():
    ids = [a[0] for a in G.ATTUNEMENTS]
    assert ids == ['reach', 'lightfoot', 'breath', 'sense', 'brightwake']
    assert all(a[2] >= 3 for a in G.ATTUNEMENTS)


def test_temples_place_waystones():
    g = Generator(21, {})
    cells, _, _ = g.generate(5, -15)
    assert int((cells == MT.ID['waystone']).sum()) >= 1


def test_waystone_save_roundtrip_keys():
    assert G.parse_key(G.key(3, -4, 12)) == (3, -4, 12)
