//! Gradient noise with the same 64-bit hashes as `tidewake/noise.py`.
//!
//! The lattice never repeats. `noise2` is scaled by 1.414, matching the pure
//! Python path (Numba is off in the reference run this was checked against).

const K1: u64 = 0x9E3779B97F4A7C15;
const K2: u64 = 0xC2B2AE3D27D4EB4F;
const K3: u64 = 0x165667B19E3779F9;
const C1: u64 = 0xBF58476D1CE4E5B9;
const C2: u64 = 0x94D049BB133111EB;

/// Exact `cos`/`sin` of `arange(16) * 2π/16 + 0.3` from NumPy, so the gradients match.
const G2: [[f64; 2]; 16] = [
    [0.95533648912560598, 0.29552020666133955],
    [0.76952514194593680, 0.63861651710011846],
    [0.46656056766778126, 0.88448925188354754],
    [0.09256637634428391, 0.99570651598274096],
    [-0.29552020666133955, 0.95533648912560598],
    [-0.63861651710011824, 0.76952514194593691],
    [-0.88448925188354743, 0.46656056766778153],
    [-0.99570651598274096, 0.09256637634428420],
    [-0.95533648912560609, -0.29552020666133927],
    [-0.76952514194593702, -0.63861651710011813],
    [-0.46656056766778159, -0.88448925188354743],
    [-0.09256637634428470, -0.99570651598274085],
    [0.29552020666133921, -0.95533648912560609],
    [0.63861651710011846, -0.76952514194593669],
    [0.88448925188354743, -0.46656056766778164],
    [0.99570651598274085, -0.09256637634428476],
];

const G3: [[f64; 3]; 16] = [
    [1.0, 1.0, 0.0],
    [-1.0, 1.0, 0.0],
    [1.0, -1.0, 0.0],
    [-1.0, -1.0, 0.0],
    [1.0, 0.0, 1.0],
    [-1.0, 0.0, 1.0],
    [1.0, 0.0, -1.0],
    [-1.0, 0.0, -1.0],
    [0.0, 1.0, 1.0],
    [0.0, -1.0, 1.0],
    [0.0, 1.0, -1.0],
    [0.0, -1.0, -1.0],
    [1.0, 1.0, 0.0],
    [-1.0, 1.0, 0.0],
    [0.0, -1.0, 1.0],
    [0.0, -1.0, -1.0],
];

#[inline]
pub fn splitmix64(mut x: u64) -> u64 {
    x = x.wrapping_add(0x9E3779B97F4A7C15);
    x = (x ^ (x >> 30)).wrapping_mul(0xBF58476D1CE4E5B9);
    x = (x ^ (x >> 27)).wrapping_mul(0x94D049BB133111EB);
    x ^ (x >> 31)
}

#[inline]
fn mix(mut h: u64) -> u64 {
    h ^= h >> 30;
    h = h.wrapping_mul(C1);
    h ^= h >> 27;
    h = h.wrapping_mul(C2);
    h ^ (h >> 31)
}

#[inline]
pub fn hash2(ix: i64, iz: i64, seed: u64) -> u64 {
    let h = (ix as u64).wrapping_mul(K1) ^ (iz as u64).wrapping_mul(K2) ^ seed;
    mix(h)
}

#[inline]
pub fn hash3(ix: i64, iy: i64, iz: i64, seed: u64) -> u64 {
    let h = (ix as u64).wrapping_mul(K1)
        ^ (iy as u64).wrapping_mul(K2)
        ^ (iz as u64).wrapping_mul(K3)
        ^ seed;
    mix(h)
}

pub fn hash_ints(seed: u64, values: &[i64]) -> u64 {
    let mut h = splitmix64(seed);
    for &v in values {
        h = splitmix64(h ^ (v as u64));
    }
    h
}

#[inline]
pub fn rand01(ix: i64, iz: i64, seed: u64) -> f64 {
    ((hash2(ix, iz, seed) >> 11) as f64) * (1.0 / ((1u64 << 53) as f64))
}

#[inline]
fn fade(t: f64) -> f64 {
    t * t * t * (t * (t * 6.0 - 15.0) + 10.0)
}

#[inline]
fn grad2(ix: i64, iy: i64, seed: u64, fx: f64, fy: f64) -> f64 {
    let g = G2[(hash2(ix, iy, seed) & 15) as usize];
    g[0] * fx + g[1] * fy
}

#[inline]
fn grad3(ix: i64, iy: i64, iz: i64, seed: u64, fx: f64, fy: f64, fz: f64) -> f64 {
    let g = G3[(hash3(ix, iy, iz, seed) & 15) as usize];
    g[0] * fx + g[1] * fy + g[2] * fz
}

pub fn noise2(x: f64, y: f64, seed: u64) -> f64 {
    let x0 = x.floor();
    let y0 = y.floor();
    let fx = x - x0;
    let fy = y - y0;
    let ix = x0 as i64;
    let iy = y0 as i64;
    let u = fade(fx);
    let v = fade(fy);
    let a00 = grad2(ix, iy, seed, fx, fy);
    let a10 = grad2(ix + 1, iy, seed, fx - 1.0, fy);
    let a01 = grad2(ix, iy + 1, seed, fx, fy - 1.0);
    let a11 = grad2(ix + 1, iy + 1, seed, fx - 1.0, fy - 1.0);
    let a = a00 + u * (a10 - a00);
    let b = a01 + u * (a11 - a01);
    (a + v * (b - a)) * 1.414
}

pub fn noise3(x: f64, y: f64, z: f64, seed: u64) -> f64 {
    let x0 = x.floor();
    let y0 = y.floor();
    let z0 = z.floor();
    let fx = x - x0;
    let fy = y - y0;
    let fz = z - z0;
    let ix = x0 as i64;
    let iy = y0 as i64;
    let iz = z0 as i64;
    let u = fade(fx);
    let v = fade(fy);
    let w = fade(fz);
    let g = |ox: i64, oy: i64, oz: i64| {
        grad3(ix + ox, iy + oy, iz + oz, seed, fx - ox as f64, fy - oy as f64, fz - oz as f64)
    };
    let lerp = |t: f64, a: f64, b: f64| a + t * (b - a);
    let y1 = lerp(v, lerp(u, g(0, 0, 0), g(1, 0, 0)), lerp(u, g(0, 1, 0), g(1, 1, 0)));
    let y2 = lerp(v, lerp(u, g(0, 0, 1), g(1, 0, 1)), lerp(u, g(0, 1, 1), g(1, 1, 1)));
    lerp(w, y1, y2)
}

#[derive(Clone, Copy)]
pub struct Noise {
    pub seed: u64,
}

impl Noise {
    pub fn new(seed: u64) -> Self {
        Self { seed: splitmix64(seed) }
    }

    pub fn noise2(&self, x: f64, y: f64) -> f64 {
        noise2(x, y, self.seed)
    }

    pub fn fbm2(&self, x: f64, y: f64, octaves: u32) -> f64 {
        self.fbm2_lg(x, y, octaves, 2.0, 0.5)
    }

    pub fn fbm2_lg(&self, x: f64, y: f64, octaves: u32, lacunarity: f64, gain: f64) -> f64 {
        let mut total = 0.0;
        let mut amp = 1.0;
        let mut freq = 1.0;
        let mut norm = 0.0;
        for i in 0..octaves {
            let s = splitmix64(self.seed.wrapping_add(i as u64));
            total += noise2(x * freq, y * freq, s) * amp;
            norm += amp;
            amp *= gain;
            freq *= lacunarity;
        }
        total / norm
    }

    pub fn fbm3(&self, x: f64, y: f64, z: f64, octaves: u32) -> f64 {
        let mut total = 0.0;
        let mut amp = 1.0;
        let mut freq = 1.0;
        let mut norm = 0.0;
        for i in 0..octaves {
            let s = splitmix64(self.seed.wrapping_add(i as u64));
            total += noise3(x * freq, y * freq, z * freq, s) * amp;
            norm += amp;
            amp *= 0.5;
            freq *= 2.0;
        }
        total / norm
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hashes_match_python() {
        assert_eq!(splitmix64(12345), 2454886589211414944);
        assert_eq!(hash2(3, -5, 99), 16526743368836086631);
        let r = rand01(3, -5, 99);
        assert!((r - 0.8959165532301244).abs() < 1e-12, "{r}");
    }

    #[test]
    fn noise_matches_python() {
        let n = Noise::new(12345);
        assert_eq!(n.seed, 2454886589211414944);
        let n2 = n.noise2(1.25, -3.5);
        assert!((n2 - 0.36768487467470157).abs() < 1e-9, "{n2}");
        let f = n.fbm2(12.5, -8.25, 4);
        assert!((f - 0.11237998661909268).abs() < 1e-9, "{f}");
        let f3 = n.fbm3(0.3, 1.7, -2.2, 2);
        assert!((f3 - 0.01830294259944106).abs() < 1e-9, "{f3}");
        assert_eq!(n.fbm3(0.0, 0.0, 0.0, 2), 0.0);
    }
}
