"""World-creation sliders: defaults, clamp, and how they ride along with a sky.

Values are 0–100 with 50 as the mid/default. They are stored on the sky and
must stay stable across saves (do not rename keys).
"""

KEYS = (
    'island_size',
    'island_thickness',
    'sky_density',
    'terrain_roughness',
    'mountain_height',
    'flatness',
    'cave_amount',
    'cave_size',
    'water',
    'biome_size',
    'tree_density',
    'glimmer_rarity',
)

# (key, label, hint, low-end word, high-end word)
SLIDERS = (
    ('island_size', 'Island size', 'How wide each island tends to grow.', 'Small', 'Vast'),
    ('island_thickness', 'Island thickness', 'How deep the land goes under your feet.', 'Thin', 'Thick'),
    ('sky_density', 'Sky density', 'How many islands fill the sky.', 'Sparse', 'Crowded'),
    ('terrain_roughness', 'Terrain roughness', 'Smooth ground versus rolling, broken land.', 'Smooth', 'Wild'),
    ('mountain_height', 'Mountain height', 'How tall the peaks and ranges rise.', 'Low', 'High'),
    ('flatness', 'Flatness', 'More gentle plains, fewer sharp drops.', 'Rugged', 'Plains'),
    ('cave_amount', 'Cave amount', 'How often caves open under the islands.', 'Rare', 'Many'),
    ('cave_size', 'Cave size', 'Tight tunnels versus wide caverns.', 'Tight', 'Huge'),
    ('water', 'Water', 'Pools, wetlands and waterfalls.', 'Dry', 'Wet'),
    ('biome_size', 'Biome size', 'How far one landscape stretches before it changes.', 'Patchy', 'Wide'),
    ('tree_density', 'Tree density', 'How wooded the islands are.', 'Bare', 'Forest'),
    ('glimmer_rarity', 'Glimmer rarity', 'How scarce golden dusk motes are. Higher is rarer.', 'Common', 'Rare'),
)

DEFAULT = 50


# 1 = pre-1.4 (no sliders). 2 = 1.4 / 1.4.1. 3 = 1.4.2 (higher, separated islands).
# 4 = 1.4.3 (discrete spaced islands, no Worley cut planes).
# 5 = 1.4.4 (larger islands plus a rare huge-continent tier).
# 6 = 1.4.4 late (islands 50% larger again, shelves spread over 500 layers, grand structures).
CURRENT = 6


def defaults():
    return {k: DEFAULT for k in KEYS}


def normalize(data, *, new=False):
    """A complete 0–100 int map. Missing keys become 50; unknown keys are dropped.

    generator_version is not a slider. New skies get CURRENT (6). Existing skies
    keep the version they were saved with; a missing version means 2 (1.4 / 1.4.1).
    """
    out = defaults()
    if data:
        for k in KEYS:
            try:
                v = int(round(float(data[k])))
            except (KeyError, TypeError, ValueError):
                continue
            out[k] = max(0, min(100, v))
        if 'generator_version' in data:
            try:
                out['generator_version'] = int(data['generator_version'])
            except (TypeError, ValueError):
                pass
    if new and 'generator_version' not in out:
        out['generator_version'] = CURRENT
    return out


def fingerprint(data):
    """Stable cache key for worker processes."""
    d = normalize(data)
    ver = int(d.get('generator_version') or 2)
    return (ver,) + tuple(d[k] for k in KEYS)


def scale(data, key, lo=0.5, mid=1.0, hi=1.5):
    """Map a 0–100 slider to a multiplier: 0→lo, 50→mid, 100→hi."""
    t = normalize(data)[key] / 100.0
    if t <= 0.5:
        return lo + (mid - lo) * (t / 0.5)
    return mid + (hi - mid) * ((t - 0.5) / 0.5)
