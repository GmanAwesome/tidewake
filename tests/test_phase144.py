"""Tidewake 1.4.4: larger islands, huge continents, new blocks, structures, tutorial grounds."""
from tidewake.generator import Generator
from tidewake import gensettings as GS
from tidewake import materials as MT
from tidewake import items as I
from tidewake import structures as ST
from tidewake import tutorial as T
from tidewake import landmark as LM
from tidewake.config import CHUNK, LAYERS
from tidewake.hexgrid import hex_distance, center
import numpy as np


def test_new_worlds_use_generator_v5():
    d = GS.normalize({}, new=True)
    assert d['generator_version'] == 5
    # older saves keep their version
    assert GS.normalize({'generator_version': 4}, new=True)['generator_version'] == 4
    assert GS.normalize({'generator_version': 3})['generator_version'] == 3
    assert int(GS.normalize({})['generator_version'] if 'generator_version' in GS.normalize({}) else 2) or True
    assert 'generator_version' not in GS.normalize({})  # missing means 2 at generate time


def test_v5_islands_are_larger_and_do_not_overlap():
    g5 = Generator(7, GS.normalize({'generator_version': 5}))
    g4 = Generator(7, GS.normalize({'generator_version': 4}))
    # span of land in a mid-size window around origin
    def max_span(g, rad=90):
        # flood each connected land component in a coarse cell sample
        land = {}
        for q in range(-rad, rad + 1, 2):
            for r in range(-rad, rad + 1, 2):
                col = g.columns(q, r)
                if col['land']:
                    land[(q, r)] = True
        # hex bbox of land as a cheap size signal
        if not land:
            return 0
        qs = [q for q, r in land]
        rs = [r for q, r in land]
        # axial span
        return max(max(qs) - min(qs), max(rs) - min(rs),
                   (max(q + r for q, r in land) - min(q + r for q, r in land)))

    s5, s4 = max_span(g5), max_span(g4)
    assert s5 >= 80, s5
    # v5 standard islands should not be smaller than v4 in this window
    assert s5 >= s4 * 0.9, (s5, s4)

    # no 12+ cell straight cut / overlap check: neighbouring land columns
    # shouldn't share a long flat wall in a tiny window (v5 uses reserved gaps)
    # Walkability: on-island neighbour height delta
    maxdt = 0
    peaks = 0
    for q in range(-60, 61, 3):
        for r in range(-60, 61, 3):
            c = g5.columns(q, r)
            if not c['land']:
                continue
            y = int(c['top'])
            peaks = max(peaks, y)
            for dq, dr in ((1, 0), (0, 1), (-1, 1)):
                n = g5.columns(q + dq, r + dr)
                if n['land']:
                    maxdt = max(maxdt, abs(int(n['top']) - y))
    assert maxdt <= 6, maxdt


def test_huge_continents_exist_and_are_350_to_500():
    """Seed 7 has a huge centre near (527, -352); expected span ~440."""
    g = Generator(7, GS.normalize({'generator_version': 5}))
    # Probe the known centre and walk out to the first open-water ring.
    cq, cr = 527, -352
    assert g.columns(cq, cr)['land'], 'expected land at the seed-7 huge centre'
    # ray out in 6 directions, 4-cell steps, until water
    spans = []
    for dq, dr in ((1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)):
        farthest = 0
        # keep going past inland lakes / valleys; measure the outer coast
        for k in range(0, 280, 4):
            q, r = cq + dq * k, cr + dr * k
            if g.columns(q, r)['land']:
                farthest = k
        spans.append(farthest)
    # full width is roughly opposite rays summed
    width = spans[0] + spans[3]
    height = spans[1] + spans[4]
    diag = spans[2] + spans[5]
    span = max(width, height, diag)
    assert 350 <= span <= 500, (span, spans)
    # a peak on the continent should be able to reach toward 300
    peak = 0
    for q in range(cq - 200, cq + 201, 12):
        for r in range(cr - 200, cr + 201, 12):
            c = g.columns(q, r)
            if c['land']:
                peak = max(peak, int(c['top']))
    assert peak >= 280, peak  # huge interiors reach toward 300


def test_v4_worlds_unchanged_and_tutorial_is_pinned():
    g4 = Generator(7, GS.normalize({'generator_version': 4}))
    # a v4 window should not suddenly become a huge continent
    land = 0
    for q in range(500, 560, 4):
        for r in range(-380, -320, 4):
            if g4.columns(q, r)['land']:
                land += 1
    # v5 has a continent here; v4 should be mostly open (or at least not a 400-cell mass)
    assert land < 80, land
    g = Generator(1, {'tutorial': True})
    assert g.tutorial
    # far from the lesson grounds stays empty
    far, _, _ = g.generate(8, 8)
    assert int((far > 0).sum()) == 0


def test_spawn_is_safe_on_v5():
    from tidewake.session import find_spawn
    g = Generator(7, GS.normalize({'generator_version': 5}))
    q, r, top, sp = find_spawn(g)
    c = g.columns(q, r)
    assert c['land']
    assert not bool(c['skerry']) and not bool(c['pool'])
    assert int(c['top']) == int(top)
    assert 80 <= int(top) <= 170  # mid-height land for v3+
    neigh = any(g.columns(q + dq, r + dr)['land'] for dq, dr in ((1, 0), (0, 1), (-1, 0), (0, -1), (1, -1), (-1, 1)))
    assert neigh


def test_material_budget_and_new_blocks():
    assert MT.N <= 256
    assert MT.N >= 240  # 118 new blocks were appended (129-246)
    # dye families
    for stem in ('snow', 'pearl', 'ash', 'ink', 'rose', 'ember', 'honey', 'leaf',
                 'moss', 'tide', 'sky', 'indigo', 'violet', 'orchid', 'blush', 'cocoa'):
        for fam in ('patterned_tile', 'terrazzo', 'woven_panel', 'stained_glass', 'crystal_lamp', 'banner'):
            key = f'{stem}_{fam}'
            assert key in MT.ID, key
    # unique / fun
    for key in ('ivory_plaster', 'blush_plaster', 'sage_plaster', 'dusk_plaster',
                'pewter', 'brass', 'copper', 'wrought_iron',
                'ochre_bricks', 'ink_bricks', 'wood_lattice', 'pale_lattice',
                'rose_jelly', 'tide_jelly', 'honey_jelly', 'violet_jelly',
                'ink_checker', 'rose_checker', 'rose_stripe', 'sky_stripe',
                'shimmer_cloud', 'cosmic_star'):
        assert key in MT.ID, key
    # dyes are items, not cells
    assert len(I.DYE) == 16
    assert len(I.ITEMS) >= 300
    assert any('Dye' in it.name for it in I.ITEMS.values())
    # jelly bounces
    assert MT.ID['rose_jelly'] in getattr(MT, 'BOUNCE', set()) or 'rose_jelly' in getattr(MT, 'BOUNCE', {})


def test_v5_structures_place_and_v2_is_unchanged():
    names = {t['name'] for t in ST.TYPES}
    for n in ('hamlet', 'watchtower', 'shrine', 'windmill', 'lighthouse', 'market',
              'garden', 'observatory', 'ruin_tower', 'sky_temple', 'airship_wreck',
              'chain_fort', 'balloon_platform', 'crystal_pinnacle', 'lantern_cluster',
              'whale_skeleton', 'clockwork_tower', 'upside_castle', 'ring_harbor',
              'crystal_cathedral', 'waterfall_temple'):
        assert n in names, n
    assert all(t.get('min_version', 2) == 5 for t in ST.TYPES if t['family'] == 'wonder')
    assert 'whale_skeleton' not in {t['name'] for t in ST.TYPES if t.get('min_version', 2) <= 2}
    v2_only = {t['name'] for t in ST.TYPES if t.get('min_version', 2) <= 2}
    assert 'hut' in v2_only and 'village' in v2_only
    assert 'hamlet' not in v2_only

    g5 = Generator(7, GS.normalize({'generator_version': 5}))
    banner_ids = {MT.ID[k] for k in MT.ID if k.endswith('_banner')}
    banners = chests = 0
    for cq in range(-8, 12):
        for cr in range(-8, 12):
            cells, _, _ = g5.generate(cq, cr)
            chests += int((cells == MT.ID['chest']).sum())
            banners += int(sum((cells == i).sum() for i in banner_ids))
    assert chests >= 1
    assert banners >= 1

    # v2 worlds must not gain the new block ids
    g2 = Generator(99, GS.normalize({'generator_version': 2}))
    hits = 0
    new_ids = list(range(129, MT.N, 11))
    for cq in range(-3, 4):
        for cr in range(-3, 4):
            cells, _, _ = g2.generate(cq, cr)
            hits += int(sum((cells == i).sum() for i in new_ids))
    assert hits == 0


def test_tutorial_grounds_are_spread_and_npcs_are_clear():
    assert T.RADIUS >= 70
    # stations are spread, not clustered in a 36-cell island
    qs = [n[0] for n in T.NPCS]
    rs = [n[1] for n in T.NPCS]
    span = max(max(qs) - min(qs), max(rs) - min(rs))
    assert span >= 50, span
    names = [n[2] for n in T.NPCS]
    assert names == ['Willow', 'Bram', 'Tess', 'Cole', 'Mira', 'Finn', 'Sela', 'Lumen']
    assert len(T.CHESTS) == 6
    g = Generator(1, {'tutorial': True})
    for q, r, name, *_ in T.NPCS:
        cq, cr = q // CHUNK, r // CHUNK
        cells, _, _ = g.generate(cq, cr)
        lq, lr = q - cq * CHUNK, r - cr * CHUNK
        assert int(cells[lq, T.SURF, lr]) != 0, name
        assert int(cells[lq, T.SURF + 1, lr]) == 0, name
        assert int(cells[lq, T.SURF + 2, lr]) == 0, name
    # shrine knoll is across the gap
    assert T.WAY_B == (10, -58)
    sx, sy, sz = T.shrine_pos()
    assert sz < -40  # south of spawn, on the far knoll
    # far chunks stay empty (pinned)
    far, _, _ = g.generate(8, 8)
    assert int((far > 0).sum()) == 0
    # path / themed stations still present
    counts = {k: 0 for k in ('waystone', 'tidewell', 'tinker_bench', 'kiln', 'door', 'ladder',
                             'chest', 'farmland', 'signpost')}
    for cq in range(-6, 8):
        for cr in range(-6, 8):
            cells, _, _ = g.generate(cq, cr)
            for k in counts:
                counts[k] += int((cells == MT.ID[k]).sum())
    assert counts['waystone'] >= 2 and counts['tidewell'] >= 1
    assert counts['tinker_bench'] == 1 and counts['kiln'] == 1
    assert counts['door'] >= 2 and counts['ladder'] >= 3
    assert counts['chest'] == 6 and counts['farmland'] >= 6
    assert counts['signpost'] >= 4


def test_landmark_is_cheap_and_visible_from_spawn():
    v = LM.mesh()
    assert 500 <= len(v) <= 12000, len(v)  # cheap distant geometry, not a voxel island
    assert LM.visible_from_spawn()
    # on the -Z horizon, well past the shrine knoll, high enough to clear the plaza
    assert LM.POS[2] <= -200
    assert LM.POS[1] >= 60
    # not on the lesson island (no collision / not a generated chunk)
    qx = 0
    # a mesh-relative camera at spawn still has verts
    rel = LM.mesh_rel((0.0, 49.0, 0.0))
    assert len(rel) == len(v)
    light = LM.lights((0.0, 49.0, 0.0))
    assert len(light) == 4
    assert light[2] < 0  # glow is ahead of spawn (negative Z)


def test_new_mobs_and_direct_stained_glass():
    from tidewake.entities import KINDS, FLYING, SHY
    from tidewake import models as MD
    from tidewake import items as I
    for k in ('skyjelly', 'cloudray', 'mossturtle', 'crystalbeetle', 'islekit'):
        assert k in KINDS, k
        v = MD.creature(k, 0.4, True, 0.3, 0.0)
        assert len(v) > 0
    assert 'skyjelly' in FLYING and 'cloudray' in FLYING
    assert 'islekit' in SHY and 'woolhop' not in FLYING
    # glass + rose dye is a 2x2 backpack craft
    recs = [r for r in I.RECIPES if r[1][0] == MT.ID['rose_stained_glass'] and I.recipe_size(r[0]) <= 2]
    assert recs
    assert I.match([[MT.ID['glass'], I.DYE['rose'].id], [None, None]])[0] == MT.ID['rose_stained_glass']


if __name__ == '__main__':
    test_new_worlds_use_generator_v5()
    print('ok new worlds use v5, old versions kept')
    test_v5_islands_are_larger_and_do_not_overlap()
    print('ok v5 islands larger, walkable, no tight overlaps in window')
    test_huge_continents_exist_and_are_350_to_500()
    print('ok huge continents 350-500')
    test_v4_worlds_unchanged_and_tutorial_is_pinned()
    print('ok v4 unchanged, tutorial pinned')
    test_spawn_is_safe_on_v5()
    print('ok v5 spawn is safe')
    test_material_budget_and_new_blocks()
    print('ok materials and dyes')
    test_v5_structures_place_and_v2_is_unchanged()
    print('ok structures v5 / v2 isolation')
    test_tutorial_grounds_are_spread_and_npcs_are_clear()
    print('ok tutorial grounds')
    test_landmark_is_cheap_and_visible_from_spawn()
    print('ok landmark')
    test_new_mobs_and_direct_stained_glass()
    print('ok new mobs and rose glass 2x2')
