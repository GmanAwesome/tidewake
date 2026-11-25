"""Settings, stored in settings.json next to the skies folder."""
import json

DEFAULTS = {
    'view_distance': 8,       # full-detail chunks (3-20)
    'far_distance': 16,       # simple far terrain reaches this far (chunks, up to 35)
    'settings_version': 3,
    'fov': 70,
    'sensitivity': 100,       # percent
    'invert_y': False,
    'vsync': True,
    'fullscreen': False,
    'ui_scale': 0,            # 0 = auto
    'fps_limit': 60,          # 0 = unlimited
    'music': 70,              # percent
    'sounds': 80,
    'clouds': True,
    'head_bob': True,
    'motes': True,
    'creatures': True,        # woolhops, pebblebeaks, mossbacks
    'dusk_critters': True,    # gloomlings in the dusk tide
    'title_showcase': '',     # last title-screen showcase, so the next launch starts elsewhere
}
FPS_CHOICES = [30, 60, 90, 120, 144, 0]


class Settings(dict):
    def __init__(self, path):
        super().__init__(DEFAULTS)
        self.path = path
        try:
            with open(path) as f:
                data = json.load(f)
            for k, v in data.items():
                if k in DEFAULTS and type(v) == type(DEFAULTS[k]):
                    self[k] = v
            ver = data.get('settings_version', 1)
            if ver < 3:       # 1.3.1: one view slider became detail + far
                old = int(data.get('view_distance', 8))
                self['far_distance'] = min(35, max(16, old))
                self['view_distance'] = min(20, max(8, old)) if ver < 2 else 8
                self['settings_version'] = 3
            self['view_distance'] = min(20, max(3, self['view_distance']))
            self['far_distance'] = min(35, max(self['view_distance'], self['far_distance']))
        except (OSError, ValueError):
            pass

    def save(self):
        try:
            with open(self.path, 'w') as f:
                json.dump(dict(self), f, indent=2)
        except OSError:
            pass
