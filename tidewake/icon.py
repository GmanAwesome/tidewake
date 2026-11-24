"""The window icon: a little cluster of element hexagons, drawn with numpy."""
import math

import numpy as np
import pyglet

from .materials import ELEMENT_COLORS


def icon_rgba(n):
    img = np.zeros((n, n, 4), np.float32)
    yy, xx = np.mgrid[0:n, 0:n] + 0.5
    r = n * 0.2
    pts = [(-0.95, 0.0, ELEMENT_COLORS[0]), (0.95, 0.0, ELEMENT_COLORS[1]), (-0.48, 0.82, ELEMENT_COLORS[2]),
           (0.48, 0.82, ELEMENT_COLORS[3]), (-0.48, -0.82, ELEMENT_COLORS[3]), (0.48, -0.82, ELEMENT_COLORS[2]),
           (0.0, 0.0, (1.0, 1.0, 1.0))]
    for dx, dy, col in pts:
        cx, cy = n / 2 + dx * r * 1.15, n / 2 + dy * r * 1.15
        px, py = np.abs(xx - cx), np.abs(yy - cy)
        # pointy-top hexagon test
        inside = (px <= r * 0.866) & (py <= r - px * 0.57735)
        rim = inside & ~((px <= r * 0.866 - 1.2) & (py <= r - 1.4 - px * 0.57735))
        img[inside] = (*col, 1)
        img[rim] = (1, 1, 1, 1)
    return (img * 255).astype(np.uint8)


def icon_images():
    out = []
    for n in (16, 32, 64, 128):
        a = icon_rgba(n)[::-1]
        out.append(pyglet.image.ImageData(n, n, 'RGBA', np.ascontiguousarray(a).tobytes()))
    return out
