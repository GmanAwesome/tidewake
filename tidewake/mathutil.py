"""Small matrix helpers (row-major numpy; transpose before sending to GL)."""
import math
import numpy as np


def perspective(fov_deg, aspect, near, far):
    f = 1.0 / math.tan(math.radians(fov_deg) / 2)
    m = np.zeros((4, 4), dtype=np.float32)
    m[0, 0] = f / aspect
    m[1, 1] = f
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = 2 * far * near / (near - far)
    m[3, 2] = -1
    return m


def view_matrix(eye, yaw_deg, pitch_deg):
    """Camera at eye looking along yaw/pitch (yaw 0 = -z, positive yaw turns right)."""
    cy, sy = math.cos(math.radians(yaw_deg)), math.sin(math.radians(yaw_deg))
    cp, sp = math.cos(math.radians(pitch_deg)), math.sin(math.radians(pitch_deg))
    fwd = np.array([sy * cp, sp, -cy * cp])
    right = np.array([cy, 0, sy])
    up = np.cross(right, fwd)
    m = np.identity(4, dtype=np.float32)
    m[0, :3], m[1, :3], m[2, :3] = right, up, -fwd
    m[:3, 3] = -m[:3, :3] @ np.asarray(eye, dtype=np.float32)
    return m


def forward_vector(yaw_deg, pitch_deg):
    cy, sy = math.cos(math.radians(yaw_deg)), math.sin(math.radians(yaw_deg))
    cp, sp = math.cos(math.radians(pitch_deg)), math.sin(math.radians(pitch_deg))
    return np.array([sy * cp, sp, -cy * cp])


def frustum_planes(vp):
    """6 planes (a, b, c, d) from a row-major view-projection matrix."""
    r = vp
    planes = np.array([r[3] + r[0], r[3] - r[0], r[3] + r[1], r[3] - r[1], r[3] + r[2], r[3] - r[2]])
    return planes / np.linalg.norm(planes[:, :3], axis=1, keepdims=True)


def boxes_visible(planes, mins, maxs):
    """Vectorised AABB-vs-frustum test. mins/maxs: (N, 3). Returns bool (N,)."""
    if len(mins) == 0:
        return np.zeros(0, dtype=bool)
    vis = np.ones(len(mins), dtype=bool)
    for a, b, c, d in planes:
        px = np.where(a > 0, maxs[:, 0], mins[:, 0])
        py = np.where(b > 0, maxs[:, 1], mins[:, 1])
        pz = np.where(c > 0, maxs[:, 2], mins[:, 2])
        vis &= (a * px + b * py + c * pz + d) >= 0
    return vis
