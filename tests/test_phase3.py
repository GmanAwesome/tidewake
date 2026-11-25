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


def test_fishing_rod_and_catches():
    from tidewake import items as I, fishing as F, materials as MT
    import random
    assert I.ROD.kind == 'rod' and I.ROD.uses == 80
    assert any(r[1][0] == I.ROD.id for r in I.RECIPES)
    assert I.SMELT[I.SILVERFIN.id] == I.COOKED_SILVERFIN.id
    assert I.SMELT[I.GLIMMERFIN.id] == I.COOKED_GLIMMERFIN.id
    assert F.biome_group(3) == 'frost'
    assert F.biome_group(8) == 'arid'
    ff = 0
    for i in range(200):
        iid, n, kind = F.roll_catch(3, 0.1, random.Random(i + 9))
        assert I.get(iid) is not None and n >= 1
        if kind == 'fish' and iid == I.FROSTFIN.id:
            ff += 1
    assert ff > 40
    # dusk in lumen groves can yield glimmerfin
    got = False
    for i in range(300):
        iid, n, kind = F.roll_catch(7, 0.7, random.Random(i + 3))
        if iid == I.GLIMMERFIN.id:
            got = True
            break
    assert got


def test_farming_hoe_seeds_and_harvest():
    from tidewake import materials as MT, items as I, farming as F
    import random
    assert MT.ID['farmland'] == 118
    assert MT.ID['skywheat'] in MT.CROP_GROW
    assert I.HOE.kind == 'hoe'
    assert any(r[1][0] == I.HOE.id for r in I.RECIPES)
    assert any(r[1][0] == I.LOAF.id for r in I.RECIPES)
    assert I.SMELT[I.SWEETROOT.id] == I.COOKED_ROOT.id
    assert F.plant_of(I.GRAIN_SEEDS.id) == MT.ID['skywheat']
    assert F.plant_of(I.BERRY_SEEDS.id) == MT.ID['berry_crop']
    ripe = F.harvest(MT.ID['skywheat'], 3, random.Random(2))
    assert any(i == I.WHEAT.id for i, _ in ripe)
    assert any(i == I.GRAIN_SEEDS.id for i, _ in ripe)
    young = F.harvest(MT.ID['skywheat'], 0, random.Random(0))
    assert all(i != I.WHEAT.id for i, _ in young)
    from tidewake.sim import LIVING
    assert MT.ID['farmland'] in LIVING and MT.ID['skywheat'] in LIVING


def test_achievement_tree():
    from tidewake import achievements as A
    assert len(A.NODES) >= 10
    assert all(len(n) == 7 for n in A.NODES)
    assert A.NODES[0][0] == 'first' and A.NODES[0][2] is None
    ids = [n[0] for n in A.NODES]
    assert len(ids) == len(set(ids))
    for nid, title, parent, col, row, how, chk in A.NODES:
        assert title and how and callable(chk)
        if parent:
            assert parent in A.BY_ID

    class Fake:
        stats = {'mined': 30, 'crafted': 1, 'tinker': 1, 'smelted': 0, 'placed': 0, 'doors': 0,
                 'motes': 0, 'fished': 0, 'tilled': 0, 'farmed': 0}
        play_time = 0
        waystones = {}
        attune = []
        awakened = []
        achieved = []

    s = Fake()
    new = A.poll(s)
    assert 'first' in s.achieved and 'gather' in s.achieved and 'craft' in s.achieved
    assert 'tinker' in s.achieved
    assert 'kiln' not in s.achieved
    assert 'shrine' not in s.achieved
    s.waystones = {'0,0,4': {'name': 'Lumen shrine', 'attuned': True}}
    s.stats['motes'] = 1
    A.poll(s)
    assert 'wander' in s.achieved and 'shrine' in s.achieved


def test_tutorial_island():
    from tidewake.generator import Generator
    from tidewake import materials as MT, tutorial as T
    g = Generator(1, {'tutorial': True})
    assert g.tutorial
    counts = {k: 0 for k in ('waystone', 'glimmer_font', 'water', 'farmland', 'skywheat',
                             'tinker_bench', 'kiln', 'door', 'ladder', 'chest', 'bedroll', 'heartwood')}
    for cq in range(-2, 3):
        for cr in range(-2, 3):
            cells, _, _ = g.generate(cq, cr)
            for k in counts:
                counts[k] += int((cells == MT.ID[k]).sum())
    far, _, _ = g.generate(8, 8)
    assert int((far > 0).sum()) == 0
    assert counts['waystone'] >= 2 and counts['glimmer_font'] >= 1
    assert counts['skywheat'] >= 1 and counts['farmland'] >= 6
    assert counts['door'] >= 2 and counts['ladder'] >= 3
    assert counts['chest'] == 6 and counts['tinker_bench'] == 1
    assert counts['water'] >= 7 and counts['heartwood'] >= 8
    assert len(T.NPCS) == 8
    names = [n[2] for n in T.NPCS]
    assert 'Willow' in names and 'Finn' in names and 'Lumen' in names
    g2 = Generator(1, {})
    assert not g2.tutorial
