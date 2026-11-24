"""Tour scripts (generators). Yield seconds to wait or a predicate to wait for."""
import math
import random

import numpy as np

from .config import LAYER
from .hexgrid import center, cell_at, ring
from .noise import seed_from_text
from . import materials as MT
from .ui import screens as S
from .ui import inventory_ui as IU
from . import items as I
from .hexgrid import spiral, DIRS

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
    pstats.Stats(pr, stream=s).sort_stats('tottime').print_stats(22)
    log(s.getvalue())
    yield shot('perf_view')


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


def _find(ses, mats, radius=14, ylo=-3, yhi=8):
    p = ses.player
    q0, r0 = cell_at(p.x, p.z)
    y0 = math.floor(p.y / LAYER)
    best = None
    for a, b in spiral(q0, r0, radius):
        for y in range(y0 + ylo, y0 + yhi):
            if ses.world.get(a, b, y) in mats:
                return (a, b, y)
    return best


def _aim(look_at, ses, cell):
    q, r, y = cell
    x, z = center(q, r)
    look_at(ses.player, x, (y + 0.5) * LAYER, z)


def _stand_near(ses, cell, look_at, dist=2):
    """Stand on solid ground a couple of cells from a target cell, looking at it."""
    q, r, y = cell
    for k in (dist, dist + 1, 1, dist + 2):
        for a, b in ring(q, r, k):
            top = ses.world.column_top(a, b)
            if top is None or top < 0 or abs(top + 1 - y) > 3:
                continue
            if ses.world.get(a, b, top + 1) not in (0, M['petals']) or ses.world.get(a, b, top + 2) != 0 or ses.world.get(a, b, top + 3) != 0:
                continue
            p = ses.player
            p.x, p.z = center(a, b)
            p.y = (top + 1) * LAYER + 0.001
            p.vx = p.vy = p.vz = 0
            _aim(look_at, ses, cell)
            return True
    return False


def v11(app, log, shot, look_at, settled, arg):
    seed = seed_from_text(arg or 'clover-lantern-3')
    yield 1.0
    yield lambda: app.backdrop['world'].busy() == 0
    yield 0.5
    yield shot('00_title')
    app.set_screen(S.NewSkyScreen(S.SkiesScreen(app)))
    app.menu.name = 'Clover Lantern'
    app.menu.seed = arg or 'clover-lantern-3'
    yield 0.4
    yield shot('01_new_sky')
    app.create_sky('Clover Lantern', seed, arg or 'clover-lantern-3', 'wanderer')
    yield lambda: app.mode == 'game'
    ses = app.session
    p = ses.player
    yield settled()
    yield 1.0
    yield shot('10_spawn')
    log('spawn', p.x, p.y, p.z, 'mobs', len(ses.mobs))
    # --- mine a tree by hand
    wood = _find(ses, (M['heartwood'],), 30, -2, 6)
    log('wood', wood)
    if wood and _stand_near(ses, wood, look_at, 2):
        yield settled()
        yield 0.3
        app.test_input = {'gather': True, 'hold': True}
        yield 1.0
        yield shot('11_mining_wood')
        for _ in range(60):
            yield 0.1
            if ses.inv.count(M['heartwood']) >= 1 and not ses.drops:
                break
        app.test_input = {}
        yield 0.6
        for dr in list(ses.drops):
            p.x, p.z = dr.x, dr.z
            yield 0.5
        yield 0.5
        log('heartwood', ses.inv.count(M['heartwood']), 'drops', len(ses.drops))
        yield shot('12_mined_wood')
    # --- craft: backpack with planks
    ses.give(M['heartwood'], 6, quiet=True)
    app.set_screen(IU.BackpackScreen())
    yield 0.3
    rec = next(r for r in I.RECIPES if r[1][0] == M['planks'])
    app.menu.fill(app, rec)
    yield 0.4
    yield shot('13_backpack_craft')
    app.menu.escape(app)
    # give a decent kit for the rest of the tour
    for iid, n in ((M['planks'], 40), (I.STICK.id, 12), (M['stone'], 30), (I.EMBERITE.id, 10), (M['verdigris_ore'], 6),
                   (M['tinker_bench'], 1), (M['kiln'], 1), (M['chest'], 1), (M['glowstick'], 12), (M['glass'], 12),
                   (I.FLUFF.id, 6), (M['bedroll'], 1)):
        ses.give(iid, n, quiet=True)
    ses.give(I.TOOLS[('pick', 1)].id, 1, quiet=True)
    app.set_screen(IU.CraftScreen(3))
    yield 0.3
    rec = next(r for r in I.RECIPES if r[1][0] == I.TOOLS[('pick', 1)].id)
    app.menu.fill(app, rec)
    yield 0.4
    yield shot('14_bench_craft')
    app.menu.escape(app)
    yield 0.3
    # --- build a little camp: bench, kiln, chest, glowsticks
    q0, r0 = cell_at(p.x, p.z)
    camp = (q0, r0)
    top = ses.world.column_top(q0, r0)
    y = top + 1
    placed = []
    for (dq, dr), mat in zip(DIRS, (M['tinker_bench'], M['kiln'], M['chest'], M['glowstick'], M['bedroll'], M['lumen_lamp'])):
        a, b = q0 + dq * 2, r0 + dr * 2
        t = ses.world.column_top(a, b)
        if t is not None and t >= 0 and ses.world.get(a, b, t + 1) in (0, M['petals']):
            ses.world.set(a, b, t + 1, mat, now=True)
            placed.append((a, b, t + 1, mat))
            if mat == M['chest']:
                from .inventory import Inventory
                ses.chests[f'{a},{b},{t + 1}'] = Inventory(27)
                ses.chests[f'{a},{b},{t + 1}'].add(I.AETHERITE.id, 3)
                ses.chests[f'{a},{b},{t + 1}'].add(M['planks'], 20)
            if mat == M['kiln']:
                from .inventory import Inventory
                ses.kilns[f'{a},{b},{t + 1}'] = {'slots': Inventory(3), 'burn': 0.0, 'burn_max': 1.0, 'prog': 0.0}
                ses.kilns[f'{a},{b},{t + 1}']['slots'].slots = [[M['verdigris_ore'], 5, 0], [I.EMBERITE.id, 4, 0], None]
    log('placed', placed)
    p.pitch = -25
    p.yaw = (p.yaw + 180) % 360
    yield settled()
    yield 0.5
    # back up and look at the camp
    p.x, p.z = center(q0 - 6, r0 + 3)
    p.drifting = True
    p.y = (y + 5) * LAYER
    look_at(p, *center(q0, r0)[:1], (y + 0.3) * LAYER, center(q0, r0)[1])
    x0, z0 = center(q0, r0)
    look_at(p, x0, (y + 0.2) * LAYER, z0)
    ses.select(6)
    yield settled()
    yield 1.0
    yield shot('20_camp')
    p.drifting = False
    _stand(ses, q0, r0)
    for (a, b, yy, mat) in placed:
        if mat == M['kiln']:
            ses.use_block(a, b, yy, mat)
            yield 1.5
            yield shot('21_kiln')
            app.menu.escape(app)
        if mat == M['chest']:
            ses.use_block(a, b, yy, mat)
            yield 0.4
            yield shot('22_chest')
            app.menu.escape(app)
    # --- creatures
    ses.mobs = []
    for kind in ('woolhop', 'woolhop', 'pebblebeak', 'mossback', 'pebblebeak'):
        ses._try_spawn(False, kind=kind, near=True)
    yield 2.0
    if ses.mobs:
        m0 = min(ses.mobs, key=lambda m: math.hypot(m.x - p.x, m.z - p.z))
        mx, mz = m0.x, m0.z
        dx, dz = p.x - mx, p.z - mz
        dd = math.hypot(dx, dz) or 1
        p.x, p.z = mx + dx / dd * 4, mz + dz / dd * 4
        p.drifting = True
        p.y = m0.y + 1.6
        for m in ses.mobs:
            m.think = 99
            m.walking = False
        look_at(p, mx, m0.y + 0.3, mz)
    yield 0.3
    yield shot('30_creatures')
    p.drifting = False
    log('mobs', [(m.kind, round(m.x, 1), round(m.z, 1)) for m in ses.mobs])
    # hit a woolhop until it drops something
    ses.select(0)
    ses.inv.slots[0] = [I.TOOLS[('blade', 2)].id, 1, I.TOOLS[('blade', 2)].uses]
    for _ in range(10):
        wl = [m for m in ses.mobs if m.kind == 'woolhop']
        if not wl:
            break
        m0 = wl[0]
        look_at(p, m0.x, m0.y + 0.5, m0.z)
        if math.hypot(m0.x - p.x, m0.z - p.z) > 3:
            p.x += (m0.x - p.x) * 0.6
            p.z += (m0.z - p.z) * 0.6
        app.test_input = {'gather': True, 'hold': True}
        yield 0.5
    app.test_input = {}
    yield 0.4
    log('drops after hunt', [(I.get(d.iid).name, d.count) for d in ses.drops])
    yield shot('31_drops')
    for dr in list(ses.drops):
        p.x, p.z = dr.x, dr.z
        p.y = max(p.y, dr.y)
        yield 0.4
    yield 1.0
    log('inv fluff', ses.inv.count(I.FLUFF.id), 'meat', ses.inv.count(I.HOPMEAT.id))
    # --- a cave: find an enclosed air pocket deep inside the island
    found = None
    q0, r0 = cell_at(p.x, p.z)
    for a, b in spiral(q0, r0, 40):
        top = ses.world.column_top(a, b)
        if top is None or top < 20:
            continue
        for yy in range(top - 4, top - 40, -1):
            if ses.world.get(a, b, yy) == 0 and all(MT.OPAQUE[max(0, ses.world.get(a, b, yy - k))] for k in (1, 2, 3, 4, 5)) \
                    and ses.world.get(a, b, yy + 1) == 0 and ses.world.get(a, b, yy + 2) == 0:
                # enclosed? solid somewhere above
                rock = (M['stone'], M['loam'], M['mossrock'], M['clay'], M['sand'], M['basalt'], M['rosestone'], M['turf']) + tuple(MT.ORES)
                if sum(1 for k in range(yy + 3, top + 1) if ses.world.get(a, b, k) in rock) >= 4:
                    ores = sum(1 for c, d in spiral(a, b, 5) for k in range(yy - 2, yy + 5) if ses.world.get(c, d, k) in MT.ORES)
                    if ores >= 3:
                        found = (a, b, yy, ores)
                        break
        if found:
            break
    log('cave', found)
    if found:
        a, b, yy, _ = found
        p.x, p.z = center(a, b)
        p.y = yy * LAYER + 0.001
        p.drifting = False
        # look at the nearest ore
        best = None
        for c, d in spiral(a, b, 5):
            for k in range(yy - 2, yy + 5):
                if ses.world.get(c, d, k) in MT.ORES:
                    best = (c, d, k)
                    break
            if best:
                break
        if best:
            _aim(look_at, ses, best)
        nb = ses.world.get(a + 1, b, yy)
        ses.world.set(a, b - 1, yy, M['glowstick'], now=True) if ses.world.get(a, b - 1, yy) == 0 and MT.SOLID[max(0, ses.world.get(a, b - 1, yy - 1))] else None
        ses.select(1)
        yield settled()
        yield 1.0
        yield shot('40_cave')
    # --- mountains vista
    q0, r0 = cell_at(p.x, p.z)
    best, bt = None, -1
    for a, b in spiral(q0, r0, 60)[::7]:
        t = ses.world.column_top(a, b)
        if t is not None and t > bt:
            best, bt = (a, b), t
    log('highest', best, bt)
    # --- dusk with gloomlings
    ses.phase = 0.5
    p.drifting = False
    _stand(ses, camp[0], camp[1])
    yield settled()
    ses.mobs = []
    for _ in range(4):
        ses._try_spawn(True, kind='gloomling', near=True)
    ses._try_spawn(True, kind='brute', near=True)
    for i, m in enumerate(ses.mobs):
        ang = math.radians(p.yaw + (i - 2) * 22)
        m.x, m.z = p.x + math.sin(ang) * (6 + i % 2), p.z - math.cos(ang) * (6 + i % 2)
        m.y = p.y + 2
    yield 0.6
    hs = [m for m in ses.mobs if m.hostile]
    if hs:
        look_at(p, hs[2 % len(hs)].x, p.y + 0.6, hs[2 % len(hs)].z)
    yield 0.2
    yield shot('50_dusk_gloomlings')
    for _ in range(5):
        yield 0.5
        log('gl', round(ses.phase, 3), [(m.kind, round(math.hypot(m.x - p.x, m.z - p.z), 2), round(m.y - p.y, 2), round(m.fade, 2), m.dead) for m in ses.mobs if m.hostile])
    log('hp after gloom', ses.hp)
    yield shot('51_bumped')
    # --- dev mode
    ses.set_dev(True)
    ses.mobs = [m for m in ses.mobs if not m.hostile]
    ses.phase = 0.12
    p.drifting = True
    p.y += 30
    p.pitch = -30
    yield settled()
    yield 1.0
    yield shot('60_dev_fly')
    app.set_screen(IU.AdminScreen())
    yield 0.4
    yield shot('61_admin_panel')
    app.set_screen(None)
    # fill a glass dome-ish box with commands
    q0, r0 = cell_at(p.x, p.z)
    t = ses.world.column_top(q0, r0) or 60
    ses.pos1 = (q0 - 3, r0 - 3, t + 1)
    ses.pos2 = (q0 + 3, r0 + 3, t + 6)
    ses.command('/fill glass')
    ses.pos1 = (q0 - 2, r0 - 2, t + 1)
    ses.pos2 = (q0 + 2, r0 + 2, t + 5)
    ses.command('/clear')
    ses.command('/give lumen lamp 4')
    ses.world.set(q0, r0, t + 1, M['lumen_lamp'], now=True)
    p.y = (t + 14) * LAYER
    x0, z0 = center(q0, r0)
    p.x, p.z = x0 + 9, z0 + 9
    look_at(p, x0, (t + 3) * LAYER, z0)
    yield settled()
    yield 1.0
    yield shot('62_fill_glass')
    if best:
        p.x, p.z = center(best[0] + 22, best[1] + 8)
        p.y = (bt - 6) * LAYER
        look_at(p, *center(*best)[:1], bt * LAYER, center(*best)[1])
        x0, z0 = center(*best)
        look_at(p, x0, (bt - 12) * LAYER, z0)
        app.hide_hud = True
        yield settled()
        yield 1.0
        yield shot('63_mountain')
        app.hide_hud = False
    ses.set_dev(False)
    # --- journal + faded screen
    app.set_screen(S.JournalScreen(tab=1))
    yield 0.4
    yield shot('70_journal_recipes')
    app.set_screen(S.JournalScreen(tab=4))
    yield 0.3
    yield shot('71_journal_controls')
    app.set_screen(None)
    ses.damage(50, 'gloomling')
    yield 0.4
    yield shot('72_faded')
    ses.respawn()
    app.set_screen(None)
    yield 0.5
    ses.save()
    app.quit_to_title()
    yield 1.0
    folder = app.thumb_cache and list(app.thumb_cache)[0]
    from .storage import SkyStorage
    sk = SkyStorage.list_skies(app.skies_dir)[0]
    app.open_sky(sk['folder'])
    yield lambda: app.mode == 'game'
    log('reloaded inv', [(I.get(s[0]).name, s[1]) for s in app.session.inv.slots if s][:12], 'chests', len(app.session.chests))
    yield 1.0
    yield shot('80_reloaded')


def vista(app, log, shot, look_at, settled, arg):
    """Far-view check: wait for LOD terrain, then a high shot and an eye-level shot."""
    import time, threading
    gaps = []

    def probe():          # how long can another thread (like the audio feeder) be starved of the GIL?
        last = time.perf_counter()
        while len(gaps) < 100000:
            time.sleep(0.01)
            now = time.perf_counter()
            gaps.append(now - last - 0.01)
            last = now
    threading.Thread(target=probe, daemon=True).start()
    yield 0.5
    app.create_sky('Vista', seed_from_text(arg or 'vista'), arg or 'vista', 'dreamer')
    yield lambda: app.mode == 'game'
    ses = app.session
    p = ses.player
    yield settled()
    t0 = time.perf_counter()
    yield lambda: ses.world.busy() == 0 and ses.world.busy_lod() == 0 and len(ses.world.lod) > 10 or time.perf_counter() - t0 > 60
    yield 1.0
    from . import fast as _f
    log('numba', _f.ENABLED)
    log('lod groups', len(ses.world.lod), 'chunks', len(ses.world.chunks), 'wait', time.perf_counter() - t0,
        'lod ms', 1000 * sum(ses.world.timings['lod']) / max(1, len(ses.world.timings['lod'])),
        'gen ms', 1000 * sum(ses.world.timings['gen']) / max(1, len(ses.world.timings['gen'])))
    p.pitch = -4
    yield 3.0
    ft = app.frame_times[-60:]
    log('fps eye', len(ft) / sum(ft))
    app.hide_hud = True
    yield shot('vista_eye')
    p.drifting = True
    p.y += 30
    p.pitch = -14
    yield 3.0
    ft = app.frame_times[-60:]
    log('fps high', len(ft) / sum(ft))
    g = sorted(gaps)
    log('gil stall ms max %.0f p99 %.0f, >250ms: %d' % (1000 * g[-1], 1000 * g[int(len(g) * 0.99)], sum(1 for x in g if x > 0.25)))
    yield shot('vista_high')
