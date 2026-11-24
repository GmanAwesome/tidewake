"""Scripted tours for automated testing and screenshots (python main.py --tour NAME --out DIR)."""
import math
import os
import time

import numpy as np
import pyglet

from .config import LAYER
from .hexgrid import center, cell_at
from .noise import seed_from_text
from .ui import screens as S


def install(app, name, out, arg=''):
    os.makedirs(out, exist_ok=True)
    log_path = os.path.join(out, 'tour.log')

    def log(*a):
        with open(log_path, 'a') as f:
            f.write(' '.join(str(x) for x in a) + '\n')

    def shot(n):
        app.shot_queue.append(os.path.join(out, n + '.png'))
        return 0.0

    def look_at(p, tx, ty, tz):
        ex, ey, ez = p.eye
        dx, dy, dz = tx - ex, ty - ey, tz - ez
        p.yaw = math.degrees(math.atan2(dx, -dz)) % 360
        p.pitch = math.degrees(math.atan2(dy, math.hypot(dx, dz)))

    def settled():
        ses = app.session
        return lambda: ses.world.busy() == 0 and not ses.world.dirty

    from . import tours
    gen = getattr(tours, name)(app, log, shot, look_at, settled, arg)
    state = {'wait': 0.0, 'cond': None, 'gen': gen, 't0': time.time()}

    def on_frame(dt):
        if state['gen'] is None:
            return
        if state['cond'] is not None:
            try:
                ok = state['cond']()
            except Exception as e:
                log('cond error', e)
                ok = True
            if not ok and time.time() - state['since'] < 90:
                return
            state['cond'] = None
        if state['wait'] > 0:
            state['wait'] -= dt
            return
        if app.shot_queue:
            return
        try:
            v = next(state['gen'])
        except StopIteration:
            log('done', time.time() - state['t0'])
            state['gen'] = None
            pyglet.clock.schedule_once(lambda _: app.quit(), 1.0)
            return
        except Exception as e:
            import traceback
            log('ERROR', traceback.format_exc())
            state['gen'] = None
            pyglet.clock.schedule_once(lambda _: app.quit(), 0.5)
            return
        if callable(v):
            state['cond'] = v
            state['since'] = time.time()
        else:
            state['wait'] = float(v or 0)

    app.on_frame = on_frame
