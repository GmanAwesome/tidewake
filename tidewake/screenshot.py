"""PNG writing (no Pillow needed) and framebuffer capture."""
import struct
import zlib

import numpy as np


def png_bytes(img):
    """img: (h, w, 3 or 4) uint8, row 0 at the top."""
    h, w, c = img.shape
    raw = b''.join(b'\x00' + row.tobytes() for row in img)
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6 if c == 4 else 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))


def save_png(path, rgb, width, height):
    img = np.frombuffer(rgb, dtype=np.uint8).reshape(height, width, 3)[::-1]
    with open(path, 'wb') as f:
        f.write(png_bytes(np.ascontiguousarray(img)))


def capture(ctx, path):
    fb = ctx.screen
    w, h = fb.viewport[2], fb.viewport[3]
    data = fb.read(viewport=(0, 0, w, h), components=3, alignment=1)
    _ = ctx.error          # reading the default framebuffer flags a benign GL error; clear it for pyglet
    save_png(path, data, w, h)
