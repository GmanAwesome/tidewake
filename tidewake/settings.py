"""Settings, stored in settings.json next to the skies folder."""
import json

DEFAULTS = {
    'view_distance': 6,       # chunks
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
        except (OSError, ValueError):
            pass

    def save(self):
        try:
            with open(self.path, 'w') as f:
                json.dump(dict(self), f, indent=2)
        except OSError:
            pass
