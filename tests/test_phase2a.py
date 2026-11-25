"""Headless tests for Tidewake 1.4 phase 2a world generation."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from tidewake.generator import Generator
from tidewake.materials import REALMS, N_REALMS, REALM_TURF, REALM_CANOPY
from tidewake import gensettings as GS

assert N_REALMS == 16 and len(REALMS) == 16 and len(REALM_TURF) == 16 and len(REALM_CANOPY) == 16

# sliders
d = GS.normalize({'island_thickness': 80, 'nope': 1, 'water': -5})
assert d['island_thickness'] == 80 and d['water'] == 0 and d['flatness'] == 50 and 'nope' not in d
assert GS.fingerprint(d) == GS.fingerprint(GS.normalize(d))
assert GS.scale(GS.defaults(), 'island_size', 0.5, 1.0, 1.5) == 1.0
print('ok sliders: normalize, clamp, fingerprint, mid-scale=1')

Q, R = np.mgrid[-160:160:4, -160:160:4]

def cols(seed, settings=None):
    return Generator(seed, settings).columns(Q, R)

# determinism
a, b = cols(123, {'mountain_height': 80}), cols(123, {'mountain_height': 80})
assert np.all(a['top'] == b['top']) and np.all(a['bottom'] == b['bottom']) and np.all(a['realm'] == b['realm'])
print('ok determinism: same seed+sliders make the same land')

# v1 compatibility: two calls match, and v2 is thicker
v1 = Generator(7).columns(Q, R)
v1b = Generator(7).columns(Q, R)
assert np.all(v1['top'] == v1b['top'])
v2 = cols(7, {})
d1 = (v1['top'] - v1['bottom'])[v1['land']].mean()
d2 = (v2['top'] - v2['bottom'])[v2['land']].mean()
assert d2 > d1 * 1.6, (d1, d2)
print('ok thickness: v2 default islands are substantially thicker (%.1f vs v1 %.1f layers)' % (d2, d1))

thin = cols(7, {'island_thickness': 15})
thick = cols(7, {'island_thickness': 95})
dt = (thin['top'] - thin['bottom'])[thin['land']].mean()
dk = (thick['top'] - thick['bottom'])[thick['land']].mean()
assert dk > dt * 1.4, (dt, dk)
print('ok thickness slider: 15 -> %.1f layers, 95 -> %.1f' % (dt, dk))

# vertical CoM varies
com = v2['com'][v2['land']]
assert com.max() - com.min() > 20, (com.min(), com.max())
print('ok island height: centers of mass span %.0f to %.0f' % (com.min(), com.max()))

# mountain / flatness sliders change relief (use a seed that shows it)
def relief(settings, seed=11):
    c = cols(seed, settings)
    land = c['land'] & ~c['skerry']
    return float((c['top'] - c['com'])[land].std())
ra = relief({'flatness': 5, 'mountain_height': 95, 'terrain_roughness': 85})
rp = relief({'flatness': 95, 'mountain_height': 8, 'terrain_roughness': 12})
assert ra > rp * 1.3, (ra, rp)
print('ok terrain sliders: alpine relief std %.1f vs plains %.1f' % (ra, rp))

# sky density and island size change land cover / scale
sp = cols(11, {'sky_density': 15})['land'].mean()
cr = cols(11, {'sky_density': 90})['land'].mean()
assert cr > sp * 1.15, (sp, cr)
print('ok sky density: sparse land %.1f%% vs crowded %.1f%%' % (100*sp, 100*cr))

# caves differ with sliders (and stay deterministic)
ca = Generator(9, {'cave_amount': 85, 'cave_size': 80}).generate(8, -3)[0]
cb = Generator(9, {'cave_amount': 85, 'cave_size': 80}).generate(8, -3)[0]
cc = Generator(9, {'cave_amount': 15, 'cave_size': 15}).generate(8, -3)[0]
assert (ca == cb).all() and not (ca == cc).all()
print('ok caves: amount/size sliders change carving, same settings stay identical')

# all 16 biomes appear across a handful of seeds
seen = set()
for seed in range(10):
    c = cols(seed, {})
    seen.update(int(i) for i in np.unique(c['realm'][c['land']]))
missing = [REALMS[i] for i in range(16) if i not in seen]
assert not missing, missing
print('ok biomes: all 16 landscapes appear (%s)' % ', '.join(REALMS))

# tree slider is wired (rate field)
g_bare = Generator(3, {'tree_density': 5})
g_forest = Generator(3, {'tree_density': 95})
assert g_forest.tree_mul > g_bare.tree_mul * 3
print('ok tree density slider scales placement (%.2f vs %.2f)' % (g_bare.tree_mul, g_forest.tree_mul))

print('ALL PHASE2A UNIT TESTS PASSED')
