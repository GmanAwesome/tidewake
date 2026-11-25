"""Scout v2 seeds for dramatic title-showcase sites."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from tidewake.generator import Generator
from tidewake.hexgrid import DIRS, hex_distance
from tidewake.noise import seed_from_text
from tidewake.session import find_spawn
from tidewake import gensettings as GS
from tidewake import materials as MT

SEEDS = [
    'keeper-of-tides', 'harbor-light', 'cliffside-cottage', 'golden-headland',
    'lantern-point', 'seabird-cove', 'windward-cape', 'bright-arch',
    'salt-wind-bay', 'windward-isle', 'ember-croft', 'mill-meadow',
    'quay-of-clouds', 'high-keep', 'star-temple', 'twin-isles',
    'cedar-crown', 'tavern-cliff', 'windmill-lea', 'moon-garden',
    'bridge-of-winds', 'sky-quay', '4096', '1729',
]

def scan(seed_text):
    gen = Generator(seed_from_text(seed_text), GS.normalize({}))
    q0, r0, top0, sp = find_spawn(gen)
    R = 90
    qs, rs = np.meshgrid(np.arange(q0 - R, q0 + R + 1, 2), np.arange(r0 - R, r0 + R + 1, 2), indexing='ij')
    c = gen.columns(qs, rs)
    land = c['land'] & ~c['skerry'] & ~c['pool'] & ~c['fall']
    best = {k: None for k in ('headland', 'cliff', 'flat', 'water', 'high', 'garden', 'wood', 'gap')}

    def consider(kind, score, rec):
        if best[kind] is None or score > best[kind][0]:
            best[kind] = (score, rec)

    H, W = land.shape
    for i in range(4, H - 4):
        for k in range(4, W - 4):
            if not land[i, k] or c['e'][i, k] < 0.04:
                continue
            q, r = int(qs[i, k]), int(rs[i, k])
            T = int(c['top'][i, k])
            B = int(c['bottom'][i, k])
            realm = int(c['realm'][i, k])
            thick = T - B
            # local flatness on a 5-step neighbourhood (step is 2, so ~10 cells)
            ts = []
            nland = 0
            for di in range(-2, 3):
                for dk in range(-2, 3):
                    if land[i+di, k+dk]:
                        ts.append(int(c['top'][i+di, k+dk]))
                        nland += 1
            if nland < 6:
                continue
            ptp = max(ts) - min(ts)
            mean_t = sum(ts) / len(ts)
            # drops per direction
            drops = []
            airs = 0
            for d, (dq, dr) in enumerate(DIRS):
                far_i, far_k = i + dq * 4, k + dr * 4  # 8 cells (step 2)
                if not (0 <= far_i < H and 0 <= far_k < W):
                    drops.append(20); airs += 1
                    continue
                if not c['land'][far_i, far_k]:
                    drops.append(20); airs += 1
                else:
                    drops.append(int(T - c['top'][far_i, far_k]))
            # water nearby
            water = 0
            for di in range(-6, 7):
                for dk in range(-6, 7):
                    ii, kk = i+di, k+dk
                    if 0 <= ii < H and 0 <= kk < W and (c['pool'][ii, kk] or c['fall'][ii, kk]):
                        water += 1
            rec = dict(q=q, r=r, top=T, bot=B, realm=realm, ptp=ptp, airs=airs,
                       drops=drops, water=water, thick=thick, com=float(c['com'][i, k]))
            # headland: meadow-ish, some airs, fairly flat, mid height
            if realm in (0, 1, 8, 10) and 36 <= T <= 88 and ptp <= 5 and airs >= 2 and nland >= 8:
                consider('headland', airs * 8 + water * 0.5 + (4 - ptp) * 3 - abs(T - 58) * 0.15, rec)
            # cliff: one or two big drops, land behind, not too jagged
            if max(drops) >= 10 and airs <= 3 and ptp <= 7 and 40 <= T <= 100:
                consider('cliff', max(drops) + water * 0.3 + (3 if realm in (4, 11, 12, 15) else 0), rec)
            # flat farm
            if realm in (0, 1, 9, 10) and ptp <= 3 and airs == 0 and nland >= 12 and 40 <= T <= 85:
                consider('flat', nland + water * 0.4 - ptp * 2, rec)
            # water edge
            if water >= 2 and ptp <= 6 and 36 <= T <= 90:
                consider('water', water + airs * 2 + (5 if max(drops) >= 6 else 0), rec)
            # high knoll
            if T >= 72 and ptp <= 6 and nland >= 8:
                consider('high', T - 60 + (4 - min(ptp, 4)) * 2 + (5 if realm in (4, 11, 12, 13) else 0), rec)
            # garden
            if realm in (0, 10, 2, 9) and ptp <= 4 and airs <= 1 and 44 <= T <= 80:
                consider('garden', (4 - ptp) * 4 + water * 0.4, rec)
            # wooded
            if realm in (0, 1, 9, 15) and c['e'][i, k] > 0.06 and ptp <= 6 and airs <= 2:
                consider('wood', float(c['e'][i, k]) * 40 + (6 if realm == 9 else 0), rec)
            # gap: land here, air a few steps one way, land again
            for d, (dq, dr) in enumerate(DIRS):
                mid_i, mid_k = i + dq * 2, k + dr * 2
                far_i, far_k = i + dq * 4, k + dr * 4
                if not (0 <= far_i < H and 0 <= far_k < W):
                    continue
                if (not land[mid_i, mid_k]) and land[far_i, far_k]:
                    t2 = int(c['top'][far_i, far_k])
                    if abs(t2 - T) <= 8:
                        grec = dict(rec)
                        grec['q2'], grec['r2'], grec['top2'], grec['dir'] = int(qs[far_i, far_k]), int(rs[far_i, far_k]), t2, d
                        consider('gap', 20 - abs(t2 - T) + airs, grec)
    return q0, r0, top0, best

def main():
    for st in SEEDS:
        try:
            q0, r0, top0, best = scan(st)
        except Exception as e:
            print(st, 'ERR', e)
            continue
        bits = []
        for kind, v in best.items():
            if not v:
                bits.append(f'{kind}=none')
                continue
            sc, rec = v
            bits.append(f"{kind}={rec['q']},{rec['r'],} T{rec['top']} r{rec['realm']} a{rec['airs']} w{rec['water']} ptp{rec['ptp']} ({sc:.1f})")
        print(f'{st:20s} spawn {q0},{r0} T{top0} | ' + ' '.join(bits))

if __name__ == '__main__':
    main()
