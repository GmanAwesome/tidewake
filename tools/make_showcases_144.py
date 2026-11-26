"""Record 1.4.4 wonder stamps as title-screen JSON builds (generator v3 terrain)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tidewake import materials as MT
from tidewake import structures as ST

M = MT.ID
INV = {}
for k, v in M.items():
    INV.setdefault(int(v), k)


class RecWorld:
    def __init__(self, top=40, rad=10):
        self.ground_y = top
        self.cells = {}
        for dq in range(-rad, rad + 1):
            for dr in range(-rad, rad + 1):
                for y in range(top - 4, top + 1):
                    self.cells[(dq, dr, y)] = (M['loam'] if y < top else M['turf'], 0)

    def get(self, q, r, y):
        return self.cells.get((q, r, y), (0, 0))[0]

    def set(self, q, r, y, mat, meta=0, now=False):
        self.cells[(q, r, y)] = (int(mat), int(meta))

    def column_top(self, q, r):
        ys = [y for (qq, rr, y), (m, _) in self.cells.items() if qq == q and rr == r and m]
        return max(ys) if ys else self.ground_y

    def mark_dirty(self, *a, **k):
        pass


def record(name, top=40, realm=0, seed=1):
    w = RecWorld(top=top, rad=12)
    ST.stamp_world(w, 0, 0, name, cond=ST.INTACT, seed=seed, realm=realm)
    blocks = []
    for (q, r, y), (mat, meta) in sorted(w.cells.items()):
        if mat <= 0:
            # keep explicit clears above the pad so flatten does not refill them? skip air
            continue
        key = INV.get(int(mat))
        if not key:
            continue
        # skip the pre-filled turf pad except where the build overwrote it
        if y <= top and (q, r, y) in [(dq, dr, yy) for dq in range(-12, 13)
                                       for dr in range(-12, 13)
                                       for yy in range(top - 4, top + 1)] and key in ('loam', 'turf'):
            # include floor if the build wrote terra/plaster over it; skip untouched pad
            # we cannot tell; include only y > top or non-turf/loam at <= top
            if y < top and key == 'loam':
                continue
            if y == top and key == 'turf':
                continue
        blocks.append([int(q), int(r), int(y - top), key, int(meta)])
    return blocks


SHOWS = [
    dict(name='Clockwork Spire', author='brass rings over a quiet isle',
         seed_text='keeper-of-tides', typ='clockwork_tower', realm=6,
         site={'q': 4, 'r': -2, 'top': 107},
         camera={'radius': 56.0, 'height': 28.0, 'target_dy': 8.0, 'yaw_offset': -18.0,
                 'speed': 0.032, 'phase': 0.16},
         flatten={'radius': 7, 'blend': 6, 'clear_up': 32, 'clear_trees': 28, 'flowers': 8}),
    dict(name='Crystal Nave', author='stained glass in the high air',
         seed_text='salt-wind-bay', typ='crystal_cathedral', realm=7,
         site={'q': 188, 'r': -80, 'top': 108},
         camera={'radius': 58.0, 'height': 26.0, 'target_dy': 7.0, 'yaw_offset': 16.0,
                 'speed': 0.03, 'phase': 0.2},
         flatten={'radius': 8, 'blend': 6, 'clear_up': 30, 'clear_trees': 28, 'flowers': 10}),
    dict(name='Whalebone Isle', author='a sky-whale at rest',
         seed_text='windward-isle', typ='whale_skeleton', realm=14,
         site={'q': 90, 'r': -20, 'top': 72},
         camera={'radius': 60.0, 'height': 24.0, 'target_dy': 4.0, 'yaw_offset': 24.0,
                 'speed': 0.034, 'phase': 0.18},
         flatten={'radius': 8, 'blend': 5, 'clear_up': 24, 'clear_trees': 26, 'flowers': 6}),
    dict(name='Hanging Keep', author='a castle that grew downward',
         seed_text='lantern-point', typ='upside_castle', realm=11,
         site={'q': -66, 'r': 40, 'top': 184},
         camera={'radius': 62.0, 'height': 18.0, 'target_dy': -2.0, 'yaw_offset': -22.0,
                 'speed': 0.03, 'phase': 0.24},
         flatten={'radius': 8, 'blend': 6, 'clear_up': 20, 'clear_trees': 26, 'flowers': 4}),
    dict(name='Ring Harbor', author='docks around a well of cloud',
         seed_text='tavern-cliff', typ='ring_harbor', realm=8,
         site={'q': 124, 'r': -4, 'top': 109},
         camera={'radius': 58.0, 'height': 26.0, 'target_dy': 4.0, 'yaw_offset': 12.0,
                 'speed': 0.033, 'phase': 0.22},
         flatten={'radius': 8, 'blend': 6, 'clear_up': 24, 'clear_trees': 26, 'flowers': 8}),
]


def main():
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           'assets', 'showcase')
    os.makedirs(out_dir, exist_ok=True)
    for spec in SHOWS:
        typ = spec['typ']
        # SHOWS items get mutated if we pop typ from the dict used later — copy
        typ = typ or spec['typ']
        blocks = record(typ, top=40, realm=spec.get('realm', 0), seed=3)
        print(spec['name'], typ, 'blocks', len(blocks))
        data = {
            'name': spec['name'],
            'author': spec['author'],
            'seed_text': spec['seed_text'],
            'gen': {
                'island_size': 50, 'island_thickness': 50, 'sky_density': 50,
                'terrain_roughness': 50, 'mountain_height': 50, 'flatness': 50,
                'cave_amount': 50, 'cave_size': 50, 'water': 50, 'biome_size': 50,
                'tree_density': 50, 'glimmer_rarity': 50, 'generator_version': 3,
            },
            'site': spec['site'],
            'camera': spec['camera'],
            'flatten': spec['flatten'],
            'blocks': blocks,
        }
        slug = spec['name'].lower().replace(' ', '_').replace("'", '')
        path = os.path.join(out_dir, slug + '.json')
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
            f.write('\n')
        print(' wrote', path, 'bytes', os.path.getsize(path))


if __name__ == '__main__':
    main()
