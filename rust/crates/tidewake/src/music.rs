//! Korobeiniki, public domain, played as a soft sine line when a sky starts.
//!
//! If the machine has no audio device the game keeps going in silence.

use std::time::Duration;

use rodio::source::{SineWave, Source};
use rodio::{OutputStream, Sink};

const Q: u64 = 280;

// The Tetris-famous opening of Korobeiniki. Frequencies in hertz, then beats.
const THEME: &[(f32, u64)] = &[
    (659.25, 1), (493.88, 1), (523.25, 1), (587.33, 1),
    (523.25, 1), (493.88, 1), (440.00, 1), (440.00, 1),
    (523.25, 1), (659.25, 1), (587.33, 1), (523.25, 1),
    (493.88, 2), (523.25, 1), (587.33, 1),
    (659.25, 1), (523.25, 1), (440.00, 1), (440.00, 2),
    (0.0, 1),
    (587.33, 1), (698.46, 1), (880.00, 1), (783.99, 1), (698.46, 1),
    (659.25, 2), (523.25, 1), (659.25, 1), (587.33, 1), (523.25, 1),
    (493.88, 1), (493.88, 1), (523.25, 1), (587.33, 1),
    (659.25, 1), (523.25, 1), (440.00, 1), (440.00, 2),
];

pub struct Music {
    _stream: OutputStream,
    _sink: Sink,
}

impl Music {
    pub fn start() -> Option<Self> {
        let (stream, handle) = OutputStream::try_default().ok()?;
        let sink = Sink::try_new(&handle).ok()?;
        sink.set_volume(0.18);
        for _ in 0..4 {
            for (hz, beats) in THEME {
                let dur = Duration::from_millis(Q * beats);
                if *hz < 1.0 {
                    let rest = SineWave::new(1.0).take_duration(dur).amplify(0.0);
                    sink.append(rest);
                } else {
                    let note = SineWave::new(*hz).take_duration(dur).amplify(0.2);
                    sink.append(note);
                }
            }
        }
        Some(Self { _stream: stream, _sink: sink })
    }
}
