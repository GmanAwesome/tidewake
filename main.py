"""Tidewake: a cozy sky of hexagon islands, living elements and sleeping spires.

    python main.py                         # opens the title screen
    python main.py --size 1600x900 --workers 6
"""
import argparse
import multiprocessing
import os
import sys


def base_dir():
    return os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser(description='Tidewake')
    ap.add_argument('--size', default='1280x720', help='window size, e.g. 1600x900')
    ap.add_argument('--workers', type=int, default=None, help='background worker processes')
    ap.add_argument('--data', default=None, help='folder for skies/, settings.json and snapshots/')
    ap.add_argument('--tour', default=None, help=argparse.SUPPRESS)
    ap.add_argument('--out', default='tour-shots', help=argparse.SUPPRESS)
    ap.add_argument('--arg', default='', help=argparse.SUPPRESS)
    args = ap.parse_args()

    import pyglet
    from tidewake.app import App
    w, h = (int(v) for v in args.size.lower().split('x'))
    n = args.workers or max(1, min(6, (os.cpu_count() or 2) - 1))
    app = App(args.data or base_dir(), size=(w, h), workers_count=n)
    if args.tour:
        from tidewake.tour import install
        install(app, args.tour, args.out, args.arg)
    pyglet.app.run(None)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
