"""Saved skies: skies/<folder>/sky.json, a thumbnail, and chunks/ holding only changed chunks."""
import json
import os
import re
import shutil
import time

import numpy as np

VERSION = 1


def pad_layers(cells, meta=None):
    """Grow a 1.4-era (128-layer) chunk to the current column height, or trim a taller one."""
    from .config import LAYERS
    L = int(cells.shape[1])
    if L == LAYERS:
        return (cells, meta) if meta is not None else cells
    def _fit(a):
        if a is None:
            return None
        if a.shape[1] == LAYERS:
            return a
        out = np.zeros((a.shape[0], LAYERS, a.shape[2]), a.dtype)
        n = min(L, LAYERS)
        out[:, :n] = a[:, :n]
        return out
    cells = _fit(cells)
    return (cells, _fit(meta)) if meta is not None else cells



def sanitize(name):
    s = re.sub(r'[^A-Za-z0-9 _\-\']', '', name).strip() or 'New Sky'
    return s[:36]


class SkyStorage:
    def __init__(self, root, folder):
        self.root = root
        self.folder = folder
        self.path = os.path.join(root, folder)
        self.chunk_dir = os.path.join(self.path, 'chunks')

    @property
    def meta_file(self):
        return os.path.join(self.path, 'sky.json')

    @property
    def thumb_file(self):
        return os.path.join(self.path, 'thumb.npy')

    def exists(self):
        return os.path.exists(self.meta_file)

    def load(self):
        with open(self.meta_file) as f:
            return json.load(f)

    def save(self, data):
        os.makedirs(self.chunk_dir, exist_ok=True)
        data = dict(data, version=VERSION, last_played=time.time())
        tmp = self.meta_file + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(data, f, indent=1)
        os.replace(tmp, self.meta_file)

    def save_thumb(self, img):
        try:
            os.makedirs(self.path, exist_ok=True)
            tmp = self.thumb_file + '.tmp.npy'
            np.save(tmp, img)
            os.replace(tmp, self.thumb_file)
        except OSError:
            pass

    def load_thumb(self):
        try:
            return np.load(self.thumb_file)
        except Exception:
            return None

    def chunk_file(self, cq, cr):
        return os.path.join(self.chunk_dir, f'c.{cq}.{cr}.npz')

    def save_chunk(self, cq, cr, cells, meta, realm):
        os.makedirs(self.chunk_dir, exist_ok=True)
        path = self.chunk_file(cq, cr)
        tmp = path + '.tmp.npz'
        np.savez_compressed(tmp, cells=cells, meta=meta, realm=realm)
        os.replace(tmp, path)

    @staticmethod
    def list_skies(root):
        out = []
        if not os.path.isdir(root):
            return out
        for folder in os.listdir(root):
            st = SkyStorage(root, folder)
            if not st.exists():
                continue
            try:
                d = st.load()
            except Exception:
                continue
            out.append(dict(folder=folder, name=d.get('name', folder), seed=d.get('seed'), mode=d.get('mode', 'wanderer'),
                            last_played=d.get('last_played', 0), awakened=len(d.get('awakened', [])),
                            play_time=d.get('play_time', 0), seed_text=d.get('seed_text', ''),
                            tutorial=bool(d.get('tutorial'))))
        out.sort(key=lambda w: -w['last_played'])
        return out

    @staticmethod
    def unique_folder(root, name):
        base = sanitize(name)
        folder, i = base, 2
        while os.path.exists(os.path.join(root, folder)):
            folder, i = f'{base} ({i})', i + 1
        return folder

    def delete(self):
        shutil.rmtree(self.path, ignore_errors=True)

    def rename(self, new_name):
        d = self.load()
        d['name'] = new_name.strip()[:36] or d.get('name', self.folder)
        tmp = self.meta_file + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(d, f, indent=1)
        os.replace(tmp, self.meta_file)
