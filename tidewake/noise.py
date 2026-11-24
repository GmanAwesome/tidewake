"""Seeded, vectorised gradient noise on numpy arrays, with no repetition.

Classic Perlin noise uses a 256-entry permutation table, so it repeats every 256
lattice cells (about 80,000 blocks at typical terrain scales). Here every lattice
corner's gradient comes from a 64-bit integer hash of (ix, iy, iz, seed), so the
noise never repeats and stays correct for huge and negative coordinates, all the
way out to where float64 itself runs out of precision (around 10^13 blocks).
"""
import numpy as np

from . import fast as _fast

MASK64 = (1 << 64) - 1
_K1, _K2, _K3 = np.uint64(0x9E3779B97F4A7C15), np.uint64(0xC2B2AE3D27D4EB4F), np.uint64(0x165667B19E3779F9)
_C1, _C2 = np.uint64(0xBF58476D1CE4E5B9), np.uint64(0x94D049BB133111EB)
_S30, _S27, _S31 = np.uint64(30), np.uint64(27), np.uint64(31)


def splitmix64(x):
    """64-bit integer mix for plain Python ints (deriving seeds, per-chunk RNG seeds)."""
    x = (x + 0x9E3779B97F4A7C15) & MASK64
    x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
    x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & MASK64
    return x ^ (x >> 31)


def hash_ints(seed, *values):
    """Combine a seed and any number of (possibly negative, possibly huge) ints into a 64-bit hash."""
    h = splitmix64(seed & MASK64)
    for v in values:
        h = splitmix64(h ^ (v & MASK64))
    return h


def _mix(h):
    h = h ^ (h >> _S30)
    h = h * _C1
    h = h ^ (h >> _S27)
    h = h * _C2
    return h ^ (h >> _S31)


def hash2(ix, iz, seed):
    """Vectorised 64-bit hash of int64 lattice coordinates -> uint64."""
    with np.errstate(over='ignore'):
        h = (np.asarray(ix).astype(np.int64).astype(np.uint64) * _K1) ^ \
            (np.asarray(iz).astype(np.int64).astype(np.uint64) * _K2) ^ np.uint64(seed & MASK64)
        return _mix(h)


def hash3(ix, iy, iz, seed):
    with np.errstate(over='ignore'):
        h = (ix.astype(np.uint64) * _K1) ^ (iy.astype(np.uint64) * _K2) ^ (iz.astype(np.uint64) * _K3) ^ np.uint64(seed & MASK64)
        return _mix(h)


def rand01(ix, iz, seed):
    """Deterministic uniform [0, 1) per integer column."""
    return (hash2(ix, iz, seed) >> np.uint64(11)).astype(np.float64) * (1.0 / (1 << 53))


_A = np.arange(16) * (2 * np.pi / 16) + 0.3
_G2 = np.stack([np.cos(_A), np.sin(_A)], axis=1)
_G3 = np.array([(1, 1, 0), (-1, 1, 0), (1, -1, 0), (-1, -1, 0), (1, 0, 1), (-1, 0, 1), (1, 0, -1), (-1, 0, -1),
                (0, 1, 1), (0, -1, 1), (0, 1, -1), (0, -1, -1), (1, 1, 0), (-1, 1, 0), (0, -1, 1), (0, -1, -1)],
               dtype=np.float64)
_F15 = np.uint64(15)


def _fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)


class Noise:
    """Gradient noise source. noise2/noise3 return roughly [-1, 1]."""

    def __init__(self, seed):
        self.seed = splitmix64(seed & MASK64)

    def noise2(self, x, y, seed=None):
        s = self.seed if seed is None else seed
        if _fast.ENABLED:
            x, y = np.broadcast_arrays(np.asarray(x, np.float64), np.asarray(y, np.float64))
            r = _fast.fbm2(np.ascontiguousarray(x).ravel(), np.ascontiguousarray(y).ravel(),
                           np.array([s & MASK64], np.uint64), 2.0, 0.5, _G2)
            return r.reshape(x.shape)
        x0, y0 = np.floor(x), np.floor(y)
        fx, fy = x - x0, y - y0
        ix, iy = x0.astype(np.int64), y0.astype(np.int64)

        def g(ox, oy):
            gv = _G2[(hash2(ix + ox, iy + oy, s) & _F15).astype(np.intp)]
            return gv[..., 0] * (fx - ox) + gv[..., 1] * (fy - oy)
        u, v = _fade(fx), _fade(fy)
        a = g(0, 0) + u * (g(1, 0) - g(0, 0))
        b = g(0, 1) + u * (g(1, 1) - g(0, 1))
        return (a + v * (b - a)) * 1.414

    def noise3(self, x, y, z, seed=None):
        s = self.seed if seed is None else seed
        if _fast.ENABLED:
            x, y, z = np.broadcast_arrays(np.asarray(x, np.float64), np.asarray(y, np.float64), np.asarray(z, np.float64))
            r = _fast.fbm3(np.ascontiguousarray(x).ravel(), np.ascontiguousarray(y).ravel(), np.ascontiguousarray(z).ravel(),
                           np.array([s & MASK64], np.uint64), 2.0, 0.5, _G3)
            return r.reshape(x.shape)
        x0, y0, z0 = np.floor(x), np.floor(y), np.floor(z)
        fx, fy, fz = x - x0, y - y0, z - z0
        ix, iy, iz = x0.astype(np.int64), y0.astype(np.int64), z0.astype(np.int64)

        def g(ox, oy, oz):
            gv = _G3[(hash3(ix + ox, iy + oy, iz + oz, s) & _F15).astype(np.intp)]
            return gv[..., 0] * (fx - ox) + gv[..., 1] * (fy - oy) + gv[..., 2] * (fz - oz)
        u, v, w = _fade(fx), _fade(fy), _fade(fz)
        def lerp(t, a, b):
            return a + t * (b - a)
        y1 = lerp(v, lerp(u, g(0, 0, 0), g(1, 0, 0)), lerp(u, g(0, 1, 0), g(1, 1, 0)))
        y2 = lerp(v, lerp(u, g(0, 0, 1), g(1, 0, 1)), lerp(u, g(0, 1, 1), g(1, 1, 1)))
        return lerp(w, y1, y2)

    def _seeds(self, octaves):
        k = ('_sd', octaves)
        v = self.__dict__.get(k)
        if v is None:
            v = self.__dict__[k] = np.array([splitmix64(self.seed + i) for i in range(octaves)], dtype=np.uint64)
        return v

    def fbm2(self, x, y, octaves=4, lacunarity=2.0, gain=0.5):
        """Fractal sum with an independent lattice per octave (no artefacts at the origin)."""
        if _fast.ENABLED:
            x = np.asarray(x, dtype=np.float64)
            y = np.broadcast_to(np.asarray(y, dtype=np.float64), x.shape)
            x, y = np.broadcast_arrays(x, y)
            r = _fast.fbm2(np.ascontiguousarray(x).ravel(), np.ascontiguousarray(y).ravel(), self._seeds(octaves), float(lacunarity), float(gain), _G2)
            return r.reshape(x.shape)
        total, amp, freq, norm = 0.0, 1.0, 1.0, 0.0
        for i in range(octaves):
            total = total + self.noise2(x * freq, y * freq, splitmix64(self.seed + i)) * amp
            norm += amp
            amp *= gain
            freq *= lacunarity
        return total / norm

    def fbm3(self, x, y, z, octaves=2, lacunarity=2.0, gain=0.5):
        if _fast.ENABLED:
            x, y, z = np.broadcast_arrays(np.asarray(x, np.float64), np.asarray(y, np.float64), np.asarray(z, np.float64))
            r = _fast.fbm3(np.ascontiguousarray(x).ravel(), np.ascontiguousarray(y).ravel(), np.ascontiguousarray(z).ravel(),
                           self._seeds(octaves), float(lacunarity), float(gain), _G3)
            return r.reshape(x.shape)
        total, amp, freq, norm = 0.0, 1.0, 1.0, 0.0
        for i in range(octaves):
            total = total + self.noise3(x * freq, y * freq, z * freq, splitmix64(self.seed + i)) * amp
            norm += amp
            amp *= gain
            freq *= lacunarity
        return total / norm


def seed_from_text(text):
    """Minecraft-style: an integer string is used as-is, anything else is hashed (Java String.hashCode)."""
    text = (text or '').strip()
    if not text:
        return None
    try:
        v = int(text)
        if -(1 << 63) <= v < (1 << 63):
            return v
    except ValueError:
        pass
    h = 0
    for ch in text:
        h = (31 * h + ord(ch)) & 0xFFFFFFFF
    return h - (1 << 32) if h >= (1 << 31) else h


def random_seed():
    """A random signed 64-bit seed from the OS's secure random source."""
    import secrets
    v = secrets.randbits(64)
    return v - (1 << 64) if v >= (1 << 63) else v


_fast._warmup()
