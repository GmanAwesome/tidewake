"""Tour scripts (generators). Yield seconds to wait or a predicate to wait for."""
import math
import random

import numpy as np

from .config import LAYER
from .hexgrid import center, cell_at, ring
from .noise import seed_from_text
from . import materials as MT
from .ui import screens as S

M = MT.ID


def title(app, log, shot, look_at, settled, arg):
    yield 2.0
    yield lambda: app.backdrop['world'].busy() == 0
    yield 1.0
    yield shot('title')
    yield 0.5


def play(app, log, shot, look_at, settled, arg):
    seed = seed_from_text(arg or 'honey-moth-7')
    yield 1.0
    app.create_sky('Tour Sky', seed, arg, 'wanderer')
    yield lambda: app.mode == 'game'
    ses = app.session
    yield settled()
    yield 1.5
    yield shot('01_spawn')
    p = ses.player
    sp = ses.nearest_spire[0] if ses.nearest_spire else None
    log('spawn', p.x, p.y, p.z, 'spire', sp)
    app.show_debug = True
    yield 0.5
    yield shot('02_debug')
    app.show_debug = False
    # walk forward for a bit
    app.test_input = {'fwd': 1}
    yield 3.0
    app.test_input = {}
    yield 0.5
    yield shot('03_walked')
    log('after walk', p.x, p.y, p.z, p.on_ground)


def _stand(ses, q, r, look=None, up=0, dist_pitch=None):
    """Put the wanderer on top of column (q, r)."""
    p = ses.player
    top = ses.world.column_top(q, r)
    x, z = center(q, r)
    p.x, p.z = x, z
    p.y = (top + 1 + up) * LAYER + 0.001
    p.vx = p.vy = p.vz = 0
    return top


def full(app, log, shot, look_at, settled, arg):
    seed = seed_from_text(arg or 'honey-moth-7')
    yield 1.0
    yield lambda: app.backdrop['world'].busy() == 0
    yield 0.5
    yield shot('00_title')
    yield 0.3
    app.set_screen(S.NewSkyScreen(S.SkiesScreen(app)))
    yield 0.5
    app.menu.name = 'Honey Moth'
    app.menu.seed = arg or 'honey-moth-7'
    yield 0.3
    yield shot('10_new_sky')
    yield 0.2
    app.create_sky('Honey Moth', seed, arg or 'honey-moth-7', 'wanderer')
    yield 0.2
    yield shot('11_loading')
    yield lambda: app.mode == 'game'
    ses = app.session
    yield settled()
    yield 1.0
    yield shot('20_spawn')
    p = ses.player
    sp = ses.nearest_spire[0]
    log('spire', sp)
    # --- gather a few cells in front of us
    ess0 = list(ses.essence)
    q, r = cell_at(p.x, p.z)
    tq, tr = q + 2, r
    top = ses.world.column_top(tq, tr)
    tx, tz = center(tq, tr)
    look_at(p, tx, (top + 1) * LAYER, tz)
    yield 0.3
    for i in range(3):
        app.test_input = {'gather': True}
        yield 0.35
    log('essence', ess0, '->', ses.essence, 'gathered', ses.stats['gathered'])
    app.test_input = {'gather': True}
    yield 0.15
    yield shot('21_gathered')
    ses.chord = [0, 2]
    yield 0.3
    yield shot('22_tuned_crystal')
    # --- tune and shape: walk to the spire and offer what it wants
    wants = sp['wants']
    log('wants', [MT.NAMES[w] for w in wants])
    ses.essence = [40, 40, 40, 40]
    ring1 = ring(sp['q'], sp['r'], 1)
    # stand 3 cells away from the spire, looking at ring cells
    stand = ring(sp['q'], sp['r'], 3)[0]
    _stand(ses, *stand)
    yield settled()
    T = sp['top']
    inv = {v: k for k, v in MT.FORMS.items()}
    for i, w in enumerate(wants):
        a, b = sorted(ring1, key=lambda c: (c[0] - stand[0]) ** 2 + (c[1] - stand[1]) ** 2 + (c[0] - stand[0]) * (c[1] - stand[1]))[i]
        cx, cz = center(a, b)
        look_at(p, cx, (T + 1) * LAYER - 0.02, cz)
        ses.chord = list(inv[w])
        yield 0.25
        yield shot(f'30_offer_{i}_aim')
        app.test_input = {'shape': True}
        yield 0.5
        log('offered', MT.NAMES[w], 'at', a, b, ses.world.get(a, b, T + 1), 'target was', ses.target, ses.target_prev)
    yield 1.0
    log('awakened', ses.awakened)
    yield shot('31_awakened')
    # step back and admire at dusk
    back = ring(sp['q'], sp['r'], 9)[3]
    _stand(ses, *back, up=4)
    sx, sz = center(sp['q'], sp['r'])
    look_at(p, sx, (T + 6) * LAYER, sz)
    ses.phase = 0.5
    for _ in range(40):
        ses._update_jellies(0.5)
        ses._update_motes(0.5)
    yield settled()
    yield 1.5
    yield shot('32_awake_dusk')
    ses.phase = 0.3
    yield 1.0
    yield shot('33_awake_golden')
    # --- living cells: find open flat ground near the spire
    ses.phase = 0.0
    w = ses.world
    flat = None
    cands = []
    for rr in range(8, 40, 2):
        cands += ring(sp['q'], sp['r'], rr)
    for a, b in cands:
        t = w.column_top(a, b)
        if t is None or t < 0:
            continue
        cells = [(a + k, b) for k in range(-1, 9)]
        if all(w.column_top(x, y) == t and w.get(x, y, t + 1) in (0, M['petals']) and w.get(x, y, t + 2) == 0
               and w.get(x, y, t) in (M['turf'], M['plinth'], M['stone']) for x, y in cells):
            flat = (a, b, t)
            break
    log('flat', flat)
    if flat:
        q0, r0, top = flat
        from .session import INITIAL_META
        placed = []
        for k, form in enumerate([M['sprout'], M['bloom'], M['crystal'], M['mossrock'], M['water'], M['lantern'], M['cloudstuff'], M['clay']]):
            a, b = q0 + k, r0
            y = top + 1 if form != M['mossrock'] else top
            w.set(a, b, y, form, INITIAL_META.get(form, 0), now=True)
            ses.sim.wake(a, b, y)
            placed.append((MT.NAMES[form], a, b, y))
        log('placed', placed)
        cx, cz = center(q0 + 3, r0)
        p.x, p.z = center(q0 + 5, r0 - 4)
        p.y = (top + 3) * LAYER
        p.drifting = True
        look_at(p, cx, (top + 1) * LAYER, cz)
        yield settled()
        yield 0.8
        yield shot('40_garden_before')
        for i in range(160):
            ses.sim.step(0.5, 0.0 if i < 100 else 1.0, budget=200)
        ses.phase = 0.5
        yield settled()
        yield 1.0
        log('after sim', [MT.NAMES[w.get(a, b, y)] for _, a, b, y in placed])
        yield shot('41_garden_after_dusk')
        ses.phase = 0.0
        yield 0.5
        yield shot('42_garden_after_light')
        p.drifting = False
    # --- glide off an edge and get carried back by clouds
    p.can_glide = True
    yield 0.2
    edge = None
    q0, r0 = cell_at(p.x, p.z)
    top = w.column_top(q0, r0) or 60
    for rad in range(4, 60):
        for (a, b) in ring(q0, r0, rad)[::3]:
            t = w.column_top(a, b)
            if t is not None and t < 0:
                edge = (a, b)
                break
        if edge:
            break
    log('edge', edge)
    q0, r0 = cell_at(p.x, p.z)
    if edge:
        ex, ez = center(*edge)
        p.x, p.z = ex, ez
        p.y = (top + 6) * LAYER
        p.pitch = -25
        app.test_input = {'jump': True, 'fwd': 1}
        yield 1.5
        yield shot('50_gliding')
        app.test_input = {}
        yield lambda: ses.carry > 0
        yield 0.5
        yield shot('51_carried')
        yield 2.0
        log('after carry', p.x, p.y, p.z, p.last_safe)
    # --- menus
    app.set_screen(S.RestScreen())
    yield 0.6
    yield shot('60_rest')
    for t in range(4):
        app.set_screen(S.JournalScreen(tab=t))
        yield 0.4
        yield shot(f'61_journal_{t}')
    app.set_screen(S.SettingsScreen(None))
    yield 0.4
    yield shot('62_settings')
    app.set_screen(None)
    # --- far away
    ses.command('/tp 1000000000 -2500000000')
    yield settled()
    yield 1.0
    app.show_debug = True
    yield 0.5
    yield shot('70_far_billion')
    app.show_debug = False
    # --- save & reload
    yield 0.2
    app.set_screen(S.RestScreen())
    yield 0.5
    name = ses.storage.folder
    awake = list(ses.awakened)
    app.quit_to_title()
    yield 1.0
    app.set_screen(S.SkiesScreen(app))
    yield 1.0
    yield shot('80_skies')
    app.open_sky(name)
    yield lambda: app.mode == 'game'
    ses2 = app.session
    log('reloaded', ses2.awakened == awake, ses2.player.x, ses2.essence)
    yield settled()
    yield 1.0
    yield shot('81_reloaded')


def realms(app, log, shot, look_at, settled, arg):
    """Visit one spot of each realm, plus a skerry field and a waterfall."""
    seed = seed_from_text(arg or 'realm-tour')
    yield 0.5
    app.create_sky('Realm Tour', seed, arg, 'dreamer')
    yield lambda: app.mode == 'game'
    ses = app.session
    p = ses.player
    p.drifting = True
    app.hide_hud = True
    g = ses.gen
    step = 6
    n = 260
    qs = (np.arange(n) - n // 2) * step
    Q, R = np.meshgrid(qs, qs, indexing='ij')
    c = g.columns(Q, R)
    targets = []
    for realm in range(8):
        m = (c['realm'] == realm) & c['land'] & (c['e'] > 0.12) & ~c['skerry']
        idx = np.argwhere(m)
        if len(idx):
            d = (Q[m] ** 2 + R[m] ** 2)
            i = idx[np.argmin(d)]
            targets.append((MT.REALMS[realm].replace(' ', '_').lower(), int(Q[tuple(i)]), int(R[tuple(i)]), int(c['top'][tuple(i)])))
    f = np.argwhere(c['fall'])
    if len(f):
        i = f[np.argmin(np.abs(Q[c['fall']]) + np.abs(R[c['fall']]))]
        targets.append(('waterfall', int(Q[tuple(i)]), int(R[tuple(i)]), int(c['top'][tuple(i)])))
    log('targets', targets)
    for k, (name, q, r, top) in enumerate(targets):
        tx, tz = center(q, r)
        ang = k * 1.3
        dist = 34 if name != 'waterfall' else 40
        p.x, p.z = tx + math.cos(ang) * dist, tz + math.sin(ang) * dist
        p.y = (top + (16 if name != 'waterfall' else 4)) * LAYER
        look_at(p, tx, (top - (0 if name != 'waterfall' else 20)) * LAYER, tz)
        ses.phase = [0.05, 0.12, 0.2, 0.3, 0.08, 0.15, 0.25, 0.6, 0.1][k % 9]
        yield 0.3
        yield settled()
        yield 1.0
        yield shot('realm_' + name)
    # high overview
    q, r = cell_at(p.x, p.z)
    p.y += 50
    p.pitch = -30
    ses.phase = 0.28
    yield settled()
    yield 1.0
    yield shot('realm_overview')


def perf(app, log, shot, look_at, settled, arg):
    import cProfile, pstats, io, time
    seed = seed_from_text('perf')
    yield 0.5
    app.create_sky('Perf', seed, '', 'wanderer')
    yield lambda: app.mode == 'game'
    ses = app.session
    yield settled()
    app.test_input = {'fwd': 1, 'hurry': True}
    pr = cProfile.Profile()
    pr.enable()
    t0 = time.perf_counter()
    yield 8.0
    pr.disable()
    ft = app.frame_times[-60:]
    log('fps', len(ft) / sum(ft))
    s = io.StringIO()
    pstats.Stats(pr, stream=s).sort_stats('cumulative').print_stats(25)
    log(s.getvalue())


def seeds(app, log, shot, look_at, settled, arg):
    """Overviews of several random seeds (to show how different skies feel)."""
    from .noise import random_seed
    yield 1.0
    for k in range(6):
        seed = random_seed()
        app.create_sky(f'Seed {k}', seed, '', 'dreamer')
        yield lambda: app.mode == 'game'
        ses = app.session
        p = ses.player
        p.drifting = True
        app.hide_hud = True
        p.y += 22
        p.pitch = -24
        ses.phase = [0.05, 0.2, 0.3, 0.1, 0.62, 0.15][k]
        yield settled()
        yield 1.0
        log('seed', k, seed)
        yield shot(f'seed_{k}')
        app.hide_hud = False
        app.quit_to_title()
        yield 0.5
