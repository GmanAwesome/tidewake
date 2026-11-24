"""All sound is synthesised at startup: soft bells, breathy gathers, a slow generative score.

The music is two calm pre-rendered loops (C major for Lighttide, A minor for Dusktide):
slow overlapping pad chords and a sparse soft melody with an echo, crossfaded as the tide turns.
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
    s = (np.sin(2 * np.pi * freq * t) + 0.18 * bright * np.sin(2 * np.pi * freq * 2.0 * t) * np.exp(-t * 3)
         + 0.05 * bright * np.sin(2 * np.pi * freq * 3.0 * t) * np.exp(-t * 6))
    return s * _env(n, 0.02, 2.4) * 0.3


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
            s = s * 0.7 + np.sin(2 * np.pi * (400 + 300 * t / dur) * t) * _env(n, 0.05, 8) * 0.05
        return s * (0.3 if step else 0.6)
    if kind == 'shape':
        n = int(RATE * 0.35)
        t = np.arange(n) / RATE
        f = rng.choice([392.0, 440.0, 523.25, 587.33])
        return (np.sin(2 * np.pi * f * t) * 0.5 + np.sin(2 * np.pi * f * 1.5 * t) * 0.2) * _env(n, 0.01, 9) * 0.45
    if kind == 'click':
        n = int(RATE * 0.07)
        t = np.arange(n) / RATE
        return np.sin(2 * np.pi * 660 * t) * _env(n, 0.003, 50) * 0.25
    if kind == 'hover':
        n = int(RATE * 0.05)
        t = np.arange(n) / RATE
        return np.sin(2 * np.pi * 880 * t) * _env(n, 0.004, 70) * 0.06
    if kind == 'mote':
        return _bell(_note(rng.choice([0, 4, 7]), 523.25), 0.7, 0.3) * 0.35
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
        return out * 0.45
    if kind == 'tide':
        out = np.zeros(int(RATE * 3.0))
        for i, s in enumerate([12, 7, 4, 0]):
            b = _bell(_note(s, 220.0), 2.4, 0.5)
            o = int(i * RATE * 0.3)
            out[o:o + len(b)] += b[:len(out) - o]
        return out * 0.35
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


def _addwrap(out, s, start):
    n = len(out)
    start %= n
    a = min(len(s), n - start)
    out[start:start + a] += s[:a]
    if a < len(s):
        out[:len(s) - a] += s[a:]


def _track(dusk, seconds=64.0, seed=5):
    """A calm, seamless ambient loop: slow pad chords plus a sparse soft melody, all in one key."""
    rng = np.random.default_rng(seed + (7 if dusk else 0))
    n = int(RATE * seconds)
    out = np.zeros(n)
    if dusk:      # A minor: Am9, Fmaj7, Dm9, Em7 (semitones from A2)
        base, chords, scale = 110.0, [[0, 7, 12, 14, 15], [-4, 3, 7, 12, 15], [-7, 0, 3, 7, 10], [-5, 2, 7, 10, 14]], [12, 15, 17, 19, 22, 24]
    else:         # C major: Cadd9, Am7, Fmaj7, G6 (semitones from C3)
        base, chords, scale = 130.81, [[0, 7, 12, 14, 16], [-3, 4, 7, 12, 16], [-7, 0, 4, 9, 16], [-5, 2, 7, 11, 16]], [12, 14, 16, 19, 21, 24, 26]
    seg = n // len(chords)
    L = seg * 2                                   # each chord overlaps the next by half
    t = np.arange(L) / RATE
    win = np.sin(np.linspace(0, np.pi, L)) ** 2
    for i, ch in enumerate(chords):
        s = np.zeros(L)
        for semi in ch:
            f = base * 2 ** (semi / 12)
            for det in (-0.4, 0.4):
                s += np.sin(2 * np.pi * (f + det) * t + rng.uniform(0, 6)) * 0.4
            s += np.sin(2 * np.pi * f * 2 * t) * 0.04
        s *= 1 + 0.08 * np.sin(2 * np.pi * t / 5.3)
        _addwrap(out, s * win, i * seg)
    out = out / np.abs(out).max() * 0.16
    # sparse melody, soft attacks, with a gentle echo
    mel = np.zeros(n)
    pos = rng.uniform(2, 4)
    last = rng.integers(len(scale))
    while pos < seconds - 1:
        last = int(np.clip(last + rng.choice([-2, -1, -1, 0, 1, 1, 2]), 0, len(scale) - 1))
        f = base * 2 ** (scale[last] / 12)
        dur = 3.0
        tt = np.arange(int(RATE * dur)) / RATE
        note = (np.sin(2 * np.pi * f * tt) + 0.12 * np.sin(2 * np.pi * f * 2 * tt)) * np.minimum(1, tt / 0.12) * np.exp(-tt * 1.4)
        _addwrap(mel, note * rng.uniform(0.7, 1.0), int(pos * RATE))
        pos += rng.choice([1.5, 2.0, 2.0, 3.0, 4.0, 6.0]) * (1.3 if dusk else 1.0)
    for k, g in ((1, 0.32), (2, 0.12)):
        mel = mel + np.roll(mel, int(RATE * 0.42 * k)) * g
    out += _smooth(mel, 3)[:n] * 0.06
    return out / np.abs(out).max() * 0.3


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
            try:
                # keep ~2.5 s of sound queued so a busy frame (loading, compiling) can't starve the music
                from pyglet.media.drivers.base import AbstractAudioPlayer
                AbstractAudioPlayer.audio_buffer_length = 2.5
            except Exception:
                pass
            rng = np.random.default_rng(11)
            for name in SOUNDS:
                self.sounds[name] = [self._load(name, _synth(name, rng)) for _ in range(2 if name != 'awaken' else 1)]
            self.tracks = None
            self.players = [None, None]
            import threading
            threading.Thread(target=self._build_tracks, daemon=True).start()
            self.mix = 0.0
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

    def _build_tracks(self):
        try:
            self.tracks = [self._load('light', _track(False)), self._load('dusk', _track(True))]
        except Exception as e:
            print('music disabled:', e)

    def set_volumes(self, sounds, music):
        self.sfx_volume, self.music_volume = sounds, music

    def update(self, dt, dusk=0.0, playing=True):
        """Two looping ambient tracks (light / dusk), crossfaded slowly as the tide turns."""
        if not self.enabled or self.tracks is None:
            return
        try:
            target = 1.0 if dusk > 0.5 else 0.0
            self.mix += (target - self.mix) * min(1.0, dt / 6.0)
            for k in (0, 1):
                v = self.music_volume * 0.9 * (self.mix if k else 1.0 - self.mix)
                pl = self.players[k]
                if pl is None and v > 0.001:
                    pl = self.players[k] = self._media.Player()
                    pl.queue(self.tracks[k])
                    pl.loop = True
                    pl.volume = 0.0
                    pl.play()
                if pl is not None and abs(getattr(pl, '_tw_vol', -1) - v) > 0.004:
                    pl.volume = v
                    pl._tw_vol = v
        except Exception:
            pass
