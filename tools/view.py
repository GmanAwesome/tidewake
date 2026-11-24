"""Render a still from a seed: python tools/view.py SEED out.png x z height yaw pitch phase"""
import sys, os, time, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
import numpy as np


def main():
    import pyglet, moderngl
    from tidewake.world import World
    from tidewake.renderer import Renderer
    from tidewake.mathutil import perspective, view_matrix
    from tidewake.screenshot import capture
    from tidewake.tide import atmosphere
    from tidewake.generator import Generator
    from tidewake.hexgrid import cell_at
    from tidewake.config import LAYER
    seed = int(sys.argv[1]); out = sys.argv[2]
    x, z, hgt, yaw, pitch, phase = (float(v) for v in sys.argv[3:9])
    vd = int(sys.argv[9]) if len(sys.argv) > 9 else 5
    cfg = pyglet.gl.Config(major_version=3, minor_version=3, forward_compatible=True, depth_size=24, double_buffer=True)
    win = pyglet.window.Window(1280, 720, config=cfg, visible=True)
    ctx = moderngl.create_context()
    R = Renderer(ctx)
    pool = ProcessPoolExecutor(6, mp_context=mp.get_context('spawn'))
    w = World(seed, None, R, pool, vd)
    g = Generator(seed)
    q, r = cell_at(x, z)
    top = int(g.columns(np.array([q]), np.array([r]))['top'][0])
    y = max(top * LAYER, 20) + hgt
    t0 = time.time()
    while True:
        w.update(x, z, 50)
        pyglet.clock.tick(); win.dispatch_events()
        if w.busy() == 0 and len(w.chunks) > 10 and not w.dirty:
            break
        if time.time() - t0 > 120: break
        time.sleep(0.02)
    print('loaded', len(w.chunks), time.time() - t0)
    proj = perspective(70, 1280 / 720, 0.1, 1000)
    vr = view_matrix((0, 0, 0), yaw, pitch)
    atmo = atmosphere(phase)
    ctx.viewport = (0, 0, *win.get_framebuffer_size())
    tt = time.perf_counter()
    R.draw((x, y, z), proj, vr, w.meshes(), atmo, w.radius, 10.0)
    ctx.finish(); print('draw', time.perf_counter() - tt, R.stats)
    capture(ctx, out)
    pool.shutdown(cancel_futures=True)


if __name__ == '__main__':
    main()
