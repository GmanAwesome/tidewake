"""All sound is synthesised at startup: soft bells, breathy gathers, a slow generative score.

The music is a looping pad of two warm chords plus bell notes picked from a pentatonic
scale at gentle random intervals; the scale drops lower and slower in the dusk tide.
If there is no audio device, the game simply runs silently.
"""
import io
import random
import struct

import numpy as np

RATE = 22050
PENTA_LIGHT = [0, 2, 4, 7, 9, 12, 14, 16]       # major pentatonic (semitones)
PENTA_DUSK = [0, 3, 5, 7, 10, 12, 15]            # minor pentatonic


def _wav(samples):
    s = np.clip(samples, -1, 1)
    data = (s * 30000).astype('<i2').tobytes()
    hdr = b'RIFF' + struct.pack('<I', 36 + len(data)) + b'WAVEfmt ' + struct.pack('<IHHIIHH', 16, 1, 1, RATE, RATE * 2, 2, 16)
    return hdr + b'data' + struct.pack('<I', len(data)) + data


def _smooth(x, k):
    """Cheap low-pass: moving average of width k (via cumulative sum)."""
    if k <= 1:
        return x
    c = np.cumsum(np.concatenate([np.zeros(k), x]))
    return (c[k:] - c[:-k]) / k


def _env(n, attack=0.005, decay=6.0):
    t = np.arange(n) / RATE
    return np.minimum(1, t / attack) * np.exp(-t * decay)


def _bell(freq, dur=1.6, bright=1.0):
    n = int(RATE * dur)
    t = np.arange(n) / RATE
    s = (np.sin(2 * np.pi * freq * t) + 0.35 * bright * np.sin(2 * np.pi * freq * 2.76 * t) * np.exp(-t * 3)
         + 0.18 * bright * np.sin(2 * np.pi * freq * 5.4 * t) * np.exp(-t * 6))
    return s * _env(n, 0.004, 2.2) * 0.35


def _note(semi, base=261.63):
    return base * 2 ** (semi / 12)


def _synth(kind, rng):
    if kind.startswith('gather_') or kind.startswith('step_'):
        mat = kind.split('_', 1)[1]
        step = kind.startswith('step_')
        dur = 0.09 if step else 0.30
        n = int(RATE * dur)
        t = np.arange(n) / RATE
        noise = rng.uniform(-1, 1, n)
        if mat in ('soft', 'leaf'):
            s = _smooth(noise, 6) * _env(n, 0.004, 26 if step else 10)
        elif mat in ('sand',):
            s = _smooth(noise, 10) * _env(n, 0.01, 20 if step else 9) * 1.4
        elif mat == 'wood':
            s = (np.sin(2 * np.pi * rng.uniform(180, 240) * t) * 0.6 + _smooth(noise, 5) * 0.4) * _env(n, 0.002, 22)
        elif mat == 'glass':
            s = sum(np.sin(2 * np.pi * rng.uniform(1400, 3600) * t) * rng.uniform(0.15, 0.35) for _ in range(4))
            s = s * _env(n, 0.002, 9)
        elif mat == 'water':
            s = _smooth(noise, 14) * _env(n, 0.03, 7) * 1.6
        elif mat == 'puff':
            s = _smooth(noise, 20) * _env(n, 0.04, 8) * 1.8
        else:
            s = (_smooth(noise, 3) * 0.7 + np.sin(2 * np.pi * rng.uniform(110, 160) * t) * 0.35) * _env(n, 0.003, 18)
        if not step:      # gathering: a soft rising shimmer as the cell dissolves into essence
            s = s * 0.7 + np.sin(2 * np.pi * (600 + 900 * t / dur) * t) * _env(n, 0.05, 6) * 0.12
        return s * (0.3 if step else 0.6)
    if kind == 'shape':
        n = int(RATE * 0.35)
        t = np.arange(n) / RATE
        f = rng.choice([392.0, 440.0, 523.25, 587.33])
        return (np.sin(2 * np.pi * f * t) * 0.5 + np.sin(2 * np.pi * f * 1.5 * t) * 0.2) * _env(n, 0.01, 9) * 0.45
    if kind == 'click':
        n = int(RATE * 0.07)
        t = np.arange(n) / RATE
        return np.sin(2 * np.pi * 1046 * t) * _env(n, 0.002, 50) * 0.35
    if kind == 'hover':
        n = int(RATE * 0.05)
        t = np.arange(n) / RATE
        return np.sin(2 * np.pi * 1568 * t) * _env(n, 0.002, 70) * 0.12
    if kind == 'mote':
        return _bell(_note(rng.choice(PENTA_LIGHT), 783.99), 1.0, 0.6) * 0.6
    if kind == 'chord':
        return _bell(_note(rng.choice([0, 4, 7])), 0.6, 0.3) * 0.5
    if kind == 'bounce':
        n = int(RATE * 0.4)
        t = np.arange(n) / RATE
        return np.sin(2 * np.pi * (200 + 500 * t) * t) * _env(n, 0.005, 7) * 0.5
    if kind == 'whoosh':
        n = int(RATE * 1.2)
        return _smooth(rng.uniform(-1, 1, n), 30) * np.sin(np.linspace(0, np.pi, n)) * 1.5
    if kind == 'awaken':
        out = np.zeros(int(RATE * 4.5))
        for i, s in enumerate([0, 4, 7, 12, 16, 19, 24]):
            b = _bell(_note(s, 196.0), 3.0, 0.8)
            o = int(i * RATE * 0.18)
            out[o:o + len(b)] += b[:len(out) - o]
        return out * 0.7
    if kind == 'tide':
        out = np.zeros(int(RATE * 3.0))
        for i, s in enumerate([12, 7, 4, 0]):
            b = _bell(_note(s, 220.0), 2.4, 0.5)
            o = int(i * RATE * 0.3)
            out[o:o + len(b)] += b[:len(out) - o]
        return out * 0.6
    return np.zeros(100)


def _pad(chords, seconds_each=8.0, base=130.81):
    """A slow, breathing pad looping through chords (semitone lists)."""
    total = int(RATE * seconds_each * len(chords))
    out = np.zeros(total)
    t = np.arange(int(RATE * seconds_each)) / RATE
    seg = len(t)
    fade = np.sin(np.linspace(0, np.pi, seg)) ** 1.5
    for i, ch in enumerate(chords):
        s = np.zeros(seg)
        for semi in ch:
            f = base * 2 ** (semi / 12)
            for det in (-0.6, 0.6):
                s += np.sin(2 * np.pi * (f + det) * t + det) * 0.5
                s += np.sin(2 * np.pi * (f * 2 + det) * t) * 0.08
        a = i * seg
        out[a:a + seg] += s * fade
        # crossfade tail into the next chord (wrapping)
    out = out + np.roll(out, seg // 2) * 0.6
    out = out / np.abs(out).max() * 0.22
    return out


SOUNDS = ['shape', 'click', 'hover', 'mote', 'chord', 'bounce', 'whoosh', 'awaken', 'tide'] + \
    [f'{p}_{m}' for p in ('gather', 'step') for m in ('stone', 'soft', 'leaf', 'sand', 'wood', 'glass', 'water', 'puff')]


class Audio:
    def __init__(self, sounds=0.8, music=0.7):
        self.sfx_volume = sounds
        self.music_volume = music
        self.sounds = {}
        self.enabled = False
        self.pad_player = None
        self.next_note = 3.0
        self.bells = {}
        try:
            import pyglet
            import pyglet.media
            self._media = pyglet.media
            rng = np.random.default_rng(11)
            for name in SOUNDS:
                self.sounds[name] = [self._load(name, _synth(name, rng)) for _ in range(2 if name != 'awaken' else 1)]
            for semi in sorted(set(PENTA_LIGHT + PENTA_DUSK)):
                self.bells[semi] = self._load(f'b{semi}', _bell(_note(semi, 523.25), 3.2, 0.5) * 0.5)
            self.pad = self._load('pad', _pad([[0, 7, 16, 19], [-3, 4, 12, 16], [-7, 0, 9, 16], [-5, 2, 11, 14]], 7.0))
            self.enabled = True
        except Exception as e:
            print('audio disabled:', e)

    def _load(self, name, samples):
        return self._media.load(f'{name}.wav', file=io.BytesIO(_wav(samples)), streaming=False)

    def play(self, name, volume=1.0, pitch=None):
        if not self.enabled or self.sfx_volume <= 0:
            return
        v = self.sounds.get(name)
        if not v:
            return
        try:
            p = random.choice(v).play()
            p.volume = self.sfx_volume * volume
            p.pitch = pitch if pitch else random.uniform(0.94, 1.06)
        except Exception:
            pass

    def set_volumes(self, sounds, music):
        self.sfx_volume, self.music_volume = sounds, music
        if self.pad_player is not None:
            try:
                self.pad_player.volume = self.music_volume * 0.8
            except Exception:
                pass

    def update(self, dt, dusk=0.0, playing=True):
        """Keep the pad looping and drop a bell note now and then."""
        if not self.enabled:
            return
        try:
            if self.pad_player is None and self.music_volume > 0:
                self.pad_player = self._media.Player()
                self.pad_player.queue(self.pad)
                self.pad_player.loop = True
                self.pad_player.volume = self.music_volume * 0.8
                self.pad_player.play()
            if self.pad_player is not None:
                self.pad_player.volume = self.music_volume * 0.8
            self.next_note -= dt
            if self.next_note <= 0 and self.music_volume > 0:
                scale = PENTA_DUSK if dusk > 0.5 else PENTA_LIGHT
                n = random.randint(1, 3)
                for i in range(n):
                    semi = random.choice(scale)
                    p = self.bells[semi].play()
                    p.volume = self.music_volume * random.uniform(0.25, 0.5)
                    p.pitch = 0.5 if dusk > 0.7 and random.random() < 0.5 else 1.0
                self.next_note = random.uniform(2.5, 7.0) * (1.4 if dusk > 0.5 else 1.0)
        except Exception:
            pass
