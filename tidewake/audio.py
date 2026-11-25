"""Tidewake audio: synthesized sound effects plus the composed soundtrack (tidewake/music.py).

The soundtrack is procedurally synthesized with numpy. Each is rendered once, in a separate
low-priority process, on first launch and cached on disk (keyed by music.cache_key()), then
loaded from the cache. Playback goes through the SDL mixer (pygame-ce) with a pyglet fallback;
tracks crossfade by volume ramps so nothing ever starts or stops on a loud sample.
"""
import io
import os
import threading
import time
import random
import struct

import numpy as np

RATE = 22050
MUSIC_RATE = 44100
MUSIC_CHANNELS = 4
MUSIC_GAIN = 0.32          # the songs are mastered hot; this sits them under the SFX
FADE_RATE = 0.22           # volume per second -> ~4 s crossfades
DAY_SONGS = ('lighttide', 'brightreef', 'emberglow', 'highmere')
DAY_SECONDS = 170.0        # rotate daytime songs after about this long


def _wav_stereo(pcm, rate):
    data = np.ascontiguousarray(pcm, dtype='<i2').tobytes()
    hdr = b'RIFF' + struct.pack('<I', 36 + len(data)) + b'WAVEfmt ' + struct.pack('<IHHIIHH', 16, 1, 2, rate, rate * 4, 4, 16)
    return hdr + b'data' + struct.pack('<I', len(data)) + data
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


SOUNDS = ['shape', 'click', 'hover', 'mote', 'chord', 'bounce', 'whoosh', 'awaken', 'tide'] + \
    [f'{p}_{m}' for p in ('gather', 'step') for m in ('stone', 'soft', 'leaf', 'sand', 'wood', 'glass', 'water', 'puff')]


def _declick(samples, ms=6):
    """Short fade at both ends so no sound starts or stops on a non-zero sample (no pops)."""
    s = np.asarray(samples, dtype=np.float64).copy()
    k = min(len(s) // 4, int(RATE * ms / 1000))
    if k > 1:
        r = np.linspace(0.0, 1.0, k)
        s[:k] *= r
        s[-k:] *= r[::-1]
    return s


class _Pygame:
    """SDL mixer: mixing and looping happen in SDL's own native audio thread, so Python being busy
    (loading land, compiling, garbage collection) can't starve the sound."""
    def __init__(self):
        import os
        os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
        import pygame.mixer as mx
        mx.pre_init(MUSIC_RATE, -16, 2, 2048)
        mx.init(MUSIC_RATE, -16, 2, 2048)
        if not mx.get_init():
            raise RuntimeError('no audio device')
        mx.set_num_channels(32)
        mx.set_reserved(MUSIC_CHANNELS)  # channels 0..3: soundtrack crossfades
        self.mx = mx

    def load(self, samples):
        a = np.clip(samples, -1, 1)
        a = np.interp(np.arange(len(a) * 2) / 2, np.arange(len(a)), a)   # SFX are 22.05 kHz; mixer runs at 44.1
        st = (np.repeat(a[:, None], 2, 1) * 30000).astype('<i2')
        return self.mx.Sound(buffer=st.tobytes())

    def load_pcm(self, pcm):
        return self.mx.Sound(buffer=np.ascontiguousarray(pcm, dtype='<i2').tobytes())

    def play(self, snd, volume):
        ch = snd.play()
        if ch is not None:
            ch.set_volume(volume)

    def music_channel(self, k):
        return self.mx.Channel(k)


class Audio:
    def __init__(self, sounds=0.8, music=0.7):
        self.sfx_volume = sounds
        self.music_volume = music
        self.sounds = {}
        self.enabled = False
        self.backend = None
        self.music = {}            # song name -> loaded sound, filled in by the prep thread
        self.music_status = 'idle'
        self.chan = {}             # song name -> [channel/player, current volume]
        self.day_i, self.day_t, self.current = 0, 0.0, None
        self._pool, self._quit = None, False
        try:
            try:
                self.pg = _Pygame()
                self.backend = 'sdl'
            except Exception as e:
                print('sdl audio unavailable, using pyglet:', e)
                import pyglet.media
                self._media = pyglet.media
                try:
                    from pyglet.media.drivers.base import AbstractAudioPlayer
                    AbstractAudioPlayer.audio_buffer_length = 2.5
                except Exception:
                    pass
                self.backend = 'pyglet'
            rng = np.random.default_rng(11)
            for name in SOUNDS:
                self.sounds[name] = [self._load(name, _declick(_synth(name, rng))) for _ in range(2 if name != 'awaken' else 1)]
            self.enabled = True
        except Exception as e:
            print('audio disabled:', e)

    def _load(self, name, samples):
        if self.backend == 'sdl':
            return self.pg.load(samples)
        return self._media.load(f'{name}.wav', file=io.BytesIO(_wav(samples)), streaming=False)

    def play(self, name, volume=1.0, pitch=None):
        if not self.enabled or self.sfx_volume <= 0:
            return
        v = self.sounds.get(name)
        if not v:
            return
        try:
            snd = random.choice(v)
            if self.backend == 'sdl':
                self.pg.play(snd, min(1.0, self.sfx_volume * volume))
            else:
                p = snd.play()
                p.volume = self.sfx_volume * volume
                p.pitch = pitch if pitch else random.uniform(0.94, 1.06)
        except Exception:
            pass

    # ------------------------------------------------------------ soundtrack prep
    def start_music(self, cache_dir):
        """Load cached songs, rendering missing ones in a background low-priority process."""
        if not self.enabled:
            return
        threading.Thread(target=self._prep_music, args=(cache_dir,), daemon=True).start()

    def _prep_music(self, cache_dir):
        from . import music
        pool = None
        try:
            self.music_status = 'preparing'
            key = music.cache_key()
            os.makedirs(cache_dir, exist_ok=True)
            for f in os.listdir(cache_dir):                    # drop songs from older versions
                if f.endswith('.npy') and not f.endswith(f'-{key}.npy'):
                    try:
                        os.remove(os.path.join(cache_dir, f))
                    except OSError:
                        pass
            for name in music.SONGS:
                if self._quit:
                    break
                path = os.path.join(cache_dir, f'{name}-{key}.npy')
                try:
                    if not os.path.exists(path):
                        if pool is None:
                            import multiprocessing as mp
                            from concurrent.futures import ProcessPoolExecutor
                            from . import workers
                            pool = self._pool = ProcessPoolExecutor(max_workers=1, mp_context=mp.get_context('spawn'),
                                                                    initializer=workers.init_worker)
                        t0 = time.time()
                        pool.submit(workers.music_job, name, path).result()
                        print(f'music: rendered {name} in {time.time() - t0:.1f}s')
                    pcm = np.load(path)
                    if pcm.ndim != 2 or pcm.shape[1] != 2:
                        raise ValueError('bad cache file')
                    self.music[name] = self._load_pcm(name, pcm)
                except Exception as e:
                    if self._quit:
                        break
                    print('music: could not prepare', name, e)
                    try:
                        os.remove(path)
                    except OSError:
                        pass
            self.music_status = 'ready'
        except Exception as e:
            self.music_status = 'failed'
            print('music disabled:', e)
        finally:
            if pool is not None:
                pool.shutdown(wait=False)

    def shutdown(self):
        """Quitting: stop any in-progress song render right away (it resumes next launch)."""
        self._quit = True
        pool = self._pool
        if pool is not None:
            try:
                for proc in list(getattr(pool, '_processes', {}).values()):
                    proc.terminate()
                pool.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass

    def _load_pcm(self, name, pcm):
        if self.backend == 'sdl':
            return self.pg.load_pcm(pcm)
        return self._media.load(f'{name}.wav', file=io.BytesIO(_wav_stereo(pcm, MUSIC_RATE)), streaming=False)

    def set_volumes(self, sounds, music):
        self.sfx_volume, self.music_volume = sounds, music

    # ------------------------------------------------------------ soundtrack playback
    def pick(self, dt, dusk=0.0, mode='game', rain=False, tutorial=False, water=False):
        """Which song should be playing now (None if nothing is ready yet)."""
        ready = self.music
        if mode != 'game':
            return 'windward' if 'windward' in ready else None
        if tutorial:
            want = 'firstlight'
        elif water:
            want = 'undertide'
        elif dusk > 0.6:
            want = 'dusktide'
        elif rain:
            want = 'rainwake'
        elif dusk > 0.3:
            want = 'emberglow'                                   # evening
        else:
            self.day_t += dt
            if self.day_t > DAY_SECONDS:
                self.day_t, self.day_i = 0.0, self.day_i + 1
            want = DAY_SONGS[self.day_i % len(DAY_SONGS)]
        if want in ready:
            return want
        if self.current in ready and self.current != 'windward':
            return self.current
        for name in ('firstlight', 'undertide', 'rainwake') + DAY_SONGS + ('dusktide',):
            if name in ready:
                return name
        return None

    def update(self, dt, dusk=0.0, mode='game', under=0.0, rain=False, tutorial=False, water=False):
        """Crossfade between songs; the cave layer fades in underground."""
        if not self.enabled:
            return
        try:
            want = self.pick(dt, dusk, mode, rain=rain, tutorial=tutorial, water=water)
            self.current = want
            mv = self.music_volume * MUSIC_GAIN
            under = under if mode == 'game' and 'cave' in self.music else 0.0
            targets = {}
            if want:
                targets[want] = mv * (1.0 - 0.75 * under)
            if under > 0:
                targets['cave'] = max(targets.get('cave', 0.0), mv * under)
            for name in list(set(self.chan) | set(targets)):
                tgt = targets.get(name, 0.0)
                ent = self.chan.get(name)
                if ent is None:
                    if tgt <= 0.001 or name not in self.music:
                        continue
                    h = self._start(name)
                    if h is None:
                        continue
                    ent = self.chan[name] = [h, 0.0]
                v = ent[1] + max(-FADE_RATE * dt, min(FADE_RATE * dt, tgt - ent[1]))
                ent[1] = v
                self._set_vol(ent[0], v)
                if tgt <= 0.0 and v <= 0.0005:
                    self._stop(ent[0])
                    del self.chan[name]
        except Exception as e:
            print('music update error:', e)

    def _start(self, name):
        if self.backend == 'sdl':
            used = {e[0] for e in self.chan.values()}          # sdl handles are channel indices
            for i in range(MUSIC_CHANNELS):
                ch = self.pg.music_channel(i)
                if i not in used and not ch.get_busy():
                    ch.set_volume(0.0)
                    ch.play(self.music[name], loops=-1)
                    return i
            return None
        pl = self._media.Player()
        pl.queue(self.music[name])
        pl.loop = True
        pl.volume = 0.0
        pl.play()
        return pl

    def _set_vol(self, h, v):
        if self.backend == 'sdl':
            self.pg.music_channel(h).set_volume(v)
        elif abs(getattr(h, '_tw_vol', -1) - v) > 0.003:
            h.volume = v
            h._tw_vol = v

    def _stop(self, h):
        try:
            if self.backend == 'sdl':
                self.pg.music_channel(h).stop()
            else:
                h.pause()
                h.delete()
        except Exception:
            pass
