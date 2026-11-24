"""Settings, stored in settings.json next to the skies folder."""
import json

DEFAULTS = {
    'view_distance': 12,      # chunks (full detail up to 7, far LOD beyond)
    'settings_version': 2,
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
            if data.get('settings_version', 1) < 2:      # 1.3: far terrain is cheap now, so see further
                self['view_distance'] = max(12, self['view_distance'])
                self['settings_version'] = 2
        except (OSError, ValueError):
            pass

    def save(self):
        try:
            with open(self.path, 'w') as f:
                json.dump(dict(self), f, indent=2)
        except OSError:
            pass
