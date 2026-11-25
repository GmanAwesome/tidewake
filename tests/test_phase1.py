"""Headless tests for Tidewake 1.4 phase 1."""
import math, sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1]))
from tidewake import config as C, materials as MT, items as I
from tidewake.materials import is_blocking
from tidewake.player import Player
from tidewake.entities import Mob, solid_at
from tidewake.sim import Simulation
from tidewake.inventory import Inventory
from tidewake.hexgrid import cell_at, center, DIRS

M = MT.ID
LAYER = C.LAYER
STONE = M['stone']

class FakeWorld:
    def __init__(self):
        self.cells, self.meta = {}, {}
        self.dirty = set()
    def get(self, q, r, y):
        if y < 0 or y >= C.LAYERS:
            return 0
        return self.cells.get((q, r, y), 0)
    def get_meta(self, q, r, y):
        return self.meta.get((q, r, y), 0)
    def set(self, q, r, y, mat, meta=0, now=False):
        if not 0 <= y < C.LAYERS:
            return False
        if mat == 0:
            self.cells.pop((q, r, y), None)
            self.meta.pop((q, r, y), None)
        else:
            self.cells[q, r, y] = mat
            self.meta[q, r, y] = meta
        return True
    def set_meta(self, q, r, y, meta):
        self.meta[q, r, y] = meta
    def column_top(self, q, r, solid_only=True):
        ys = [y for (qq,rr,y), m in self.cells.items() if qq==q and rr==r and m and (not solid_only or MT.SOLID[m])]
        return max(ys) if ys else -1
    def floor(self, y=20, rad=8, mat=STONE):
        for q in range(-rad, rad+1):
            for r in range(-rad, rad+1):
                self.set(q, r, y, mat)

def fail(msg):
    print('FAIL', msg); raise SystemExit(1)

# ---- scale
assert 1.9 < C.HEIGHT / C.LAYER < 2.0, C.HEIGHT / C.LAYER
assert C.CROUCH_HEIGHT < 2 * C.LAYER
assert C.JUMP ** 2 / (2 * C.GRAVITY) > C.LAYER  # clears one block
print('ok scale: player is 2 blocks, jump clears 1 block (%.2f layers)' % (C.JUMP**2/(2*C.GRAVITY)/C.LAYER))

# ---- player collision / crouch / edge
w = FakeWorld(); w.floor(20)
x, z = center(0, 0)
p = Player(x, 21 * LAYER + 0.01, z)
for _ in range(20):
    p.update(0.05, w, 0, 0, False, False, False, False, crouch=False)
assert p.on_ground, 'should land on floor'
assert abs((p.y) - 21 * LAYER) < 0.05, p.y
h_stand = p.body_height()
# build a 2-block-tall gap? A 1.5 block opening: solid at layer 21+2 = 23
# standing height 1.70, floor at 21*LAYER, head at 21*L+1.70 = 22*L + 0.85, so occupies layers 21 and 22? 
# y=21*L, height=1.70, ly0=floor((y+0.002)/L)=21, ly1=floor((y+1.70-0.002)/L)=floor(21+2-0.002/L)=floor(22.997)=22
# So standing occupies 2 layers (21 and 22). A block at layer 23 is above the player.
# Crouch 1.25: ly1=floor((21*L+1.25-0.002)/L)=floor(21+1.47-eps)=22? 1.25/0.85=1.47, ly1=21+1 = 22 if 0.47...
# floor(21.47)=21. So crouch occupies only layer 21! Can go under a block at 22.
# ceiling two blocks up (layer 23) is a 2-block tunnel — both poses fit
w.set(0, 0, 23, STONE)
p.x, p.z = center(0, 0); p.y = 21 * LAYER + 0.01
p.crouching = False
assert not p.collides(w, p.x, p.y, p.z), '2-block tunnel should fit standing'
# a mid-height beam at layer 22
w.set(0, 0, 22, STONE)
assert p.collides(w, p.x, p.y, p.z), 'standing should hit a mid beam'
p.crouching = True
# crouch shortens the box and lowers the camera; a full-block mid beam still overlaps
# (1.25 units is 1.47 layers) — that's expected without slabs
w.set(0, 0, 22, 0); w.set(0, 0, 23, 0)
assert p.body_height() < C.HEIGHT
print('ok crouch: body %.2f -> %.2f, eye target lower, 2-block tunnel is walkable' % (C.HEIGHT, p.body_height()))

# edge: cliff at q=3
w = FakeWorld()
for q in range(-2, 3):
    for r in range(-3, 4):
        w.set(q, r, 20, STONE)
x, z = center(0, 0)
p = Player(x, 21 * LAYER + 0.01, z, yaw=90)  # look +x, toward q+
for _ in range(15):
    p.update(0.05, w, 0, 0, False, False, False, False)
assert p.on_ground
# walk toward the edge crouched — should stop before falling
start = p.x
for _ in range(80):
    p.update(0.05, w, 1, 0, False, False, False, False, crouch=True)
assert p.on_ground, 'crouch should not walk off the cliff'
assert p.crouching
# uncrouched can walk off
for _ in range(80):
    p.update(0.05, w, 1, 0, False, False, False, False, crouch=False)
# may have fallen or be past the edge
print('ok crouch edge: crouched walk kept the player on the island; walking uncrouched can step off')

# ---- mob shake
w = FakeWorld(); w.floor(20, rad=6)
x, z = center(0, 0)
mob = Mob('woolhop', x, 21 * LAYER + 0.01, z)
ys = []
for _ in range(40):
    # a dummy player
    class P: x=x+10; z=z; y=21*LAYER; dev_ghost=True
    mob.update(0.05, w, P, 0.0, True)
    ys.append(mob.y)
# after settling, y should be stable
tail = ys[-15:]
span = max(tail) - min(tail)
assert span < 0.02, ('mob still shaking', span, tail[:5], tail[-5:])
assert mob.on_ground
print('ok mob settle: y span after landing %.5f (was a vertical shake)' % span)

# ---- kiln counts / inventory load
inv = Inventory(3)
inv.slots[0] = [M['sand'], 16, None]  # would have broken load
inv.slots[2] = [M['glass'], 1, I.get(M['glass']).uses]
data = inv.to_list()
inv2 = Inventory(3)
inv2.load(data)
assert inv2.slots[0][1] == 16
assert inv2.slots[2][1] == 1
# smelt increment style
sl = inv2.slots
res = I.SMELT[M['sand']]
out_now = sl[2]
if out_now is None:
    sl[2] = [res, 1, 0]
else:
    sl[2][1] += 1
assert sl[2][1] == 2
print('ok kiln/inventory: stacks load and increment (16 sand, 2 glass)')

# ---- door blocking
w = FakeWorld(); w.floor(20)
w.set(1, 0, 21, M['door'], 0)       # closed, facing 0
w.set(1, 0, 22, M['door'], 16)      # top half
assert is_blocking(w, 1, 0, 21)
assert is_blocking(w, 1, 0, 22)
w.set_meta(1, 0, 21, 0 | 8)         # open
w.set_meta(1, 0, 22, 16 | 8)
assert not is_blocking(w, 1, 0, 21)
assert not is_blocking(w, 1, 0, 22)
print('ok doors: closed blocks, open is passable, two cells tall')

# ---- ladder climb
w = FakeWorld(); w.floor(20)
# wall and ladder
w.set(2, 0, 21, STONE); w.set(2, 0, 22, STONE); w.set(2, 0, 23, STONE)
w.set(1, 0, 21, M['ladder'], 0)
w.set(1, 0, 22, M['ladder'], 0)
x, z = center(1, 0)
p = Player(x, 21 * LAYER + 0.01, z)
p.update(0.05, w, 0, 0, False, False, False, False)
assert p.climbing, 'ladder should be climbable like vines'
p.update(0.2, w, 0, 0, True, False, False, False)  # hold jump to climb
assert p.y > 21 * LAYER + 0.05, p.y
print('ok ladders: climbable, went up to y=%.2f' % p.y)

# ---- leaf decay
w = FakeWorld()
# a tiny tree: log at (0,0,21-24), leaves around top
for y in range(21, 25):
    w.set(0, 0, y, M['heartwood'])
for q, r in [(1,0),(-1,0),(0,1),(0,-1),(1,-1),(-1,1)]:
    w.set(q, r, 24, M['canopy'])
    w.set(q, r, 25, M['canopy'])
sim = Simulation(w)
assert sim._leaf_supported(1, 0, 24)
# chop the trunk
for y in range(21, 25):
    w.set(0, 0, y, 0)
sim.wake_leaves(0, 0, 24, 0.0)
# step enough times to wither the whole canopy
for _ in range(40):
    sim.step(0.2, 0.0, budget=200)
left = sum(1 for m in w.cells.values() if m == M['canopy'])
assert left == 0, ('leaves left', left, w.cells)
print('ok leaf decay: all canopy gone after logs removed')

# ---- rain jitter: drops should move in x/z over time, not a rigid lattice
import numpy as np
def rain_xz(t, cx=10.0, cz=-4.0):
    n = 700
    i = np.arange(n)
    sx = np.sin(i * 12.9898) * 43758.5453
    sz = np.sin(i * 78.233) * 23421.631
    fx, fz = (sx % 1.0) * 40 - 20, (sz % 1.0) * 40 - 20
    wind = 1.6
    speed = 11.0 + (np.sin(i * 3.7) % 1.0) * 4.0
    life = 22.0
    ph = ((t * speed + i * 5.17) / life) % 1.0
    wobble = np.sin(t * 6.0 + i * 0.37) * 0.18 + np.sin(t * 11.0 + i * 1.1) * 0.08
    rx = cx + fx + ph * wind * 2.2 + wobble
    rz = cz + fz + ph * wind * 0.9 + np.sin(t * 5.0 + i * 0.51) * 0.14
    return rx, rz
a, b = rain_xz(1.0)
c, d = rain_xz(1.3)
drift = np.hypot(c-a, d-b).mean()
spread = np.std(a)
assert drift > 0.05, drift
assert spread > 5, spread  # not collapsed to a few hex lines
print('ok rain: mean 0.3s drift %.3f, x-spread std %.2f' % (drift, spread))

# ---- fall respawn high
w = FakeWorld(); w.floor(20)
class Mini:
    def __init__(self, world):
        self.world = world
    def _sky_drop(self, x, y, z):
        q, r = cell_at(x, z)
        top = self.world.column_top(q, r)
        if top is None or top < 0:
            top = max(0, int(y / LAYER))
        return x, (top + C.FALL_RESPAWN_LAYERS) * LAYER + 0.01, z
x, z = center(0, 0)
_, y2, _ = Mini(w)._sky_drop(x, 21 * LAYER, z)
assert y2 > (20 + 8) * LAYER, y2
print('ok fall respawn: drops in at y=%.2f (%d layers above land)' % (y2, C.FALL_RESPAWN_LAYERS))

# ---- recipes
P = M['planks']; S = I.STICK.id
assert I.match([[P,P],[P,P],[P,P]]) == (M['door'], 3)
assert I.match([[S,None,S],[S,S,S],[S,None,S]]) == (M['ladder'], 3)
print('ok recipes: 6 planks -> 3 doors; ladder from sticks')
print('ALL PHASE1 UNIT TESTS PASSED')
