//! Lighttide and Dusktide. Values match `tide.py`.

#[derive(Clone, Copy)]
pub struct Atmo {
    pub dusk: f32,
    pub zenith: [f32; 3],
    pub horizon: [f32; 3],
    pub sun: [f32; 3],
    pub cloud: [f32; 3],
    pub deep: [f32; 3],
    pub name: &'static str,
}

// dusk, zenith, horizon, sun, cloud top, cloud deep — the columns `tide.py` interpolates
const KEYS: &[(f32, [f32; 3], [f32; 3], [f32; 3], [f32; 3], [f32; 3])] = &[
    (0.00, [0.46, 0.66, 0.94], [0.96, 0.89, 0.86], [1.00, 0.93, 0.82], [1.00, 0.97, 0.96], [0.78, 0.76, 0.90]),
    (0.50, [0.36, 0.40, 0.70], [1.00, 0.66, 0.52], [1.00, 0.66, 0.42], [1.00, 0.80, 0.70], [0.66, 0.48, 0.66]),
    (1.00, [0.07, 0.08, 0.22], [0.38, 0.28, 0.50], [0.30, 0.32, 0.58], [0.52, 0.48, 0.74], [0.20, 0.16, 0.34]),
];

pub fn phase_of(time: f32) -> f32 {
    (time / 720.0).rem_euclid(1.0)
}

pub fn dusk_amount(phase: f32) -> f32 {
    0.5 - 0.5 * (std::f32::consts::TAU * phase).cos()
}

pub fn name(phase: f32) -> &'static str {
    let d = dusk_amount(phase);
    let rising = (phase % 1.0) > 0.5;
    if d < 0.25 {
        "Lighttide"
    } else if d > 0.75 {
        "Dusktide"
    } else if rising {
        "Turning to light"
    } else {
        "Turning to dusk"
    }
}

pub fn atmosphere(time: f32) -> Atmo {
    let phase = phase_of(time);
    let d = dusk_amount(phase);
    let mut a = 0;
    for i in 0..KEYS.len() - 1 {
        if KEYS[i].0 <= d && d <= KEYS[i + 1].0 {
            a = i;
            break;
        }
    }
    let (d0, z0, h0, s0, c0, e0) = KEYS[a];
    let (d1, z1, h1, s1, c1, e1) = KEYS[a + 1];
    let t = if (d1 - d0).abs() < 1e-5 { 0.0 } else { (d - d0) / (d1 - d0) };
    let mix = |p: [f32; 3], q: [f32; 3]| [p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t, p[2] + (q[2] - p[2]) * t];
    Atmo {
        dusk: d,
        zenith: mix(z0, z1),
        horizon: mix(h0, h1),
        sun: mix(s0, s1),
        cloud: mix(c0, c1),
        deep: mix(e0, e1),
        name: name(phase),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn lighttide_and_dusktide_match_the_table() {
        let light = atmosphere(0.0);
        assert!(light.dusk < 0.01, "{}", light.dusk);
        assert!((light.zenith[2] - 0.94).abs() < 1e-3);
        assert_eq!(light.name, "Lighttide");
        // phase 0.5 is the depth of dusk: dusk_amount = 1
        let dusk = atmosphere(360.0);
        assert!(dusk.dusk > 0.99, "{}", dusk.dusk);
        assert_eq!(dusk.name, "Dusktide");
        assert!((dusk.zenith[0] - 0.07).abs() < 1e-3);
        assert!((light.cloud[1] - 0.97).abs() < 1e-3);
        assert!((dusk.deep[2] - 0.34).abs() < 1e-3);
    }
}
