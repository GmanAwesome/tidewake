"""Tidewake composed theme: procedural numpy synthesis (no samples).

render(variant) -> (stems dict of float32 (N,2) arrays, sample rate). Stems loop
seamlessly (note tails and reverb wrap circularly), so the game can crossfade
layers (lead / keys / bass / perc / pad / cave) live. mix(stems) -> int16 stereo.
"""
import numpy as np

SR = 44100
MAJOR = [0, 2, 4, 5, 7, 9, 11]
MINOR = [0, 2, 3, 5, 7, 8, 10]

# ---- the composition (scale degrees, 0 = tonic, 7 = octave; None = rest; beats)
# Hook: adapted from Korobeiniki (public-domain Russian folk song, the "Tetris" tune),
# re-keyed into Tidewake's mode and swung.
HOOK = [(4, 1), (1, .5), (2, .5), (3, 1), (2, .5), (1, .5),
        (0, 1), (0, .5), (2, .5), (4, 1), (3, .5), (2, .5),
        (1, 1.5), (2, .5), (3, 1), (4, 1),
        (2, 1), (0, 1), (0, 2),
        (None, .5), (3, 1), (5, .5), (7, 1), (6, .5), (5, .5),
        (4, 1.5), (2, .5), (4, 1), (3, .5), (2, .5),
        (1, 1), (1, .5), (2, .5), (3, 1), (4, 1),
        (2, 1), (0, 1), (0, 2)]
# calm piano break built from the hook's first figure, with space between
BREAK = [(4, 1), (1, .5), (2, .5), (3, 2), (None, 4),
         (5, 1), (3, .5), (4, .5), (5, 2), (None, 4),
         (4, 1), (1, .5), (2, .5), (3, 1), (4, 1), (2, 2), (0, 2),
         (1, 1), (2, 1), (3, 1), (1, 1), (4, 3), (None, 1)]
INTRO = [(None, 8), (4, 1), (1, .5), (2, .5), (3, 2), (None, 4)]   # piano teases the hook
_CH = {'intro': [0, 5, 3, 4], 'A': [0, 0, 4, 0, 3, 0, 4, 0], 'A2': [0, 0, 4, 0, 3, 0, 4, 0],
       'B': [3, 0, 5, 4, 3, 0, 1, 4]}
FORM = [('intro', INTRO), ('A', HOOK), ('A2', HOOK), ('B', BREAK), ('A', HOOK)]


# ---- v5: original legato melodies, one per loop. Korobeiniki (public domain) shows up
# only as 2-3 bars per section of its rhythm/interval cell, marked "K".
# 99 = the home key's V chord (B sections modulate away and cadence back home).
_R = None
_K1 = lambda s: [(s, 1), (s - 3, .5), (s - 2, .5), (s - 1, 1), (s - 2, .5), (s - 3, .5)]   # K cell
_K2 = lambda s: [(s, 1), (s, .5), (s + 2, .5), (s + 4, 1), (s + 3, .5), (s + 2, .5)]      # K cell
LIGHT = dict(
    intro=[(_R, 4), (2, 1), (3, 1), (4, 2), (5, 1), (4, .5), (3, .5), (2, 1), (1, 1),
           (3, .5), (4, .5), (5, .5), (6, .5), (4, 2)],
    A=[(2, .5), (3, .5), (4, 1), (4, .5), (5, .5), (4, 1),            # I
       (3, .5), (2, .5), (1, .5), (2, .5), (3, .5), (5, 1.5),         # vi
       *_K1(7),                                                     # IV  K
       *_K2(4),                                                     # V   K
       (5, 1.5), (6, .5), (7, 1), (4, 1),                           # I   K rhythm
       (5, .5), (4, .5), (3, .5), (2, .5), (1, 1), (2, 1),          # vi
       (3, .5), (2, .5), (1, .5), (3, .5), (5, 1), (4, 1),          # ii
       (3, .5), (4, .5), (5, .5), (6, .5), (4, 2)],                 # V  (half cadence)
    B=[(5, 1.5), (4, .5), (2, 1), (1, 1),                           # (G major) ii
       (2, .5), (1, .5), (-1, 1), (1, 2),                           # V
       (2, 1.5), (4, .5), (7, 1), (6, 1),                           # I
       (5, 2), (4, 1), (2, 1),                                      # vi
       *_K1(7),                                                     # IV  K  (build starts)
       *_K2(4),                                                     # V   K
       (5, .5), (6, .5), (7, .5), (8, .5), (9, .5), (8, .5), (7, .5), (6, .5),   # iii run
       (4, .5), (5, .5), (6, .5), (7, .5), (8, 1.25), (_R, .75)])   # home V -> drop
LIGHT['A2'] = LIGHT['A'][:24] + [
    (5, .5), (6, .5), (7, 1), (8, .5), (7, .5), (5, 1),             # IV
    (3, 1.5), (4, .5), (5, 1), (8, 1),                              # ii  K rhythm
    (7, .5), (6, .5), (8, .5), (7, .5), (6, .5), (4, .5), (1, .5), (6, .5),  # V
    (7, 4)]                                                         # I  (home)
DUSK = dict(
    intro=[(_R, 4), (4, 1.5), (3, .5), (2, 1), (4, 1), (5, 2), (4, 2), (1, 2), (-1, 2)],
    A=[(4, 1.5), (3, .5), (2, 1), (4, 1),                           # i
       (5, 1.5), (4, .5), (2, 2),                                   # VI
       *_K1(5),                                                     # iv  K
       (4, 1), (1, .5), (2, .5), (1, 1), (-1, 1),                   # V
       (0, 1.5), (1, .5), (2, 1), (4, 1),                           # i   K rhythm
       (5, 1), (4, 1), (5, 1), (7, 1),                              # VI
       (8, 1.5), (7, .5), (5, 1), (3, 1),                           # iv
       (4, 1), (6, 1), (4, 2)],                                     # V
    B=[(5, 2), (4, 1), (3, 1),                                      # (C major) IV
       (4, 1.5), (3, .5), (2, 1), (1, 1),                           # V
       (2, 1), (4, 1), (6, 2),                                      # iii
       (5, 3), (4, 1),                                              # vi
       *_K1(5),                                                     # ii  K
       *_K2(4),                                                     # V   K
       (7, 2), (4, 1), (2, 1),                                      # I
       (1, 1), (2, 1), (1, 1), (-1, 1)])                            # home V
DUSK['A2'] = DUSK['A'][:18] + [
    (2, 1), (4, 1), (5, 1), (7, 1),                                 # VI
    (8, 1.5), (7, .5), (5, 1), (3, 1),                              # iv
    (4, .5), (6, .5), (8, .5), (7, .5), (6, .5), (4, .5), (1, .5), (-1, .5),  # V
    (0, 4)]                                                         # i (home)
CAVE = dict(
    intro=[(_R, 4), (0, 2), (2, 1), (4, 1), (5, 2), (4, 2), (1, 2), (-1, 2)],
    A=[(0, 2), (2, 1), (4, 1), (5, 2), (4, 1), (2, 1), (3, 1), (5, 1), (7, 2), (6, 2), (4, 2),
       *_K1(4), *_K2(0),                                            # i, VI  K
       (3, 2), (5, 1), (3, 1), (1, 2), (-1, 2)],
    B=[(5, 2), (7, 2), (8, 1.5), (7, .5), (5, 2), (4, 2), (2, 1), (0, 1), (1, 2), (4, 2),
       (2, 1.5), (3, .5), (5, 2), *_K1(5), (4, 1), (6, 1), (8, 1), (6, 1), (7, 4)])
CAVE['A2'] = CAVE['A']
for _m in (LIGHT, DUSK, CAVE):
    for _k, _v in _m.items():
        assert abs(sum(d for _, d in _v) - (16 if _k == 'intro' else 32)) < 1e-9, (_k, sum(d for _, d in _v))
LIGHT_CH = {'intro': [0, 0, 3, 4], 'A': [0, 5, 3, 4, 0, 5, 1, 4], 'A2': [0, 5, 3, 4, 3, 1, 4, 0],
            'B': [1, 4, 0, 5, 3, 4, 2, 99]}
DUSK_CH = {'intro': [0, 0, 5, 4], 'A': [0, 5, 3, 4, 0, 5, 3, 4], 'A2': [0, 5, 3, 4, 5, 3, 4, 0],
           'B': [3, 4, 2, 5, 1, 4, 0, 99]}
CAVE_CH = {'intro': [0, 0, 3, 4], 'A': [0, 5, 3, 4, 0, 5, 3, 4], 'A2': [0, 5, 3, 4, 0, 5, 3, 4],
           'B': [5, 3, 0, 4, 5, 3, 4, 0]}

VARIANTS = {
    'lighttide': dict(root=62, mode=MAJOR, bpm=117, whim=True, form=(0, 1, 2, 3, 2), bkey=(5, MAJOR),
                      lead=('piano', 'box+kal/steel+box', 'steel+box/box+kal', 'piano/steel+box', 'x'),
                      verb=0.26, rt=1.8, swing=0.09, perc=1.0, pad=0.5, jungle=True, lift=0, mel=LIGHT, ch=LIGHT_CH),
    'dusktide': dict(root=57, mode=MINOR, bpm=84, form=(0, 1, 3, 2), bkey=(3, MAJOR), bounce=.55,
                     lead=('piano', 'piano/flute', 'flute/piano+flute', 'piano/steel+piano', 'x'),
                     verb=0.42, rt=3.2, swing=0.07, perc=0.5, pad=0.9, mel=DUSK, ch=DUSK_CH),
    'cave': dict(root=57, mode=MINOR, bpm=72, form=(0, 1, 3), breg=-12,
                 lead=('piano', 'kalimba/ocarina', 'x', 'piano/ocarina', 'x'),
                 verb=0.6, rt=5.0, swing=0.0, perc=0.2, pad=0.6, cave=True, mel=CAVE, ch=CAVE_CH),
}


# ---- v6 companion songs (same "tide call" family: repeated note, step up, fall back)
REEF = dict(   # Brightreef: F major, playful
    intro=[(_R, 4), (4, 1), (5, 1), (7, 2), (6, 1), (5, .5), (4, .5), (2, 1), (4, 1),
           (1, .5), (2, .5), (3, .5), (6, .5), (4, 2)],
    A=[(4, .5), (4, .5), (5, .5), (4, .5), (2, 1), (0, 1),
       (1, .5), (2, .5), (4, 1), (6, 1), (4, 1),
       *_K1(7),
       (4, 1), (6, .5), (8, .5), (7, 1), (6, 1),
       (5, .5), (4, .5), (2, .5), (4, .5), (7, 2),
       (6, 1), (5, .5), (4, .5), (2, 1), (4, 1),
       *_K2(1),
       (4, 1), (6, 1), (4, 2)],
    B=[(3, 1.5), (4, .5), (5, 1), (3, 1), (2, 1.5), (1, .5), (0, 2),
       (5, 1), (4, .5), (5, .5), (7, 1), (9, 1), (8, 1), (6, 1), (4, 2),
       *_K1(7),
       (6, .5), (7, .5), (8, .5), (9, .5), (8, .5), (7, .5), (6, .5), (4, .5),
       (4, .5), (6, .5), (8, .5), (9, .5), (10, .5), (9, .5), (8, .5), (6, .5),
       (4, .5), (5, .5), (6, .5), (7, .5), (8, 1.25), (_R, .75)])
REEF['A2'] = REEF['A'][:22] + [(5, 1.5), (4, .5), (2, 1), (5, 1), (3, .5), (4, .5), (5, 1), (8, 1), (7, 1),
                               (6, .5), (7, .5), (8, .5), (6, .5), (4, .5), (6, .5), (8, .5), (6, .5), (7, 4)]
WIND = dict(   # Windward: E minor, adventurous
    intro=[(0, .5), (0, .5), (1, .5), (2, .5), (4, 2), (3, 1), (1, .5), (2, .5), (3, 1), (6, 1),
           (5, 1.5), (4, .5), (2, 2), (4, 1), (6, 1), (8, 1.5), (_R, .5)],
    A=[(0, .5), (0, .5), (1, .5), (2, .5), (4, 1.5), (2, .5),
       (3, 1), (1, .5), (2, .5), (3, 1), (6, 1),
       (5, 1.5), (4, .5), (2, 1), (0, 1),
       *_K1(4),
       *_K2(0),
       (1, 1.5), (2, .5), (3, 1), (6, 1),
       (5, 1), (3, .5), (5, .5), (7, 1), (5, 1),
       (4, 1), (6, 1), (8, 2)],
    B=[(4, 2), (2, 1), (0, 1), (5, 1.5), (4, .5), (2, 2), (3, 1), (1, 1), (3, 1), (6, 1), (4, 3), (2, 1),
       *_K1(7), *_K2(2),
       (4, .5), (6, .5), (8, .5), (6, .5), (4, 1), (1, 1),
       (4, 1), (6, 1), (8, 1), (6, 1)])
WIND['A2'] = WIND['A'][:21] + [(2, 1), (4, 1), (6, 1), (9, 1), (7, 1.5), (5, .5), (3, 1), (5, 1),
                               (4, .5), (6, .5), (8, .5), (6, .5), (4, .5), (1, .5), (-1, .5), (1, .5), (0, 4)]
EMBER = dict(  # Emberglow: Eb major, warm and gentle
    intro=[(_R, 4), (2, 1.5), (4, .5), (5, 2), (3, 2), (5, 2), (4, 2), (1, 2)],
    A=[(2, 1.5), (1, .5), (0, 1), (2, 1),
       (1, 1.5), (2, .5), (4, 2),
       (5, 1), (4, .5), (5, .5), (7, 1), (5, 1),
       (3, 3), (2, .5), (3, .5),
       *_K1(4),
       (1, 1.5), (2, .5), (4, 1), (6, 1),
       (5, 1), (3, 1), (1, 1), (3, 1),
       (4, 2), (6, 1), (4, 1)],
    B=[(2, 2), (0, 2), (5, 1.5), (3, .5), (0, 2), (4, 1), (2, 1), (4, 1), (7, 1), (6, 2), (4, 2),
       *_K1(7),
       (6, 1.5), (5, .5), (3, 1), (1, 1),
       (4, 1), (6, 1), (8, 2),
       (4, 1), (6, .5), (5, .5), (4, 1), (1, 1)])
EMBER['A2'] = EMBER['A'][:15] + [(7, 1.5), (6, .5), (5, 1), (2, 1), *_K2(1), (4, 1), (6, 1), (8, 1), (6, 1), (7, 4)]
for _m in (REEF, WIND, EMBER):
    for _k, _v in _m.items():
        assert abs(sum(d for _, d in _v) - (16 if _k == 'intro' else 32)) < 1e-9, (_k, sum(d for _, d in _v))
REEF_CH = {'intro': [0, 3, 0, 4], 'A': [0, 2, 3, 4, 0, 2, 1, 4], 'A2': [0, 2, 3, 4, 5, 1, 4, 0],
           'B': [3, 0, 5, 4, 3, 6, 4, 99]}
WIND_CH = {'intro': [0, 6, 5, 4], 'A': [0, 6, 5, 4, 0, 6, 3, 4], 'A2': [0, 6, 5, 4, 2, 3, 4, 0],
           'B': [0, 5, 6, 2, 3, 5, 4, 99]}
EMBER_CH = {'intro': [0, 5, 3, 4], 'A': [0, 4, 5, 3, 0, 4, 1, 4], 'A2': [0, 4, 5, 3, 5, 1, 4, 0],
            'B': [5, 3, 0, 4, 5, 6, 4, 99]}
VARIANTS.update({
    'brightreef': dict(root=65, mode=MAJOR, bpm=128, whim=True, form=(0, 1, 2, 3, 2), bkey=(9, MINOR),
                       lead=('glock', 'marimba+glock/steel', 'steel+marimba/marimba+glock', 'piano/marimba', 'x'),
                       verb=0.24, rt=1.6, swing=0.08, perc=1.0, pad=0.4, jungle=True, mel=REEF, ch=REEF_CH),
    'windward': dict(root=64, mode=MINOR, bpm=108, form=(0, 1, 3, 2), bkey=(7, MINOR),
                     lead=('steel+flute', 'steel/flute', 'steel+flute/steel', 'piano/flute', 'x'), bigintro=True,
                     verb=0.32, rt=2.4, swing=0.1, perc=.9, pad=0.6, jungle=True, mel=WIND, ch=WIND_CH),
    'emberglow': dict(root=63, mode=MAJOR, bpm=90, form=(0, 1, 3, 2), bkey=(-3, MINOR), bounce=.5,
                      lead=('piano', 'ocarina/piano', 'piano+ocarina/ocarina', 'piano/steel+piano', 'x'),
                      verb=0.38, rt=2.6, swing=0.06, perc=0.45, pad=1.0, mel=EMBER, ch=EMBER_CH),
})

# ---- v9 companion songs: new keys and moods, same family (K cells are public-domain Korobeiniki hints)
FIRST = dict(   # Firstlight: C major, gentle lesson-island air
    intro=[(_R, 6), (0, 1), (2, 1), (4, 2), (5, 1), (4, .5), (2, .5), (0, 2), (4, 2)],
    A=[(0, 1), (2, .5), (4, .5), (5, 1), (4, 1),
       (2, 1), (0, 1), (2, 2),
       *_K1(7),
       (4, 1), (2, .5), (0, .5), (2, 1), (4, 1),
       *_K2(0),
       (5, 1), (4, .5), (5, .5), (7, 1), (5, 1),
       (4, 2), (2, 1), (0, 1)],
    B=[(5, 2), (4, 1), (2, 1), (0, 2), (4, 2),
       *_K1(5),
       (4, 1), (6, 1), (7, 2),
       (5, 1), (4, 1), (2, 1), (0, 1),
       (2, 2), (4, 2)])
FIRST['A2'] = FIRST['A'][:16] + [(5, 1.5), (4, .5), (2, 1), (5, 1), *_K2(4), (5, 1), (7, 1), (4, 2), (0, 2)]
UNDER = dict(   # Undertide: F# minor, slow and wet
    intro=[(_R, 4), (0, 2), (2, 2), (3, 2), (2, 1), (0, 1), (-2, 2), (0, 2)],
    A=[(0, 2), (3, 1), (2, 1),
       (0, 1.5), (-2, .5), (0, 2),
       *_K1(5),
       (3, 2), (2, 1), (0, 1),
       (2, 1.5), (3, .5), (5, 2),
       (3, 1), (2, 1), (0, 2),
       *_K2(0),
       (0, 2)],
    B=[(3, 2), (5, 2), (7, 2), (5, 2),
       *_K1(3),
       (2, 2), (0, 2),
       (3, 1), (5, 1), (3, 1), (2, 1),
       (0, 4)])
UNDER['A2'] = UNDER['A'][:14] + [(5, 2), (3, 1), (2, 1), (0, 2), (-2, 2), (0, 4), (3, 2), (0, 2)]
RAIN = dict(    # Rainwake: G minor, soft weather
    intro=[(_R, 2), (4, 1.5), (3, .5), (2, 2), (0, 2), (2, 1), (3, 1), (4, 2), (2, 2), (0, 2)],
    A=[(4, 1.5), (3, .5), (2, 1), (0, 1),
       (2, 1.5), (3, .5), (4, 2),
       *_K1(5),
       (4, 1), (2, 1), (0, 1), (2, 1),
       (3, 2), (2, 1), (0, 1),
       *_K2(2),
       (4, 1), (3, 1), (2, 1), (0, 1)],
    B=[(5, 2), (3, 2), (4, 2), (2, 2),
       *_K1(7),
       (5, 1), (4, 1), (2, 2),
       (0, 2), (2, 2)])
RAIN['A2'] = RAIN['A'][:16] + [(5, 1.5), (4, .5), (2, 1), (0, 1), (2, 2), (4, 2), (5, 2), (4, 2)]
HIGH = dict(    # Highmere: A major, open and bright day
    intro=[(_R, 4), (4, 1), (5, 1), (7, 2), (6, 1), (4, 1), (2, 2), (4, 2), (0, 2)],
    A=[(4, .5), (5, .5), (7, 1), (7, .5), (9, .5), (7, 1),
       (5, 1), (4, 1), (2, 2),
       *_K1(7),
       (4, 1), (6, 1), (7, 2),
       *_K2(4),
       (5, 1), (4, .5), (2, .5), (0, 1), (2, 1),
       (4, 2), (7, 1), (4, 1)],
    B=[(9, 2), (7, 1), (5, 1), (4, 2), (2, 2),
       *_K1(5),
       (4, 1), (6, 1), (7, 2),
       (5, 2), (4, 2)])
HIGH['A2'] = HIGH['A'][:16] + [(5, 1), (7, 1), (9, 1), (7, 1), *_K2(4), (5, 1), (7, 1), (4, 2), (0, 2)]
for _m in (FIRST, UNDER, RAIN, HIGH):
    for _k, _v in _m.items():
        tgt = 16 if _k == 'intro' else 32
        gap = tgt - sum(d for _, d in _v)
        if gap > 1e-9:
            _v.append((_R, gap))
        assert abs(sum(d for _, d in _v) - tgt) < 1e-9, (_k, sum(d for _, d in _v))
FIRST_CH = {'intro': [0, 5, 3, 4], 'A': [0, 4, 5, 3, 0, 4, 1, 4], 'A2': [0, 4, 5, 3, 5, 1, 4, 0],
            'B': [5, 3, 0, 4, 5, 1, 4, 99]}
UNDER_CH = {'intro': [0, 6, 5, 4], 'A': [0, 6, 5, 3, 0, 6, 4, 0], 'A2': [0, 6, 5, 3, 2, 4, 6, 0],
            'B': [3, 0, 5, 4, 6, 5, 4, 99]}
RAIN_CH = {'intro': [0, 6, 5, 4], 'A': [0, 6, 3, 4, 0, 5, 6, 4], 'A2': [0, 6, 3, 4, 5, 1, 4, 0],
           'B': [5, 3, 0, 4, 6, 5, 4, 99]}
HIGH_CH = {'intro': [0, 4, 5, 0], 'A': [0, 4, 5, 3, 0, 4, 1, 4], 'A2': [0, 4, 5, 3, 5, 1, 4, 0],
           'B': [4, 0, 5, 3, 4, 1, 4, 99]}
VARIANTS.update({
    'firstlight': dict(root=60, mode=MAJOR, bpm=92, form=(0, 1, 3, 2), bkey=(5, MAJOR), bounce=.5,
                       lead=('piano', 'ocarina/piano', 'piano+ocarina/ocarina', 'piano/steel+piano', 'x'),
                       verb=0.34, rt=2.8, swing=0.05, perc=0.35, pad=0.9, mel=FIRST, ch=FIRST_CH),
    'undertide': dict(root=54, mode=MINOR, bpm=66, form=(0, 1, 3, 2), bkey=(3, MAJOR), bounce=.4,
                      lead=('flute', 'ocarina/flute', 'flute+ocarina/ocarina', 'piano/flute', 'x'),
                      verb=0.62, rt=5.5, swing=0.0, perc=0.15, pad=1.2, mel=UNDER, ch=UNDER_CH),
    'rainwake': dict(root=55, mode=MINOR, bpm=78, form=(0, 1, 3, 2), bkey=(4, MAJOR), bounce=.55,
                     lead=('piano', 'kalimba/piano', 'piano+kalimba/kalimba', 'ocarina/piano', 'x'),
                     verb=0.48, rt=3.8, swing=0.04, perc=0.3, pad=1.0, mel=RAIN, ch=RAIN_CH),
    'highmere': dict(root=69, mode=MAJOR, bpm=114, whim=True, form=(0, 1, 2, 3, 2), bkey=(7, MINOR),
                     lead=('steel+box', 'glock/steel', 'steel+glock/marimba', 'piano/steel', 'x'),
                     verb=0.25, rt=1.7, swing=0.08, perc=0.9, pad=0.45, jungle=True, lift=0, mel=HIGH, ch=HIGH_CH),
})



def _hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def _pitch(deg, root, mode):
    o, d = divmod(deg, 7)
    return root + 12 * o + mode[d]


def _env(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(t / max(a, 1e-4), 1.0) * np.exp(-t / d)


# ---- instruments: each returns a mono float array
def box(f, dur, v, rng):
    """Music box / celesta: inharmonic tine partials, quick bright decay."""
    n = int((dur + 3.0) * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for ratio, amp, dec in ((1, 1, 1.3), (2.0, .16, .55), (3.01, .05, .22), (5.43, .035, .07)):
        if f * ratio < 9000:
            out += amp * np.sin(2 * np.pi * f * ratio * t + rng.random() * 6) * np.exp(-t / dec)
    return out * np.minimum(t / .005, 1) * v * .5


def kalimba(f, dur, v, rng):
    """Kalimba tine: warm fundamental, woody overtone, thumb click."""
    n = int((dur + 1.6) * SR)
    t = np.arange(n) / SR
    out = np.sin(2 * np.pi * f * t) * np.exp(-t / .9)
    out += .35 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t / .25)
    out += .2 * np.sin(2 * np.pi * f * 5.9 * t) * np.exp(-t / .04)
    click = rng.standard_normal(n) * np.exp(-t / .003) * .15
    return (out + click) * np.minimum(t / .003, 1) * v * .55


def _lp(x, fc):
    """Brick-ish lowpass via FFT (fine for short buffers)."""
    X = np.fft.rfft(x)
    fr = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / (1 + (fr / fc) ** 4), len(x))


def _bp(x, lo, hi):
    X = np.fft.rfft(x)
    fr = np.fft.rfftfreq(len(x), 1 / SR) + 1
    return np.fft.irfft(X / (1 + (fr / hi) ** 4) / (1 + (lo / fr) ** 4), len(x))


def flute(f, dur, v, rng, breath=.10, harm=(.22, .06)):
    """Soft flute / ocarina: sines + breath noise, slow attack, delayed vibrato."""
    n = int((dur + .5) * SR)
    t = np.arange(n) / SR
    vib = 1 + .005 * np.sin(2 * np.pi * 5.0 * t) * np.clip((t - .25) / .4, 0, 1)
    ph = 2 * np.pi * np.cumsum(f * vib) / SR
    tone = np.sin(ph) + harm[0] * np.sin(2 * ph) + harm[1] * np.sin(3 * ph)
    noise = _bp(rng.standard_normal(n), f * .8, f * 3) * breath * 3
    a = np.clip(t / .07, 0, 1) ** 1.5
    rel = np.clip((dur + .25 - t) / .25, 0, 1)
    chiff = np.exp(-t / .03) * .6
    return (tone * a + noise * (a * .6 + chiff)) * rel * v * .42


def ocarina(f, dur, v, rng):
    return flute(f, dur, v, rng, breath=.05, harm=(.06, .02))


def bass(f, dur, v, rng):
    """Warm round pluck-bass."""
    n = int((dur + .6) * SR)
    t = np.arange(n) / SR
    out = np.sin(2 * np.pi * f * t) + .3 * np.sin(4 * np.pi * f * t) * np.exp(-t / .3) + .08 * np.sin(6 * np.pi * f * t) * np.exp(-t / .1)
    rel = np.clip((dur + .1 - t) / .3, 0, 1)
    return out * np.minimum(t / .006, 1) * np.exp(-t / 1.6) * rel * v * .6


def pad(f, dur, v, rng):
    n = int((dur + 1.5) * SR)
    t = np.arange(n) / SR
    out = sum(np.sin(2 * np.pi * f * d * t + rng.random() * 6) for d in (1, 1.003, .997, 2.001))
    a = np.clip(t / .9, 0, 1) * np.clip((dur + 1.2 - t) / 1.2, 0, 1)
    return out * a * v * .08


_BANK = {}


def _banked(fn):
    """Reuse 6 pre-rendered hits per noise instrument (FFT filtering is the slow part)."""
    def w(v, rng):
        k = (fn.__name__, int(rng.integers(6)))
        if k not in _BANK:
            _BANK[k] = fn(1.0, np.random.default_rng(k[1] + 99))
        return _BANK[k] * v
    w.__name__ = fn.__name__
    return w


@_banked
def shaker(v, rng):
    n = int(.09 * SR)
    t = np.arange(n) / SR
    return _bp(rng.standard_normal(n), 5000, 11000) * np.minimum(t / .008, 1) * np.exp(-t / .025) * v * .2


def woodblock(v, rng):
    n = int(.12 * SR)
    t = np.arange(n) / SR
    out = np.sin(2 * np.pi * 880 * t) * np.exp(-t / .03) + .5 * np.sin(2 * np.pi * 1390 * t) * np.exp(-t / .015)
    return out * v * .18


def thump(v, rng):
    n = int(.3 * SR)
    t = np.arange(n) / SR
    f = 55 + 50 * np.exp(-t / .02)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .12) * np.minimum(t / .004, 1) * v * .45


@_banked
def clap(v, rng):
    n = int(.16 * SR)
    t = np.arange(n) / SR
    env = sum(np.exp(-np.clip(t - o, 0, None) / .006) * (t >= o) for o in (0, .009, .018)) / 3
    env += np.exp(-t / .05) * .5
    return _bp(rng.standard_normal(n), 900, 3500) * env * v * .22


@_banked
def splash(v, rng):
    n = int(1.2 * SR)
    t = np.arange(n) / SR
    return _bp(rng.standard_normal(n), 3000, 12000) * np.exp(-t / .35) * np.minimum(t / .003, 1) * v * .16


def swell(beats, beat, v, rng):
    """Soft rising filtered-noise build-up into the next section."""
    n = int(beats * beat * SR)
    t = np.linspace(0, 1, n)
    x = _bp(rng.standard_normal(n), 2500, 9000) * t ** 2.5
    return x * v * .12


def drip(f, rng):
    n = int(.25 * SR)
    t = np.arange(n) / SR
    fs = f * (1 + 1.5 * np.exp(-t / .02))
    return np.sin(2 * np.pi * np.cumsum(fs) / SR) * np.exp(-t / .05) * .12


def piano(f, dur, v, rng):
    """Soft felt piano: slightly inharmonic decaying partials, felt-damped highs, damper release."""
    n = int((dur + 2.5) * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k in range(1, 7):
        fk = f * k * np.sqrt(1 + .0004 * k * k)
        if fk > 8000:
            break
        amp = k ** -1.3 / (1 + (fk / 2200) ** 2)
        out += amp * np.sin(2 * np.pi * fk * t + rng.random() * 6) * np.exp(-t / (2.6 / k ** .7))
    rel = np.where(t < dur + .15, 1.0, np.exp(-(t - dur - .15) / .35))
    return out * np.minimum(t / .006, 1) * rel * v * .5


def marimba(f, dur, v, rng):
    n = int((dur + 1.0) * SR)
    t = np.arange(n) / SR
    out = np.sin(2 * np.pi * f * t) * np.exp(-t / .38) + .25 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t / .07)
    out += .08 * np.sin(2 * np.pi * 9.9 * f * t) * np.exp(-t / .02)
    return out * np.minimum(t / .0015, 1) * v * .5


def steel(f, dur, v, rng):
    """Steel-drum-ish: FM ping with a bright, quickly mellowing tone."""
    n = int((dur + 1.4) * SR)
    t = np.arange(n) / SR
    idx = 1.1 * np.exp(-t / .12)
    out = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t / .7)
    out += .2 * np.sin(2 * np.pi * 3.0 * f * t) * np.exp(-t / .15)
    return out * np.minimum(t / .003, 1) * v * .42


def drum(f0, dec, v, rng, bend=.45):
    """Hand drum (bongo/conga): pitched membrane with a pitch drop and a slap."""
    n = int((dec * 6) * SR)
    t = np.arange(n) / SR
    f = f0 * (1 + bend * np.exp(-t / .012))
    out = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / dec)
    out += rng.standard_normal(n) * np.exp(-t / .002) * .12
    return out * np.minimum(t / .001, 1) * v * .3


def bird(rng):
    """Little jungle bird: 2-4 quick frequency-swept chirps."""
    k = int(rng.integers(2, 5))
    base = rng.uniform(2400, 4200)
    n = int((.09 * k + .1) * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for j in range(k):
        tt = t - j * .09
        m = (tt >= 0) & (tt < .06)
        fr = base * (1 + .35 * np.sin(np.pi * tt[m] / .06)) * (1 + .1 * j)
        ph = 2 * np.pi * np.cumsum(fr) / SR
        out[m] += np.sin(ph) * np.sin(np.pi * tt[m] / .06) ** 2
    return out * .05


def pizz(f, dur, v, rng):
    """Pizzicato string: bright harmonic pluck, very short."""
    n = int((dur + .5) * SR)
    t = np.arange(n) / SR
    out = sum(np.sin(2 * np.pi * f * k * t) * np.exp(-t / (.22 / k ** .6)) / k for k in range(1, 7) if f * k < 9000)
    return out * np.minimum(t / .002, 1) * v * .45


def glock(f, dur, v, rng):
    """Glockenspiel sparkle: bright bar partials, ringing fundamental."""
    n = int(1.6 * SR)
    t = np.arange(n) / SR
    out = np.sin(2 * np.pi * f * t) * np.exp(-t / .6) + .3 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / .12)
    out += .1 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t / .04)
    return out * np.minimum(t / .001, 1) * v * .3


INSTR = {'pizz': pizz, 'glock': glock, 'piano': piano, 'marimba': marimba, 'steel': steel, 'box': box, 'kalimba': kalimba, 'flute': flute, 'ocarina': ocarina}


# ---- mixing helpers
class _Track:
    def __init__(self, n):
        self.n = n
        self.buf = np.zeros((n, 2), dtype=np.float32)

    def add(self, x, t0, pan=0.0, haas=0.0):
        """Add mono x at sample t0 (wrapping around the loop), equal-power pan."""
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        d = int(haas * SR)
        x = np.array(x, dtype=np.float64)
        f = min(len(x), int(.03 * SR))
        x[-f:] *= np.linspace(1, 0, f)                   # never truncate a tail abruptly
        for ch, g, off in ((0, l, 0), (1, r, d)):
            s, i = (t0 + off) % self.n, 0
            while i < len(x):
                k = min(len(x) - i, self.n - s)
                self.buf[s:s + k, ch] += x[i:i + k] * g
                i, s = i + k, 0


def _reverb(n, rt, seed):
    """Circular FFT convolution with a decaying stereo noise tail -> seamless loop."""
    rng = np.random.default_rng(seed)
    L = int(rt * 1.3 * SR)
    t = np.arange(L) / SR
    ir = rng.standard_normal((L, 2)) * np.exp(-6.9 * t / rt)[:, None]
    ir[: int(.012 * SR)] = 0                            # pre-delay
    for c in range(2):
        ir[:, c] = _lp(ir[:, c], 6000)
    ir /= np.sqrt((ir ** 2).sum(0))
    N = 1 << int(np.ceil(np.log2(n + L)))               # fast FFT size; tail folded back later
    H = np.zeros((N, 2))
    H[:L] = ir
    return np.fft.rfft(H, axis=0)


def _conv_loop(x, H):
    """Circular (loop-seamless) convolution of x (n,2) with reverb spectrum H."""
    n = len(x)
    N = 2 * (H.shape[0] - 1)
    y = np.fft.irfft(np.fft.rfft(x, N, axis=0) * H, N, axis=0)
    out = y[:n].copy()
    for s in range(n, N, n):                             # wrap the tail onto the loop start
        seg = y[s:s + n]
        out[:len(seg)] += seg
    return out


def _voice(pitches, lo):
    """Close voicing: put every chord tone in [lo, lo+12) so chords sit just under the tune."""
    return sorted(lo + (p - lo) % 12 for p in pitches)


def render(variant='lighttide', seed=7):
    V = VARIANTS[variant]
    rng = np.random.default_rng(seed)
    mode, bpm, sw = V['mode'], V['bpm'], V['swing']
    beat = 60.0 / bpm
    order = list(V.get('form', range(len(FORM))))
    form = [(FORM[i][0], V['mel'][FORM[i][0]]) for i in order]
    _CH = V['ch']
    leads = [V['lead'][i] for i in order]
    bars = sum(len(_CH[name]) for name, _ in form)
    n = int(round(bars * 4 * beat * SR))
    S = {k: _Track(n) for k in ('hand', 'lead', 'keys', 'piano', 'bass', 'perc', 'pad', 'cave', 'amb')}
    jungle = V.get('jungle', False)

    def at(b):
        """One shared swing grid for every part: the off-8th is pushed late by `sw` beats and
        16ths in between are warped proportionally, so melody, bass and drums always agree."""
        whole, fr = divmod(b, 1.0)
        fr = fr * (.5 + sw) / .5 if fr < .5 else .5 + sw + (fr - .5) * (.5 - sw) / .5
        return int(round((whole + fr) * beat * SR))

    b0 = 0.0
    for si, (name, mel) in enumerate(form):
        lead = leads[si]
        last = si == len(form) - 1
        big = name in ('A', 'A2') or (name == 'intro' and V.get('bigintro'))
        home, hmode = V['root'] + (V.get('lift', 0) if last else 0), V['mode']
        if name == 'B' and V.get('bkey'):
            root, mode = home + V['bkey'][0], V['bkey'][1]          # contrasting key area
        else:
            root, mode = home, hmode
        if name == 'B' and V.get('breg'):
            root += V['breg']                                       # contrasting register
        nb = len(_CH[name])
        nxt = form[(si + 1) % len(form)][0]
        nroot = V['root'] + (V.get('lift', 0) if si + 1 == len(form) - 1 else 0)
        nmode = V['mode']
        if nxt == 'B' and V.get('bkey'):
            nroot, nmode = nroot + V['bkey'][0], V['bkey'][1]
        # --- melody: hook "call"; marimba / kalimba "response" on held notes
        b, hist, onsets = b0, [], []
        for deg, d in mel:
            if deg is not None:
                onsets.append(b)
                cdb = _CH[name][min(int((b - b0) // 4), nb - 1)]
                kroot, kmode = (home, hmode) if cdb == 99 else (root, mode)
                dom = (cdb == 99 or cdb % 7 == 4) and kmode is MINOR
                m = _pitch(deg, kroot + 12, kmode) + (1 if dom and deg % 7 == 6 else 0)
                parts = lead.split('/')
                ld = parts[int((b - b0) // 16) % len(parts)]                # hand the line between instruments
                acc = 1.0 if b % 2 == 0 else .85
                whim = V.get('whim') and name != 'intro'
                play = d * .7 if whim and d <= .5 else d            # bouncy staccato
                if whim and d >= .5 and (b % 1 == 0) and rng.random() < .2:   # grace-note skip into the note
                    gm = _pitch(deg + 1 if rng.random() < .5 else deg - 1, kroot + 12, kmode)
                    S['lead'].add(box(_hz(gm + 12), .12 * beat, .3, rng), max(0, at(b) - int(.055 * SR)), pan=.25)
                if whim and d >= 2:                                    # glock sparkle answering the held note
                    for j, e in enumerate((deg + 4, deg + 2, deg + 7)):
                        S['keys'].add(glock(_hz(_pitch(e, kroot + 24, kmode)), .25 * beat, .5 - .08 * j, rng),
                                      at(b + d - 1 + j * .25), pan=.5 - .3 * j)
                for j, inst in enumerate(ld.split('+')):
                    fn = INSTR['kalimba' if inst == 'kal' else inst]
                    mm = m - 12 if (inst in ('kal', 'piano') and '+' in ld) or (inst == 'piano' and name == 'intro') else m
                    vv = .8 * acc * (1 if j == 0 else .5)
                    S['lead'].add(fn(_hz(mm), (play if '+' in ld or j == 0 else d) * beat, vv, rng), at(b), pan=(.12, -.22, .3)[j])
                if name in ('A2', 'B') or last:
                    if d >= 1:                           # doubled third below on sustained notes
                        th = _pitch(deg - 2, kroot + 12, kmode)
                        fn = flute if not jungle else box
                        S['keys'].add(fn(_hz(th), d * beat, .32, rng), at(b), pan=-.35)
                if V.get('cave'):
                    S['cave'].add(drip(_hz(m + 12), rng) * .5, at(b + .75), pan=rng.uniform(-.7, .7))
                hist.append(deg)
                if d >= 2 and len(hist) >= 3 and name != 'intro':
                    resp = marimba if (jungle or V.get('bounce')) else kalimba
                    for j, e in enumerate(hist[-4:-1]):
                        S['keys'].add(resp(_hz(_pitch(e, kroot, kmode)), beat * .5, .42, rng), at(b + .5 + j * .5), pan=.45)
            b += d
        # --- harmony per bar
        for k, cdeg in enumerate(_CH[name]):
            bb = b0 + 4 * k
            fill = k == nb - 1
            def cinfo(cd, rt, md):
                if cd == 99:
                    cd, rt, md = 4, home, hmode
                ps = [_pitch(cd + i, rt, md) for i in (0, 2, 4, 6)]
                if cd % 7 == 4 and md is MINOR:
                    ps[1] += 1                                      # harmonic-minor dominant
                return ps
            ps = cinfo(cdeg, root - (V.get('breg') or 0) if name == 'B' else root, mode)
            tri = _voice(ps[:3], home + 2)
            sev = _voice(ps, home + 2)
            r = (ps[0] - home) % 12 + home - 24
            fifth = r + (ps[2] - ps[0])
            ncd = _CH[name][k + 1] if k + 1 < nb else _CH[nxt][0]
            nps = cinfo(ncd, root, mode) if k + 1 < nb else cinfo(ncd, nroot, nmode)
            nr = (nps[0] - home) % 12 + home - 24
            appr = nr - 1 if (nr - r) % 12 else r + 7
            build = jungle and name == 'B' and k >= 4      # second half of the break builds back up
            calm = (name in ('intro', 'B') and not build and not big) or V.get('cave')
            ramp = (k - 3) / 4 if build else 1.0
            # felt piano: open fifth + rolled maj7/min7 voicing (Minecraft-style calm)
            if calm or not jungle:
                S['piano'].add(piano(_hz(r + 12), 3.8 * beat, .5, rng) + piano(_hz(fifth + 12), 3.8 * beat, .4, rng), at(bb), pan=-.2)
                for i, p_ in enumerate(sev):
                    S['piano'].add(piano(_hz(p_), (3.6 - .25 * i) * beat, .3, rng), at(bb + .25 * i) + 0, pan=-.1 + .12 * i)
                if not calm:                             # Dusktide: flowing piano 8ths in the A sections
                    for i, s in enumerate((0, 1, 2, 3, 2, 1)):
                        S['piano'].add(piano(_hz(sev[s] + 12), beat * .6, .14, rng), at(bb + 1 + i * .5), pan=.25)
            else:
                S['piano'].add(sum(piano(_hz(p_), 1.5 * beat, .2, rng) for p_ in sev), at(bb), pan=-.15)
            # bass
            # developed bass: chord tones, passing tones and octave jumps on the shared grid;
            # answers the melody in its gaps, fills at phrase ends, walks into chord changes.
            third, fif, octv = r + (ps[1] - ps[0]), r + (ps[2] - ps[0]), r + 12
            hits = [o - bb for o in onsets if bb <= o < bb + 4]
            gap2 = not any(2 <= h < 4 for h in hits)                 # melody holds -> bass answers
            moving = (nr - r) % 12 != 0
            appr = nr - 1 if nr > r else nr + 1
            walk = (third if abs(nr - third) < abs(nr - fif) else fif) if moving else fif
            if calm:
                steps = [(0, r, 1.9, .7), (2, fif, 1.4, .5)]
                if fill or moving:
                    steps.append((3.5, appr if moving else octv, .45, .45))
            else:
                v4 = k % 4
                if v4 == 0:
                    steps = [(0, r, .9, 1), (1, fif, .9, .7), (2, octv, .45, .8), (2.5, fif, .45, .6)]
                elif v4 == 1:
                    steps = [(0, r, 1.4, 1), (1.5, r, .45, .55), (2, third, .9, .75)]
                elif v4 == 2:
                    steps = [(0, r, .9, 1), (1, third, .45, .65), (1.5, fif, .45, .6), (2, octv, .9, .8)]
                else:
                    steps = [(0, r, .9, 1), (1, fif, .9, .7), (2, octv, .45, .75), (2.5, fif, .45, .6)]
                if gap2 and not fill:                                 # answer the held melody note
                    steps = steps[:1] + [(1, fif, .9, .7), (2, third, .45, .7), (2.5, fif, .45, .65)]
                if fill:                                              # phrase-end fill
                    steps = [(0, r, .9, 1), (1, fif, .45, .7), (1.5, octv, .45, .7),
                             (2, fif, .45, .7), (2.5, third, .45, .65)]
                steps += [(3, walk, .45, .7), (3.5, appr if moving else r, .45, .65)]
            for bt, nt, dd, vv in steps:
                if build and fill and bt >= 3.25:
                    continue
                x = bass(_hz(nt), dd * beat, vv * ramp ** .5 * V.get('bounce', 1), rng)
                pl = int(.03 * SR)
                x[:pl] += np.sin(2 * np.pi * _hz(nt) * 3 * np.arange(pl) / SR) * np.exp(-np.arange(pl) / SR / .008) * .2 * vv
                S['bass'].add(x, at(bb + bt))
            if V['pad']:
                S['pad'].add(sum(pad(_hz(p_), 4 * beat, 1, rng) for p_ in tri), at(bb), pan=-.25, haas=.012)
            # DK-style jungle: kalimba ostinato + call-and-response marimba stabs + hand drums
            if jungle and (big or build):
                for i, s in enumerate((0, 1, 2, 0, 1, 2, 0, 2)):
                    if V.get('whim'):
                        hop = 12 if i in (2, 5) else 0               # playful octave skips
                        S['keys'].add(pizz(_hz(tri[s] - 12 + hop), beat * .25, .42 if i in (0, 3, 6) else .26, rng),
                                      at(bb + i / 2), pan=-.35 if i % 2 else .3)
                    else:
                        S['keys'].add(kalimba(_hz(tri[s] - 12), beat * .5, .4 if i in (0, 3, 6) else .24, rng),
                                      at(bb + i / 2), pan=-.35 if i % 2 else .3)
                if V.get('whim') and k % 4 == 1 and k < nb - 1:       # cheeky music-box run down at bar end
                    for j in range(4):
                        S['keys'].add(box(_hz(_pitch((4 if cdeg == 99 else cdeg) + 7 - j, root + 12, mode)), .25 * beat, .28, rng),
                                      at(bb + 3 + j / 4), pan=.45 - .2 * j)
                if k % 2 == 1:
                    for st in (2.5, 3.5):
                        S['keys'].add(sum(marimba(_hz(p_), beat * .4, .3, rng) for p_ in tri), at(bb + st), pan=.4)
            pv = V['perc']
            if pv and (big or build or (jungle and name == 'B')):
                soft = name == 'B' and not build
                for e in range(16 if jungle else 8):
                    q = e / (4 if jungle else 2)
                    v = (.9 if e % 4 == 2 else .45 if e % 2 else .3) if jungle else (1 if e % 2 else .55)
                    if fill and q >= 2:
                        v = .7 + .05 * e if jungle else v
                    if build and fill and q >= 3.25:
                        continue
                    S['perc'].add(shaker(v * pv * (.5 if soft else .8) * ramp, rng), at(bb + q), pan=.4)
                hi, lo, cg = (390, .06), (280, .08), (175, .14)
                # simple hand-drum groove: conga on 1 and 3, bongo backbeat on 2 and 4, light 8th lifts
                patt = [(0, cg, .8), (1, lo, .65), (2, cg, .7), (3, lo, .65), (1.5, hi, .3), (3.5, hi, .35)]
                if soft:
                    patt = [(0, cg, .6), (2, cg, .45)]
                if build:                                # rising drum build, 8ths then 16ths
                    step = .5 if k < 6 else .25
                    patt = [(q * step, (lo, hi)[int(q) % 2], .3 + .6 * ramp * (q * step) / 4)
                            for q in range(int(4 / step)) if not (fill and q * step >= 3.25)]
                if fill and not soft and not build:
                    patt += [(3 + j / 4, (hi, lo)[j % 2], .45 + .1 * j) for j in range(4)]
                for bt, (f0, dc), vv in patt:
                    S['hand'].add(drum(f0, dc, vv * pv, rng), at(bb + bt), pan=.3 if f0 > 300 else -.25 if f0 > 200 else -.05)
                if jungle and not soft:
                    kicks = (0, 2) if not fill else (0, 1, 2, 3)
                    if build:
                        kicks = (0, 2) if k < 7 else (0, .5, 1, 1.5, 2, 2.5, 3)
                    for kb in kicks:
                        S['perc'].add(thump(.95 * pv * ramp, rng), at(bb + kb))
                    for cb in (1, 3):
                        if not (build and fill and cb == 3):
                            S['perc'].add(clap(.7 * pv * ramp, rng), at(bb + cb), pan=.1)
                    if fill and nxt != 'intro':
                        S['perc'].add(swell(4 if not build else 3.25, beat, pv * 1.4, rng), at(bb), haas=.01)
                if jungle and k == 0 and big:            # the drop: everything lands together
                    S['perc'].add(splash(pv, rng), at(bb), haas=.008)
                    S['keys'].add(sum(marimba(_hz(p_), beat, .45, rng) for p_ in tri), at(bb), pan=.2)
            if fill:                                     # pickup run into the next section
                for j in range(4):
                    if jungle:
                        S['keys'].add(glock(_hz(_pitch(3 + j, nroot + 12, nmode)), beat * .25, .4 + .05 * j, rng),
                                      at(bb + 3 + j / 4), pan=-.3)
                    S['keys'].add(marimba(_hz(_pitch(-4 + j, nroot, nmode)), beat * .25, .3, rng)
                                  if jungle else kalimba(_hz(_pitch(-3 + j, nroot, nmode)), beat * .25, .28 + .04 * j, rng),
                                  at(bb + 3 + j / 4), pan=.2)
            # ambience: jungle birds by day, sparse at dusk
            if not V.get('cave') and rng.random() < (.55 if jungle else .2):
                S['amb'].add(bird(rng), at(bb + rng.integers(0, 8) / 2), pan=rng.uniform(-.9, .9))
            if V.get('cave'):
                S['cave'].add(pad(_hz(_pitch(0, root - 24, mode)), 4 * beat, 3, rng), at(bb), haas=.02)
                for _ in range(2):
                    S['cave'].add(drip(rng.uniform(900, 2200), rng), at(bb + rng.integers(0, 8) / 2), pan=rng.uniform(-.9, .9))
        b0 += 4 * nb
    H = _reverb(n, V['rt'], seed)
    send = {'hand': .4, 'lead': 1.25, 'keys': 1.0, 'piano': 1.2, 'bass': .25, 'perc': .4, 'pad': 1.4, 'cave': 2, 'amb': 1.5}
    gain = {'lead': .62, 'keys': .8, 'piano': .75, 'bass': 1.05 if jungle else .9, 'perc': 1.75 if jungle else 1.2, 'pad': V['pad'], 'cave': 1, 'amb': 3}
    gain['hand'] = gain['perc'] * .84                 # hand drums ~1.5 dB under the kit
    gain['bass'] *= .85
    # duck hand drums + bass a little under melody notes (circular, loop-safe)
    blk = 512
    lv = np.abs(S['lead'].buf).max(1)
    nbk = -(-n // blk)
    e = np.pad(lv, (0, nbk * blk - n)).reshape(nbk, blk).max(1)
    for _ in range(4):
        e = (np.roll(e, 1) + 2 * e + np.roll(e, -1)) / 4
    e = np.clip(e / (np.percentile(e, 95) + 1e-9), 0, 1)
    duck = np.interp(np.arange(n) / blk, np.arange(nbk) + .5, 1 - .3 * e, period=nbk)[:, None]
    out = {}
    for k, tr in S.items():
        if not tr.buf.any() or gain[k] == 0:
            continue
        dry = tr.buf * gain[k] * (duck if k in ('hand', 'bass') else 1)
        wet = _conv_loop(dry, H)
        out[k] = (dry * (1 - V['verb'] * .5) + wet * V['verb'] * send[k] * 1.6).astype(np.float32)
    return out, SR


def mix(stems, levels=None, target=.89):
    """Sum stems, gentle look-ahead limiter, normalize; returns int16 (N,2)."""
    levels = levels or {}
    x = sum(v * levels.get(k, 1.0) for k, v in stems.items()).astype(np.float64)
    x /= np.abs(x).max() / 1.25 + 1e-9                  # drive slightly into the limiter
    blk = 256
    nb = len(x) // blk + 1
    pad_ = np.pad(np.abs(x).max(1), (0, nb * blk - len(x)))
    pk = pad_.reshape(nb, blk).max(1)
    pk = np.maximum(pk, np.roll(pk, 1))                  # look-ahead 1 block
    pk = np.maximum.reduce([np.roll(pk, s) for s in range(-2, 3)])
    g = np.minimum(1, .8 / np.maximum(pk, 1e-9))
    for _ in range(3):                                   # smooth gain (circular, loop-safe)
        g = np.minimum(g, (np.roll(g, 1) + g + np.roll(g, -1)) / 3)
    gs = np.interp(np.arange(len(x)) / blk, np.arange(nb) + .5, g, period=nb)
    x *= gs[:, None]
    x = np.tanh(x / .95) * .95                           # soft ceiling, no hard clipping
    x *= target / np.abs(x).max()
    return (x * 32767).astype(np.int16)


# ---- in-game cache: each song is rendered once (in a low-priority worker) and saved
MUSIC_VERSION = 'v9'
SONGS = ('windward', 'lighttide', 'dusktide', 'brightreef', 'emberglow', 'cave',
         'firstlight', 'undertide', 'rainwake', 'highmere')


def cache_key():
    """Changes whenever the composition or synthesis settings change -> cache regenerates."""
    import hashlib
    blob = repr((MUSIC_VERSION, SR, sorted((k, sorted(v.items(), key=str)) for k, v in VARIANTS.items()))).encode()
    return hashlib.sha1(blob).hexdigest()[:10]


def render_to(name, path):
    """Render one song, mix it, and save int16 stereo PCM atomically to `path` (.npy)."""
    import os
    st, _ = render(name)
    pcm = mix(st)
    del st
    tmp = path[:-4] + '.part.npy'
    np.save(tmp, pcm)
    os.replace(tmp, path)
    return path


if __name__ == '__main__':
    import subprocess, sys, time
    outdir = sys.argv[1] if len(sys.argv) > 1 else '.'
    for v in (sys.argv[2:] or ('lighttide', 'dusktide', 'cave')):
        t = time.time()
        st, sr = render(v)
        pcm = mix(st)
        el = time.time() - t
        a = pcm.astype(float) / 32767
        seam = np.abs(a[0] - a[-1]).max()
        step = np.abs(np.diff(a, axis=0)).max()
        print(f'{v}: {len(pcm)/sr:.1f}s render {el:.1f}s peak {np.abs(a).max():.3f} '
              f'rms {np.sqrt((a**2).mean()):.3f} seam_jump {seam:.4f} max_step {step:.4f}')
        name = {'cave': 'theme_cave_layer'}.get(v, 'theme_' + v) + '_v8'
        loops = 1 if v != 'cave' else 1
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 's16le', '-ar', str(sr), '-ac', '2',
                        '-i', '-', '-b:a', '192k', f'{outdir}/{name}.mp3'], input=np.tile(pcm, (loops, 1)).tobytes(), check=True)
