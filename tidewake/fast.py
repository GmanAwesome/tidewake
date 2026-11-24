"""Compiled (Numba) kernels for the hot paths, with a pure-numpy fallback.

If Numba or LLVM is unavailable (or JIT fails), `ENABLED` is False and callers use numpy.
In the frozen exe the JIT cache lives next to the exe's user data (NUMBA_CACHE_DIR).
"""
import os
import sys

import numpy as np

ENABLED = False
if getattr(sys, 'frozen', False) and 'NUMBA_CACHE_DIR' not in os.environ:
    base = os.environ.get('LOCALAPPDATA') or os.path.expanduser('~')
    os.environ['NUMBA_CACHE_DIR'] = os.path.join(base, 'Tidewake', 'numba-cache')
try:
    if os.environ.get('TIDEWAKE_NO_NUMBA'):
        raise ImportError('disabled')
    from numba import njit, prange
    ENABLED = True
except Exception:          # pragma: no cover
    njit = None

if ENABLED:
    _K1 = np.uint64(0x9E3779B97F4A7C15)
    _K2 = np.uint64(0xC2B2AE3D27D4EB4F)
    _K3 = np.uint64(0x165667B19E3779F9)
    _C1 = np.uint64(0xBF58476D1CE4E5B9)
    _C2 = np.uint64(0x94D049BB133111EB)

    @njit(cache=True, inline='always')
    def _mix(h):
        h = h ^ (h >> np.uint64(30))
        h = h * _C1
        h = h ^ (h >> np.uint64(27))
        h = h * _C2
        return h ^ (h >> np.uint64(31))

    @njit(cache=True, inline='always')
    def _fade(t):
        return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)

    @njit(cache=True, inline='always')
    def _g2(ix, iy, s, fx, fy, G2):
        h = _mix((np.uint64(ix) * _K1) ^ (np.uint64(iy) * _K2) ^ s)
        k = np.int64(h & np.uint64(15))
        return G2[k, 0] * fx + G2[k, 1] * fy

    @njit(cache=True)
    def fbm2(x, y, seeds, lac, gain, G2):
        """x, y: flat float64 arrays. seeds: uint64 per octave."""
        n = x.shape[0]
        out = np.empty(n)
        norm = 0.0
        amp = 1.0
        for o in range(seeds.shape[0]):
            norm += amp
            amp *= gain
        for i in range(n):
            tot = 0.0
            amp = 1.0
            freq = 1.0
            for o in range(seeds.shape[0]):
                s = seeds[o]
                xx, yy = x[i] * freq, y[i] * freq
                x0, y0 = np.floor(xx), np.floor(yy)
                fx, fy = xx - x0, yy - y0
                ix, iy = np.int64(x0), np.int64(y0)
                a00 = _g2(ix, iy, s, fx, fy, G2)
                a10 = _g2(ix + 1, iy, s, fx - 1.0, fy, G2)
                a01 = _g2(ix, iy + 1, s, fx, fy - 1.0, G2)
                a11 = _g2(ix + 1, iy + 1, s, fx - 1.0, fy - 1.0, G2)
                u, v = _fade(fx), _fade(fy)
                a = a00 + u * (a10 - a00)
                b = a01 + u * (a11 - a01)
                tot += (a + v * (b - a)) * 1.414 * amp
                amp *= gain
                freq *= lac
            out[i] = tot / norm
        return out

    @njit(cache=True, inline='always')
    def _g3(ix, iy, iz, s, fx, fy, fz, G3):
        h = _mix((np.uint64(ix) * _K1) ^ (np.uint64(iy) * _K2) ^ (np.uint64(iz) * _K3) ^ s)
        k = np.int64(h & np.uint64(15))
        return G3[k, 0] * fx + G3[k, 1] * fy + G3[k, 2] * fz

    @njit(cache=True)
    def fbm3(x, y, z, seeds, lac, gain, G3):
        n = x.shape[0]
        out = np.empty(n)
        norm = 0.0
        amp = 1.0
        for o in range(seeds.shape[0]):
            norm += amp
            amp *= gain
        for i in range(n):
            tot = 0.0
            amp = 1.0
            freq = 1.0
            for o in range(seeds.shape[0]):
                s = seeds[o]
                xx, yy, zz = x[i] * freq, y[i] * freq, z[i] * freq
                x0, y0, z0 = np.floor(xx), np.floor(yy), np.floor(zz)
                fx, fy, fz = xx - x0, yy - y0, zz - z0
                ix, iy, iz = np.int64(x0), np.int64(y0), np.int64(z0)
                u, v, w = _fade(fx), _fade(fy), _fade(fz)
                c000 = _g3(ix, iy, iz, s, fx, fy, fz, G3)
                c100 = _g3(ix + 1, iy, iz, s, fx - 1, fy, fz, G3)
                c010 = _g3(ix, iy + 1, iz, s, fx, fy - 1, fz, G3)
                c110 = _g3(ix + 1, iy + 1, iz, s, fx - 1, fy - 1, fz, G3)
                c001 = _g3(ix, iy, iz + 1, s, fx, fy, fz - 1, G3)
                c101 = _g3(ix + 1, iy, iz + 1, s, fx - 1, fy, fz - 1, G3)
                c011 = _g3(ix, iy + 1, iz + 1, s, fx, fy - 1, fz - 1, G3)
                c111 = _g3(ix + 1, iy + 1, iz + 1, s, fx - 1, fy - 1, fz - 1, G3)
                y1 = (c000 + u * (c100 - c000)) + v * ((c010 + u * (c110 - c010)) - (c000 + u * (c100 - c000)))
                y2 = (c001 + u * (c101 - c001)) + v * ((c011 + u * (c111 - c011)) - (c001 + u * (c101 - c001)))
                tot += (y1 + w * (y2 - y1)) * amp
                amp *= gain
                freq *= lac
            out[i] = tot / norm
        return out


def _warmup():
    """Compile (or load from cache) once; on any failure fall back to numpy."""
    global ENABLED
    if not ENABLED:
        return
    try:
        from .noise import _G2, _G3
        z = np.zeros(2)
        s = np.array([1], np.uint64)
        fbm2(z, z, s, 2.0, 0.5, _G2)
        fbm3(z, z, z, s, 2.0, 0.5, _G3)
    except Exception as e:      # pragma: no cover
        print('numba disabled:', e)
        ENABLED = False
