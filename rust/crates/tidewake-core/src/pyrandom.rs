//! CPython `random.Random` (MT19937), used for a seed's temperament and trees.
//!
//! `random()` matches `Lib/random.py` + `_random`: two tempered words,
//! `(a>>5) * 2^26 + (b>>6)`, divided by `2^53`.

const N: usize = 624;
const M: usize = 397;

pub struct PyRng {
    mt: [u32; N],
    index: usize,
}

impl PyRng {
    pub fn seed_u64(seed: u64) -> Self {
        let mut rng = Self { mt: [0; N], index: N };
        if seed == 0 {
            rng.init_by_array(&[0]);
        } else if seed <= u32::MAX as u64 {
            rng.init_by_array(&[seed as u32]);
        } else {
            rng.init_by_array(&[seed as u32, (seed >> 32) as u32]);
        }
        rng
    }

    fn init_genrand(&mut self, s: u32) {
        self.mt[0] = s;
        for i in 1..N {
            let prev = self.mt[i - 1];
            self.mt[i] = 1812433253u32
                .wrapping_mul(prev ^ (prev >> 30))
                .wrapping_add(i as u32);
        }
        self.index = N;
    }

    fn init_by_array(&mut self, key: &[u32]) {
        self.init_genrand(19650218);
        let mut i = 1usize;
        let mut j = 0usize;
        let key_length = key.len();
        let mut k = N.max(key_length);
        while k > 0 {
            let prev = self.mt[i - 1];
            self.mt[i] = (self.mt[i] ^ ((prev ^ (prev >> 30)).wrapping_mul(1664525)))
                .wrapping_add(key[j])
                .wrapping_add(j as u32);
            i += 1;
            j += 1;
            if i >= N {
                self.mt[0] = self.mt[N - 1];
                i = 1;
            }
            if j >= key_length {
                j = 0;
            }
            k -= 1;
        }
        k = N - 1;
        while k > 0 {
            let prev = self.mt[i - 1];
            self.mt[i] = (self.mt[i] ^ ((prev ^ (prev >> 30)).wrapping_mul(1566083941)))
                .wrapping_sub(i as u32);
            i += 1;
            if i >= N {
                self.mt[0] = self.mt[N - 1];
                i = 1;
            }
            k -= 1;
        }
        self.mt[0] = 0x8000_0000;
        self.index = N;
    }

    pub fn gen_u32(&mut self) -> u32 {
        if self.index >= N {
            for i in 0..N {
                let x = (self.mt[i] & 0x8000_0000) | (self.mt[(i + 1) % N] & 0x7fff_ffff);
                let mut xa = self.mt[(i + M) % N] ^ (x >> 1);
                if x & 1 != 0 {
                    xa ^= 0x9908_b0df;
                }
                self.mt[i] = xa;
            }
            self.index = 0;
        }
        let mut y = self.mt[self.index];
        self.index += 1;
        y ^= y >> 11;
        y ^= (y << 7) & 0x9d2c_5680;
        y ^= (y << 15) & 0xefc6_0000;
        y ^= y >> 18;
        y
    }

    pub fn random(&mut self) -> f64 {
        let a = (self.gen_u32() >> 5) as f64;
        let b = (self.gen_u32() >> 6) as f64;
        (a * 67_108_864.0 + b) * (1.0 / 9_007_199_254_740_992.0)
    }

    pub fn uniform(&mut self, a: f64, b: f64) -> f64 {
        a + (b - a) * self.random()
    }

    fn getrandbits(&mut self, k: u32) -> u64 {
        if k == 0 {
            return 0;
        }
        if k <= 32 {
            return (self.gen_u32() >> (32 - k)) as u64;
        }
        let mut v = 0u64;
        let mut left = k;
        let mut shift = 0;
        while left > 0 {
            let take = left.min(32);
            let bits = (self.gen_u32() >> (32 - take)) as u64;
            v |= bits << shift;
            shift += take;
            left -= take;
        }
        v
    }

    fn randbelow(&mut self, n: u64) -> u64 {
        let k = 64 - n.leading_zeros();
        loop {
            let r = self.getrandbits(k);
            if r < n {
                return r;
            }
        }
    }

    /// Inclusive, matching `random.randint`.
    pub fn randint(&mut self, a: i32, b: i32) -> i32 {
        let width = (b as i64 - a as i64 + 1) as u64;
        a + self.randbelow(width) as i32
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::noise::splitmix64;

    #[test]
    fn uniforms_match_python_seed_7() {
        let mut rng = PyRng::seed_u64(splitmix64(7));
        let a = rng.uniform(120.0, 300.0);
        let b = rng.uniform(-0.04, 0.16);
        let c = rng.uniform(20.0, 110.0);
        assert!((a - 196.6337159828866).abs() < 1e-9, "{a}");
        assert!((b - 0.13640592363954251).abs() < 1e-9, "{b}");
        assert!((c - 90.1995795591472).abs() < 1e-9, "{c}");
    }

    #[test]
    fn random_matches_known_seeds() {
        let cases = [
            (0u64, 0.8444218515250481_f64),
            (1, 0.13436424411240122),
            (16294208416658607535, 0.2584797560128377),
            (10451216379200822465, 0.6098380585699298),
            (2617385799015359219, 0.2545342047455593),
            (13679457532755275413, 0.0005965909310217121),
        ];
        for (seed, want) in cases {
            let mut rng = PyRng::seed_u64(seed);
            let got = rng.random();
            assert!((got - want).abs() < 1e-12, "{seed} {got}");
        }
    }

    #[test]
    fn randint_matches_python() {
        let mut rng = PyRng::seed_u64(99);
        let a: Vec<i32> = (0..8).map(|_| rng.randint(2, 4)).collect();
        let b: Vec<i32> = (0..6).map(|_| rng.randint(8, 12)).collect();
        assert_eq!(a, vec![3, 3, 2, 4, 2, 2, 2, 2]);
        assert_eq!(b, vec![8, 10, 11, 12, 12, 8]);
    }
}
