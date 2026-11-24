"""Top-down map of a seed (debug tool): python tools/topmap.py SEED out.png [size] [step]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PIL import Image
from tidewake.generator import Generator
from tidewake.materials import REALM_TURF
seed = int(sys.argv[1]); out = sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 400
step = int(sys.argv[4]) if len(sys.argv) > 4 else 2
ox = int(sys.argv[5]) if len(sys.argv) > 5 else 0
g = Generator(seed)
q = np.arange(-n // 2, n // 2) * step + ox
Q, R = np.meshgrid(q, q, indexing='ij')
Q = Q - R // 2   # roughly square
c = g.columns(Q, R)
col = REALM_TURF[c['realm']] * (0.55 + 0.45 * np.clip((c['top'] - 30) / 70.0, 0, 1))[..., None]
img = np.where(c['land'][..., None], col, np.array([0.85, 0.87, 0.95]))
img = np.where(c['fall'][..., None], np.array([0.2, 0.4, 1.0]), img)
img = np.where((c['pool'] & c['land'])[..., None], np.array([0.3, 0.6, 0.9]), img)
im = (np.transpose(img, (1, 0, 2)) * 255).astype(np.uint8)
I = Image.fromarray(im[::-1])
from PIL import ImageDraw
d = ImageDraw.Draw(I)
for s in g.spires_near(ox, 0, regions=n * step // 128 + 1):
    i = (s['q'] + s['r'] // 2 - ox) / step + n / 2; k = n - 1 - (s['r'] / step + n / 2)
    if 0 <= i < n and 0 <= k < n:
        d.ellipse([i - 3, k - 3, i + 3, k + 3], fill=(120, 60, 200))
I.save(out)
print('land %.2f' % c['land'].mean(), 'realms', np.bincount(c['realm'][c['land']].ravel(), minlength=8))
